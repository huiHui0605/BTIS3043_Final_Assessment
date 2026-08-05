import numpy as np

class FuzzyEngine:
    """
    Implements the fuzzy reasoning layer of the system.

    Where PredicateEngine answers a hard yes/no ("does this record satisfy
    the query?"), FuzzyEngine takes only the records that already passed
    the predicate stage and scores *how well* they satisfy the department's
    softer preferences (relevance strength, how recent, how affordable,
    how suitable the format is, etc.) using membership functions that
    return a degree of truth in [0.0, 1.0] rather than a strict boolean.
    """
    def __init__(self):
        pass

    def calculate_recency_score(self, year):
        """Membership function for Recency (linear ramp between 2018 and 2024)"""
        if year is None or np_isnan(year):
            return 0.0
        try:
            year = int(year)
        except:
            return 0.0
        if year >= 2024:
            return 1.0
        elif year <= 2018:
            return 0.0
        else:
            # Linear interpolation: a year exactly halfway between 2018
            # and 2024 gets a score of 0.5, etc.
            return (year - 2018) / 6.0

    def membership_modern_year(self, year):
        """Membership function for 'Modern' Year (linear ramp up: 0 at <=2018, 1 at >=2024)"""
        return self.calculate_recency_score(year)

    def membership_recent_year(self, year):
        """Membership function for 'Recent' Year (triangular centered at 2021: 0 at 2018, 1 at 2021, 0 at 2024)"""
        # Triangular shape: membership rises from 2018 to a peak at 2021,
        # then falls back down to 2024 - i.e. "recent" (as distinct from
        # "modern"/"old") peaks around the midpoint of the window rather
        # than at either extreme.
        if year is None or np_isnan(year):
            return 0.0
        try:
            year = float(year)
        except:
            return 0.0
        if year <= 2018 or year >= 2024:
            return 0.0
        elif year <= 2021:
            return (year - 2018) / 3.0
        else:
            return (2024 - year) / 3.0

    def membership_old_year(self, year):
        """Membership function for 'Old' Year (linear ramp down: 1 at <=2018, 0 at >=2024)"""
        # Mirror image of membership_modern_year - "old" is highest for
        # anything at or before 2018, fading to 0 by 2024.
        if year is None or np_isnan(year):
            return 0.0
        try:
            year = float(year)
        except:
            return 0.0
        if year <= 2018:
            return 1.0
        elif year >= 2024:
            return 0.0
        else:
            return (2024 - year) / 6.0

    def calculate_affordability_score(self, price):
        """Membership function for Affordability / 'Cheap' Price (linear ramp down: 1 at <=100, 0 at >=300)"""
        if price is None or np_isnan(price):
            return 0.0
        try:
            price = float(price)
        except:
            return 0.0
        if price <= 100:
            return 1.0
        elif price >= 300:
            return 0.0
        else:
            # Linear interpolation between the "definitely affordable"
            # ($100) and "definitely not affordable" ($300) anchors.
            return (300 - price) / 200.0

    def membership_cheap_price(self, price):
        """Membership function for 'Cheap' Price (linear ramp down: 1 at <=100, 0 at >=300)"""
        return self.calculate_affordability_score(price)

    def membership_moderate_price(self, price):
        """Membership function for 'Moderate' Price (triangular centered at 200: 0 at 100, 1 at 200, 0 at 300)"""
        # Same triangular pattern as membership_recent_year, but for
        # price: "moderate" peaks at the midpoint ($200) between the cheap
        # and expensive anchors.
        if price is None or np_isnan(price):
            return 0.0
        try:
            price = float(price)
        except:
            return 0.0
        if price <= 100 or price >= 300:
            return 0.0
        elif price <= 200:
            return (price - 100) / 100.0
        else:
            return (300 - price) / 100.0

    def membership_expensive_price(self, price):
        """Membership function for 'Expensive' Price (linear ramp up: 0 at <=100, 1 at >=300)"""
        # Mirror image of membership_cheap_price.
        if price is None or np_isnan(price):
            return 0.0
        try:
            price = float(price)
        except:
            return 0.0
        if price <= 100:
            return 0.0
        elif price >= 300:
            return 1.0
        else:
            return (price - 100) / 200.0

    def calculate_recency_score_with_mfs(self, year):
        """Returns (score, mu_modern, mu_recent, mu_old)"""
        # Convenience wrapper that bundles the crisp recency score
        # together with all three named membership degrees ("modern",
        # "recent", "old"), so callers that want the full fuzzy-set
        # breakdown (e.g. for reporting) don't need four separate calls.
        score = self.calculate_recency_score(year)
        mu_modern = self.membership_modern_year(year)
        mu_recent = self.membership_recent_year(year)
        mu_old = self.membership_old_year(year)
        return score, mu_modern, mu_recent, mu_old

    def calculate_affordability_score_with_mfs(self, price):
        """Returns (score, mu_cheap, mu_moderate, mu_expensive)"""
        # Same idea as calculate_recency_score_with_mfs, but for price.
        score = self.calculate_affordability_score(price)
        mu_cheap = self.membership_cheap_price(price)
        mu_moderate = self.membership_moderate_price(price)
        mu_expensive = self.membership_expensive_price(price)
        return score, mu_cheap, mu_moderate, mu_expensive

    def calculate_format_suitability(self, format_val, dataset_type):
        """Calculates format suitability membership degree"""
        # Dataset A has no format field of its own (it's the "current
        # subscriptions" list, implicitly all eBooks already), so format
        # suitability is trivially maxed out for it.
        if dataset_type == 'A':
            return 1.0
        if not format_val or not isinstance(format_val, str) or str(format_val).strip() == "" or format_val == "Unknown Format":
            # Unknown/missing format: treated as a neutral 0.5 rather than
            # penalising the record outright for missing data.
            return 0.5
        f = format_val.lower()
        if 'epub' in f or 'pdf' in f:
            # ePub/PDF are considered the most broadly usable formats.
            return 1.0
        elif 'adobe' in f:
            # Adobe-Reader-locked formats are usable but less flexible.
            return 0.7
        else:
            return 0.5

    def calculate_topic_relevance_and_relationship(self, row, dataset_type, topic_class):
        """
        Determines fuzzy topic relevance membership and relationship text based on Scenario and keywords.

        Unlike the predicate layer (which only needs a yes/no topic
        match), the fuzzy layer needs a *graded* relevance score so that,
        e.g., a book classified under the exact "Artificial Intelligence"
        discipline can outrank one that merely mentions an AI keyword in
        its title. `topic_class` (passed in from the predicate result)
        is used only to work out which scenario's scoring rules apply.
        """
        title = str(row.get('Title', '')).lower()

        # Determine Scenario based on topic_class
        if topic_class in ["Directly AI-related", "Programming Support", "Mathematical Support"]:
            scenario_id = 1
        else:
            scenario_id = 2

        if scenario_id == 1:
            # Check for exact Artificial Intelligence discipline match:
            # the strongest possible relevance signal is the record being
            # formally classified under an "Artificial Intelligence"
            # discipline field, rather than just mentioning it in the title.
            is_ai_direct_discipline = False
            if dataset_type == 'B':
                l3 = str(row.get('Discipline (Level 3)', '')).strip()
                l4 = str(row.get('Discipline (Level 4)', '')).strip()
                if l3 == "Artificial Intelligence" or l4 == "Artificial Intelligence":
                    is_ai_direct_discipline = True
            elif dataset_type == 'C':
                disc = str(row.get('Discipline', '')).strip()
                if disc == "Artificial Intelligence":
                    is_ai_direct_discipline = True

            if is_ai_direct_discipline:
                # Perfect relevance score for a formally-classified AI title.
                return 1.0, "AI-direct"

            # Check AI keywords in Title or Discipline
            check_text = title
            if dataset_type == 'B':
                check_text += " " + " ".join([str(row.get(f'Discipline (Level {i})', '')) for i in range(1, 5)])
            elif dataset_type == 'C':
                disc_val = str(row.get('Discipline', ''))
                if disc_val != "IT, Programming, Web Development":
                    check_text += " " + str(row.get('Category', '')) + " " + disc_val

            # Reuse the predicate engine's keyword lists/matcher rather
            # than duplicating them, so both layers stay in sync.
            from predicate_engine import PredicateEngine, KEYWORDS_AI, KEYWORDS_PROGRAMMING, KEYWORDS_MATHEMATICS
            pe = PredicateEngine()

            # Graded relevance: AI keyword match scores highest (0.85,
            # just under the "formally classified" 1.0), programming
            # support next (0.60), maths support lowest of the three
            # accepted categories (0.55) - reflecting how directly each
            # relates to the department's core AI teaching interest.
            ai_matches = pe.check_keywords(check_text, KEYWORDS_AI)
            if ai_matches:
                return 0.85, "AI-direct"

            prog_matches = pe.check_keywords(check_text, KEYWORDS_PROGRAMMING)
            if prog_matches:
                return 0.60, "Programming support"

            math_matches = pe.check_keywords(check_text, KEYWORDS_MATHEMATICS)
            if math_matches:
                return 0.55, "Mathematical support"

            return 0.0, "None"

        else:  # scenario_id == 2
            # Check for exact Computer Security discipline match (same
            # idea as the AI-direct-discipline check above, for Scenario 2).
            is_cs_direct_discipline = False
            if dataset_type == 'B':
                l3 = str(row.get('Discipline (Level 3)', '')).strip()
                l4 = str(row.get('Discipline (Level 4)', '')).strip()
                if l3 == "Computer Security" or l4 == "Computer Security":
                    is_cs_direct_discipline = True
            elif dataset_type == 'C':
                disc = str(row.get('Discipline', ''))
                if disc == "Computer Security":
                    is_cs_direct_discipline = True

            if is_cs_direct_discipline:
                return 1.0, "Direct security relevance"

            # Check keywords in Title or Discipline
            check_text = title
            if dataset_type == 'B':
                check_text += " " + " ".join([str(row.get(f'Discipline (Level {i})', '')) for i in range(1, 5)])
            elif dataset_type == 'C':
                disc_val = str(row.get('Discipline', ''))
                if disc_val != "IT, Programming, Web Development":
                    check_text += " " + str(row.get('Category', '')) + " " + disc_val

            from predicate_engine import PredicateEngine, DIRECT_SECURITY_KWS, GENERIC_SECURITY_KWS
            pe = PredicateEngine()

            # Direct security keyword match, or a generic "security" term
            # confirmed by computing context, both score 0.85 (just under
            # the 1.0 reserved for formal "Computer Security" discipline
            # classification).
            direct_matches = pe.check_keywords(check_text, DIRECT_SECURITY_KWS)
            if direct_matches:
                return 0.85, "Direct security relevance"

            generic_matches = pe.check_keywords(check_text, GENERIC_SECURITY_KWS)
            if generic_matches:
                context_ok = False
                cs_words = ["computing", "computer", "engineering", "information technology", "cs/it", "it,", "software", "network", "digital", "data communication", "database"]
                if dataset_type == 'B':
                    disc_text = " ".join([str(row.get(f'Discipline (Level {i})', '')) for i in range(1, 5)])
                elif dataset_type == 'C':
                    disc_val = str(row.get('Discipline', ''))
                    if disc_val != "IT, Programming, Web Development":
                        disc_text = str(row.get('Category', '')) + " " + disc_val
                    else:
                        disc_text = ""
                else:
                    disc_text = ""
                if disc_text:
                    context_ok = any(w in disc_text.lower() for w in cs_words)
                else:
                    context_ok = any(w in title for w in cs_words)
                if context_ok:
                    return 0.85, "Direct security relevance"

            # Check related security terms: lower relevance score (0.55)
            # for topics that support security work (forensics, incident
            # response, privacy, disaster recovery) without being core
            # cybersecurity content themselves.
            related_kws = ["forensics", "incident response", "privacy", "disaster recovery"]
            if any(w in title for w in related_kws):
                return 0.55, "Related (forensics/incident response/privacy)"

            return 0.0, "None"

    def evaluate_ebook(self, row, topic_class, dataset_type):
        """
        Evaluates an eBook record and returns its fuzzy score, details, and membership levels.

        This is the main entry point other modules call. It combines the
        individual fuzzy criteria (topic relevance, recency, format
        suitability, and - depending on which fields the dataset actually
        has - collection support or affordability) into one weighted
        Fuzzy_Score per record, using a defuzzification-by-weighted-sum
        approach so results can be ranked on a single comparable number.
        """
        # 1. Get Topic Relevance and Relationship
        topic_rel, relationship = self.calculate_topic_relevance_and_relationship(row, dataset_type, topic_class)

        # 2. Get Recency Score
        # Each dataset names its publication-year column differently, so
        # pick the right column per dataset_type before scoring it.
        year = None
        if dataset_type == 'A':
            year = row.get('Copyright Year', None)
        elif dataset_type == 'B':
            year = row.get('Copyright', None)
        elif dataset_type == 'C':
            year = row.get('Copyright Year', None)

        recency_score = self.calculate_recency_score(year)
        _, mu_modern, mu_recent, mu_old = self.calculate_recency_score_with_mfs(year)

        # 3. Get Format Suitability
        fmt = row.get('eBook Format', '') if dataset_type in ['B', 'C'] else 'eBook'
        format_suit = self.calculate_format_suitability(fmt, dataset_type)

        # 4. Get Collection Support (Dataset A only)
        # Dataset A represents books the library already holds, so instead
        # of affordability/format, it's scored on how many copies are
        # already in the collection (more copies = stronger existing
        # institutional support for the title).
        collection_support = None
        if dataset_type == 'A':
            qty = row.get('Quantity', 1)
            try:
                qty = int(qty)
            except:
                qty = 1
            if qty >= 3:
                collection_support = 1.0
            elif qty == 2:
                collection_support = 0.6
            else:
                collection_support = 0.3

        # 5. Get Affordability (Only Dataset C has prices)
        # The overall weighting scheme differs per dataset because each
        # dataset offers a different set of usable attributes - Dataset C
        # is the only one with price data, so it's the only one that
        # includes an affordability component; Dataset A has no format or
        # price data, so it substitutes collection support instead.
        if dataset_type == 'C':
            price = row.get('April List Price (USD)', row.get('Price', None))
            affordability_score, mu_cheap, mu_moderate, mu_expensive = self.calculate_affordability_score_with_mfs(price)
            # Weights: Topic 40%, Recency 25%, Affordability 20%, Format 15%
            final_score = (0.40 * topic_rel) + (0.25 * recency_score) + (0.20 * affordability_score) + (0.15 * format_suit)
            eval_details = f"Topic={topic_rel:.2f}, Recency={recency_score:.2f}, Price={affordability_score:.2f}, Format={format_suit:.2f}"
        else:
            price = None
            affordability_score = None
            mu_cheap = 0.0
            mu_moderate = 0.0
            mu_expensive = 0.0
            if dataset_type == 'A':
                # Weights: Topic 60%, Recency 25%, Support 15%
                # Topic relevance is weighted most heavily here since
                # Dataset A has the fewest independent signals available.
                final_score = (0.60 * topic_rel) + (0.25 * recency_score) + (0.15 * collection_support)
                eval_details = f"Topic={topic_rel:.2f}, Recency={recency_score:.2f}, Support={collection_support:.2f}"
            else:  # Dataset B
                # Weights: Topic 50%, Recency 30%, Format 20%
                final_score = (0.50 * topic_rel) + (0.30 * recency_score) + (0.20 * format_suit)
                eval_details = f"Topic={topic_rel:.2f}, Recency={recency_score:.2f}, Format={format_suit:.2f}"

        final_score = round(final_score, 3)
        # Note: several fields are duplicated under two different key
        # styles (e.g. 'fuzzy_score' and 'Fuzzy_Score') so both the
        # internal ranking code (scenarios.py, which expects lowercase
        # keys) and the Excel report generator (which expects the
        # Title_Case display names) can read this dict without either
        # side needing to translate the other's naming convention.
        return {
            'fuzzy_score': final_score,
            'Fuzzy_Score': final_score,
            'topic_relevance': topic_rel,
            'Relevance': topic_rel,
            'recency_score': recency_score,
            'Recency': recency_score,
            'affordability_score': affordability_score,
            'Affordability': affordability_score,
            'format_suitability': format_suit,
            'Format_Suit': format_suit,
            'Collection_Support': collection_support,
            'Relationship': relationship,
            'details': eval_details,
            'raw_year': year,
            'raw_price': price,
            'mu_modern': mu_modern,
            'mu_recent': mu_recent,
            'mu_old': mu_old,
            'mu_cheap': mu_cheap,
            'mu_moderate': mu_moderate,
            'mu_expensive': mu_expensive
        }

def np_isnan(val):
    """Safe NaN check that tolerates non-numeric input by returning False
    instead of raising (see predicate_engine.np_isnan for the same
    pattern)."""
    try:
        import numpy as np
        return np.isnan(val)
    except:
        return False
