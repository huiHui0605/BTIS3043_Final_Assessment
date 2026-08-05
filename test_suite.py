import unittest
import os
import pandas as pd
import numpy as np
from data_loader import DataLoader
from predicate_engine import PredicateEngine
from fuzzy_engine import FuzzyEngine
from scenarios import ScenarioEvaluator

class TestBookRetrievalSystem(unittest.TestCase):
    """
    Basic regression/sanity tests for the whole pipeline: confirms the
    loaders produce usable data, the predicate engine classifies obvious
    example titles correctly, fuzzy membership functions always stay
    within the valid [0, 1] range, and a full end-to-end evaluation run
    produces the expected result structure.
    """
    @classmethod
    def setUpClass(cls):
        # Shared across all test methods (rather than re-created per
        # test) since these objects are stateless/cheap to reuse and a
        # full ScenarioEvaluator run in particular is expensive to redo
        # for every single test.
        cls.loader = DataLoader()
        cls.pred_engine = PredicateEngine()
        cls.fuzzy_engine = FuzzyEngine()
        cls.evaluator = ScenarioEvaluator()

    def test_data_loader(self):
        """Test loading and cleaning datasets"""
        # Dataset A
        # Confirms the file loads, isn't empty, and that a couple of the
        # columns load_dataset_a() is expected to create/clean are present.
        df_a = self.loader.load_dataset_a()
        self.assertFalse(df_a.empty)
        self.assertIn('Copyright Year', df_a.columns)
        self.assertIn('Recommended by', df_a.columns)

        # Dataset B
        df_b = self.loader.load_dataset_b()
        self.assertFalse(df_b.empty)
        self.assertIn('Copyright', df_b.columns)
        self.assertIn('Discipline (Level 4)', df_b.columns)

        # Dataset C
        df_c = self.loader.load_dataset_c()
        self.assertFalse(df_c.empty)
        self.assertIn('Copyright Year', df_c.columns)
        self.assertIn('April List Price (USD)', df_c.columns)

    def test_predicate_engine_sc1(self):
        """Test predicate logic for Scenario 1"""
        # Test AI match: a title that plainly names "Artificial
        # Intelligence" should pass Scenario 1 and be classified as
        # directly AI-related, not merely programming/math support.
        row_ai = {'Title': 'Introduction to Artificial Intelligence', 'Copyright': 2024, 'eBook Format': 'ePub'}
        passed, topic, reason, pred_details = self.pred_engine.evaluate_scenario_1(row_ai, 'B')
        self.assertTrue(passed)
        self.assertEqual(topic, 'Directly AI-related')

        # Test Programming match: a Python title (no AI keywords) should
        # still pass, but be classified as programming support instead.
        row_prog = {'Title': 'Python for Beginners', 'Copyright': 2023, 'eBook Format': 'PDF'}
        passed, topic, reason, pred_details = self.pred_engine.evaluate_scenario_1(row_prog, 'B')
        self.assertTrue(passed)
        self.assertEqual(topic, 'Programming Support')

        # Test Math match: similarly, a maths-only title should pass as
        # mathematical support.
        row_math = {'Title': 'Linear Algebra and Calculus', 'Copyright': 2022, 'eBook Format': 'ePub'}
        passed, topic, reason, pred_details = self.pred_engine.evaluate_scenario_1(row_math, 'B')
        self.assertTrue(passed)
        self.assertEqual(topic, 'Mathematical Support')

        # Test Fail cases (old year in Scenario 2): a security title
        # published before 2010 should be rejected by Scenario 2's hard
        # year predicate, even though its topic itself matches.
        row_old = {'Title': 'Computer Security 101', 'Copyright': 2008, 'eBook Format': 'ePub'}
        passed, topic, reason, pred_details = self.pred_engine.evaluate_scenario_2(row_old, 'B')
        self.assertFalse(passed)

    def test_predicate_engine_sc2(self):
        """Test predicate logic for Scenario 2"""
        # Test Security match: an unambiguous "Computer Security" title
        # from 2025 should clearly pass.
        row_sec = {'Title': 'Handbook of Computer Security', 'Copyright': 2025, 'eBook Format': 'ePub'}
        passed, topic, reason, pred_details = self.pred_engine.evaluate_scenario_2(row_sec, 'B')
        self.assertTrue(passed)
        self.assertEqual(topic, 'Cybersecurity / Secure Computing')

        # Test non-match: an unrelated psychology title should be
        # rejected outright (no security keywords at all).
        row_non = {'Title': 'Social Psychology Fundamentals', 'Copyright': 2024, 'eBook Format': 'ePub'}
        passed, topic, reason, pred_details = self.pred_engine.evaluate_scenario_2(row_non, 'B')
        self.assertFalse(passed)

    def test_fuzzy_memberships(self):
        """Test that fuzzy membership values fall within [0, 1]"""
        # Recency: sweep a range of years spanning below, within and
        # above the 2018-2024 scoring window, and confirm every named
        # membership function (modern/recent/old) plus the combined
        # recency score always stays within the valid fuzzy [0, 1] range.
        for year in [2010, 2018, 2020, 2022, 2025, 2026]:
            self.assertTrue(0.0 <= self.fuzzy_engine.membership_modern_year(year) <= 1.0)
            self.assertTrue(0.0 <= self.fuzzy_engine.membership_recent_year(year) <= 1.0)
            self.assertTrue(0.0 <= self.fuzzy_engine.membership_old_year(year) <= 1.0)
            rec = self.fuzzy_engine.calculate_recency_score(year)
            self.assertTrue(0.0 <= rec <= 1.0)

        # Affordability: same idea, sweeping prices below, within and
        # above the $100-$300 scoring window.
        for price in [50, 120, 190, 250, 320]:
            self.assertTrue(0.0 <= self.fuzzy_engine.membership_cheap_price(price) <= 1.0)
            self.assertTrue(0.0 <= self.fuzzy_engine.membership_moderate_price(price) <= 1.0)
            self.assertTrue(0.0 <= self.fuzzy_engine.membership_expensive_price(price) <= 1.0)
            aff = self.fuzzy_engine.calculate_affordability_score(price)
            self.assertTrue(0.0 <= aff <= 1.0)

    def test_evaluator(self):
        """Test full scenario evaluation output structures"""
        # End-to-end smoke test: run the real evaluation pipeline (against
        # the actual dataset files on disk) and check the result dict has
        # an entry for every dataset, and that a passed record in Dataset
        # C carries all the ranking columns the report generator expects.
        res_sc1 = self.evaluator.run_evaluation(scenario_id=1)
        self.assertIn('A', res_sc1)
        self.assertIn('B', res_sc1)
        self.assertIn('C', res_sc1)

        # Verify columns of processed datasets
        df_passed_c = res_sc1['C']['passed_full']
        if not df_passed_c.empty:
            self.assertIn('fuzzy_score', df_passed_c.columns)
            self.assertIn('FuzzyRank', df_passed_c.columns)
            self.assertIn('BaselineRank', df_passed_c.columns)
            self.assertIn('RankChange', df_passed_c.columns)

if __name__ == '__main__':
    unittest.main()
