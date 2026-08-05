import pandas as pd
import numpy as np
from data_loader import DataLoader
from predicate_engine import PredicateEngine
from fuzzy_engine import FuzzyEngine

class ScenarioEvaluator:
    """
    Orchestrates a full end-to-end evaluation run for one scenario
    (Scenario 1 = AI/Programming/Math, Scenario 2 = Cybersecurity):
    loads all three datasets, runs every row through the predicate
    engine, runs fuzzy scoring on whatever passes, then ranks and
    packages the results for the report generator.

    This class is the "glue" between data_loader, predicate_engine and
    fuzzy_engine - none of those three know about each other directly,
    ScenarioEvaluator is what wires them together per the pipeline
    described in the assessment: Scenario -> Predicate query -> 
    Predicate-only results -> Fuzzy evaluation -> Fuzzy-enhanced 
    results -> Comparison.
    """
    def __init__(self, base_dir=None):
        self.loader = DataLoader(base_dir)
        self.pred_engine = PredicateEngine()
        self.fuzzy_engine = FuzzyEngine()

    def run_evaluation(self, scenario_id=1):
        """
        Runs the full predicate + fuzzy pipeline for one scenario across
        all three datasets and returns a dict keyed by dataset name
        ('A', 'B', 'C'), each holding the predicate-passed records (full
        and top-N), a sample of rejected records, and every evaluated
        record (for size/coverage stats).
        """
        # Load and clean all three source datasets up front so the same
        # in-memory copies are reused for every row evaluated below.
        datasets = {
            'A': self.loader.load_dataset_a(),
            'B': self.loader.load_dataset_b(),
            'C': self.loader.load_dataset_c()
        }

        results = {}

        for name, df in datasets.items():
            predicate_passed_records = []
            sample_rejected_records = []
            all_evaluated_records = []

            # Evaluate every row in this dataset individually against the
            # predicate rules for the requested scenario.
            for idx, row in df.iterrows():
                if scenario_id == 1:
                    passed, topic_class, reason, pred_details = self.pred_engine.evaluate_scenario_1(row, name)
                else:
                    passed, topic_class, reason, pred_details = self.pred_engine.evaluate_scenario_2(row, name)

                # Pick the year column relevant to this dataset (kept
                # here for potential future use/debugging; ranking itself
                # re-reads the year column later via `year_col`).
                if name == 'A':
                    year = row.get('Copyright Year', None)
                elif name == 'B':
                    year = row.get('Copyright', None)
                else:
                    year = row.get('Copyright Year', None)

                # Build a flat dict combining the original row data with
                # the predicate verdict, so downstream code (fuzzy engine,
                # report generator) can work off one unified record shape
                # instead of juggling the row and the verdict separately.
                rec_info = dict(row)
                rec_info['OriginalIndex'] = idx
                # Each dataset uses a different column as its natural
                # record identifier (No. for A, ISBN for B, VBID for C) -
                # fall back through them in order to always get something.
                rec_info['RecordID'] = str(row.get('No.', row.get('eBook ISBN', row.get('VBID', 'N/A'))))
                rec_info['PredicatePassed'] = 'PASS' if passed else 'REJECT'
                rec_info['TopicClass'] = topic_class if passed else 'None'
                rec_info['Reason'] = reason
                rec_info['Dataset'] = name
                rec_info['TopicPredicateMatch'] = pred_details.get('topic_match')
                rec_info['YearPredicateMatch'] = pred_details.get('year_match')
                rec_info['FormatPredicateMatch'] = pred_details.get('format_match')
                rec_info['PricePredicateMatch'] = pred_details.get('price_match')
                rec_info['DeptPredicateMatch'] = pred_details.get('dept_match')
                rec_info['QtyPredicateMatch'] = pred_details.get('qty_match')
                rec_info['EdPredicateMatch'] = pred_details.get('ed_match')

                if passed:
                    # Only records that satisfied the predicate query move
                    # on to fuzzy scoring - fuzzy reasoning refines an
                    # already-qualified pool, it doesn't rescue rejects.
                    fuzzy_res = self.fuzzy_engine.evaluate_ebook(row, topic_class, name)
                    rec_info.update(fuzzy_res)
                    predicate_passed_records.append(rec_info)
                else:
                    # Keep a small sample (up to 5) of rejected records per
                    # dataset, just enough for the report to illustrate
                    # *why* records were excluded without dumping every
                    # rejection.
                    if len(sample_rejected_records) < 5:
                        sample_rejected_records.append(rec_info)

                all_evaluated_records.append(rec_info)

            df_passed = pd.DataFrame(predicate_passed_records)
            df_all = pd.DataFrame(all_evaluated_records)
            df_rejected = pd.DataFrame(sample_rejected_records)

            year_col = 'Copyright Year' if name in ['A', 'C'] else 'Copyright'

            if len(df_passed) > 0:
                # Baseline rank: order by publication year (newest first), tie-broken by title.
                # This represents what a simple, non-fuzzy ordering
                # (predicate-only, sorted by recency) would have produced,
                # so it can be compared against the fuzzy ranking below.
                df_baseline = df_passed.sort_values(by=[year_col, 'Title'], ascending=[False, True]).reset_index(drop=True)
                # Map each title to its rank position (1 = best) in the
                # baseline ordering. Titles are normalised (lowercased,
                # spaces stripped) so the lookup is robust to minor
                # formatting differences between the two DataFrames.
                baseline_rank_map = {str(row['Title']).strip().lower().replace(" ", ""): idx + 1 for idx, row in df_baseline.iterrows()}

                # Fuzzy rank: order by fuzzy suitability score (highest first), tie-broken by year then title.
                df_fuzzy_order = df_passed.sort_values(by=['fuzzy_score', year_col, 'Title'], ascending=[False, False, True]).reset_index(drop=True)
                fuzzy_rank_map = {str(row['Title']).strip().lower().replace(" ", ""): idx + 1 for idx, row in df_fuzzy_order.iterrows()}

                # Attach both rank numbers back onto every passed record
                # (in its original row order) so a single table can show
                # "where it would have ranked" vs "where it actually ranks".
                baseline_ranks = []
                fuzzy_ranks = []

                for _, row in df_passed.iterrows():
                    title_clean = str(row['Title']).strip().lower().replace(" ", "")
                    baseline_ranks.append(baseline_rank_map.get(title_clean, 1))
                    fuzzy_ranks.append(fuzzy_rank_map.get(title_clean, 1))

                df_passed['BaselineRank'] = baseline_ranks
                df_passed['FuzzyRank'] = fuzzy_ranks
                # Positive RankChange = fuzzy reasoning moved the record up
                # (it now ranks better/lower-numbered than the recency-only
                # baseline); negative = fuzzy reasoning moved it down.
                df_passed['RankChange'] = df_passed['BaselineRank'] - df_passed['FuzzyRank']

                df_passed = df_passed.sort_values(by='FuzzyRank').reset_index(drop=True)
            else:
                # No records passed the predicate for this dataset/scenario -
                # still build an (empty) DataFrame with the expected
                # columns so downstream code (report generator) doesn't
                # have to special-case a totally empty result.
                df_passed = pd.DataFrame(columns=list(df.columns) + [
                    'OriginalIndex', 'RecordID', 'PredicatePassed', 'TopicClass', 'Reason', 'Dataset',
                    'TopicPredicateMatch', 'YearPredicateMatch', 'FormatPredicateMatch', 'PricePredicateMatch',
                    'DeptPredicateMatch', 'QtyPredicateMatch', 'EdPredicateMatch', 'fuzzy_score',
                    'topic_relevance', 'recency_score', 'affordability_score', 'format_suitability',
                    'mu_modern', 'mu_recent', 'mu_old', 'mu_cheap', 'mu_moderate', 'mu_expensive',
                    'details', 'BaselineRank', 'FuzzyRank', 'RankChange'
                ])

            # Scenario-specific display limits: Scenario 1 asks for up to
            # 5 records per dataset; Scenario 2 asks for all "Current
            # Subscription" (Dataset A) records plus up to 10 for the
            # others, per the assessment's required-output rules.
            if scenario_id == 1:
                df_top = df_passed.head(5).copy()
            else:
                if name == 'A':
                    df_top = df_passed.copy()
                else:
                    df_top = df_passed.head(10).copy()

            results[name] = {
                'passed_full': df_passed,
                'passed_top': df_top,
                'rejected': df_rejected,
                'all': df_all
            }

        return results

def np_isnan(val):
    """Safe NaN check that tolerates non-numeric input by returning False
    instead of raising."""
    try:
        import numpy as np
        return np.isnan(val)
    except:
        return False
