"""
tests/test_analyzer.py
======================
Tests for the Quiz Performance Analyzer.

Only Python's built-in ``unittest`` module is used - no pytest and no other
testing framework.

Run the tests from the project folder:

    python -m unittest discover -s tests -v

or directly:

    python tests/test_analyzer.py
"""

import os
import shutil
import sys
import tempfile
import unittest

import matplotlib
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

# The project modules live one folder above this test file.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Charts must be created without opening a window while testing.
matplotlib.use("Agg", force=True)

import analyzer          # noqa: E402  (import after the path setup)
import data_manager      # noqa: E402
import visualizer        # noqa: E402


# --------------------------------------------------------------------------- #
# Shared test data
# --------------------------------------------------------------------------- #

def sample_records():
    """Return a small list of raw records used by most tests.

    Round 1 is easy (90 % average), round 2 is moderate (60 %), round 3 is
    difficult (45 %). Priya scores better than Rahul on average.
    """
    rows = [
        ("Rahul", "Round 1", 1, 10, 8, "2026-10-01"),
        ("Rahul", "Round 1", 2, 10, 9, "2026-10-02"),
        ("Rahul", "Round 2", 1, 10, 6, "2026-10-03"),
        ("Rahul", "Round 2", 2, 10, 5, "2026-10-04"),
        ("Rahul", "Round 3", 1, 10, 4, "2026-10-05"),
        ("Priya", "Round 1", 1, 10, 9, "2026-10-01"),
        ("Priya", "Round 1", 2, 10, 10, "2026-10-02"),
        ("Priya", "Round 2", 1, 10, 7, "2026-10-03"),
        ("Priya", "Round 2", 2, 10, 6, "2026-10-04"),
        ("Priya", "Round 3", 1, 10, 5, "2026-10-05"),
    ]
    return [{"player_name": name, "round_name": round_label, "attempt": attempt,
             "total_questions": total, "correct_answers": correct, "date": day}
            for name, round_label, attempt, total, correct, day in rows]


def sample_dataframe():
    """Return the sample records as a validated DataFrame."""
    return data_manager.validate_dataframe(pd.DataFrame(sample_records(),
                                                        columns=data_manager.FIELDS))


# --------------------------------------------------------------------------- #
# 1. Score and accuracy
# --------------------------------------------------------------------------- #

class TestScoreCalculation(unittest.TestCase):

    def test_score_calculation(self):
        self.assertEqual(analyzer.calculate_score(8, 10), 80.0)
        self.assertEqual(analyzer.calculate_score(0, 10), 0.0)
        self.assertEqual(analyzer.calculate_score(10, 10), 100.0)
        self.assertEqual(analyzer.calculate_score(1, 3), 33.33)
        self.assertEqual(analyzer.calculate_score("7", "10"), 70.0)

    def test_accuracy_calculation(self):
        self.assertEqual(analyzer.calculate_accuracy(8, 10), 80.0)
        self.assertEqual(analyzer.calculate_accuracy(0, 4), 0.0)

    def test_invalid_score_input(self):
        with self.assertRaises(ValueError):          # division by zero
            analyzer.calculate_score(5, 0)
        with self.assertRaises(ValueError):          # negative answers
            analyzer.calculate_score(-1, 10)
        with self.assertRaises(ValueError):          # more answers than questions
            analyzer.calculate_score(11, 10)
        with self.assertRaises(ValueError):          # text instead of numbers
            analyzer.calculate_score("abc", 10)

    def test_vectorised_score_calculation(self):
        scores = analyzer.calculate_score_array([8, 5, 10], [10, 10, 10])
        self.assertIsInstance(scores, np.ndarray)
        np.testing.assert_allclose(scores, [80.0, 50.0, 100.0])

    def test_scores_are_calculated_when_loading(self):
        dataframe = sample_dataframe()
        self.assertEqual(dataframe.loc[0, "score"], 80.0)
        self.assertEqual(dataframe.loc[0, "accuracy"], 80.0)


# --------------------------------------------------------------------------- #
# 2. Averages and other statistical values
# --------------------------------------------------------------------------- #

class TestStatistics(unittest.TestCase):

    def test_average_score(self):
        self.assertEqual(analyzer.calculate_average_score([80, 90, 70]), 80.0)
        self.assertEqual(analyzer.calculate_average_score([60]), 60.0)

    def test_average_accuracy(self):
        self.assertEqual(analyzer.calculate_average_accuracy([50, 100]), 75.0)

    def test_average_of_empty_list(self):
        with self.assertRaises(ValueError):
            analyzer.calculate_average_score([])

    def test_standard_deviation(self):
        self.assertEqual(analyzer.calculate_std_deviation([80, 80, 80]), 0.0)
        self.assertAlmostEqual(analyzer.calculate_std_deviation([0, 100]), 50.0)

    def test_classify_difficulty(self):
        self.assertEqual(analyzer.classify_difficulty(20), analyzer.LABEL_DIFFICULT)
        self.assertEqual(analyzer.classify_difficulty(49.99), analyzer.LABEL_DIFFICULT)
        self.assertEqual(analyzer.classify_difficulty(50), analyzer.LABEL_MODERATE)
        self.assertEqual(analyzer.classify_difficulty(70), analyzer.LABEL_MODERATE)
        self.assertEqual(analyzer.classify_difficulty(70.01), analyzer.LABEL_EASY)
        self.assertEqual(analyzer.classify_difficulty(95), analyzer.LABEL_EASY)


# --------------------------------------------------------------------------- #
# 3. Player statistics
# --------------------------------------------------------------------------- #

class TestPlayerStatistics(unittest.TestCase):

    def setUp(self):
        self.dataframe = sample_dataframe()

    def test_player_statistics(self):
        stats = analyzer.get_player_statistics(self.dataframe, "Rahul")
        self.assertEqual(stats["attempts"], 5)
        self.assertEqual(stats["average_score"], 64.0)
        self.assertEqual(stats["average_accuracy"], 64.0)
        self.assertEqual(stats["best_score"], 90.0)
        self.assertEqual(stats["lowest_score"], 40.0)
        self.assertEqual(stats["best_attempt"], ("Round 1", 2, 90.0))
        self.assertEqual(stats["questions_answered"], 50)
        self.assertEqual(stats["correct_answers"], 32)
        self.assertIn("Round 1", stats["rounds"])
        self.assertEqual(stats["rounds"]["Round 1"]["average_accuracy"], 85.0)
        self.assertEqual(len(stats["scores"]), 5)

    def test_unknown_player(self):
        with self.assertRaises(ValueError):
            analyzer.get_player_statistics(self.dataframe, "Nobody")

    def test_player_progress_is_ordered(self):
        progress = analyzer.get_player_progress(self.dataframe, "Rahul")
        self.assertEqual(len(progress), 5)
        self.assertEqual(progress[0], ("Round 1 (attempt 1)", 80.0, 80.0))
        self.assertEqual(progress[-1][0], "Round 3 (attempt 1)")

    def test_find_best_player(self):
        best_player, best_average = analyzer.find_best_player(self.dataframe)
        self.assertEqual(best_player, "Priya")
        self.assertEqual(best_average, 74.0)

    def test_players_average_scores(self):
        averages = analyzer.get_players_average_scores(self.dataframe)
        self.assertEqual(set(averages.keys()), {"Rahul", "Priya"})


# --------------------------------------------------------------------------- #
# 4. Round statistics and difficult rounds
# --------------------------------------------------------------------------- #

class TestRoundAnalysis(unittest.TestCase):

    def setUp(self):
        self.dataframe = sample_dataframe()

    def test_round_statistics(self):
        stats = analyzer.get_round_statistics(self.dataframe, "Round 3")
        self.assertEqual(stats["attempts"], 2)
        self.assertEqual(stats["average_score"], 45.0)
        self.assertEqual(stats["average_accuracy"], 45.0)
        self.assertEqual(stats["highest_score"], 50.0)
        self.assertEqual(stats["lowest_score"], 40.0)
        self.assertEqual(stats["difficulty"], analyzer.LABEL_DIFFICULT)
        self.assertEqual(stats["players"], ["Priya", "Rahul"])

    def test_unknown_round(self):
        with self.assertRaises(ValueError):
            analyzer.get_round_statistics(self.dataframe, "Round 9")

    def test_difficult_round_detection(self):
        rounds = analyzer.find_difficult_rounds(self.dataframe)
        names = [item["round_name"] for item in rounds]
        labels = [item["difficulty"] for item in rounds]

        # Hardest round comes first.
        self.assertEqual(names, ["Round 3", "Round 2", "Round 1"])
        self.assertEqual(labels, [analyzer.LABEL_DIFFICULT,
                                  analyzer.LABEL_MODERATE,
                                  analyzer.LABEL_EASY])
        self.assertEqual(rounds[0]["average_accuracy"], 45.0)
        self.assertEqual(rounds[-1]["average_accuracy"], 90.0)

    def test_round_difficulty_map(self):
        difficulty_map = analyzer.get_round_difficulty_map(self.dataframe)
        self.assertEqual(difficulty_map["Round 2"], 60.0)

    def test_find_best_round(self):
        best_round, best_accuracy = analyzer.find_best_round(self.dataframe)
        self.assertEqual(best_round, "Round 1")
        self.assertEqual(best_accuracy, 90.0)


# --------------------------------------------------------------------------- #
# 5. Comparisons
# --------------------------------------------------------------------------- #

class TestComparison(unittest.TestCase):

    def setUp(self):
        self.dataframe = sample_dataframe()

    def test_player_comparison(self):
        comparison = analyzer.compare_players(self.dataframe, ["Rahul", "Priya"])
        self.assertEqual(comparison["Rahul"]["average_score"], 64.0)
        self.assertEqual(comparison["Priya"]["average_score"], 74.0)
        self.assertEqual(comparison["Priya"]["best_score"], 100.0)
        self.assertEqual(comparison["Rahul"]["attempts"], 5)
        self.assertEqual(len(comparison["Rahul"]["rounds_played"]), 3)

    def test_player_comparison_needs_two_players(self):
        with self.assertRaises(ValueError):
            analyzer.compare_players(self.dataframe, ["Rahul"])

    def test_round_comparison(self):
        comparison = analyzer.compare_rounds(self.dataframe, ["Round 1", "Round 3"])
        self.assertEqual(comparison["Round 1"]["average_score"], 90.0)
        self.assertEqual(comparison["Round 1"]["difficulty"], analyzer.LABEL_EASY)
        self.assertEqual(comparison["Round 3"]["difficulty"], analyzer.LABEL_DIFFICULT)
        self.assertEqual(comparison["Round 3"]["attempts"], 2)

    def test_round_comparison_needs_two_rounds(self):
        with self.assertRaises(ValueError):
            analyzer.compare_rounds(self.dataframe, ["Round 1"])


# --------------------------------------------------------------------------- #
# 6. Searching, filtering and summary
# --------------------------------------------------------------------------- #

class TestSearchAndSummary(unittest.TestCase):

    def setUp(self):
        self.dataframe = sample_dataframe()

    def test_filter_by_player(self):
        result = analyzer.filter_results(self.dataframe, player_name="rahu")
        self.assertEqual(len(result), 5)                     # case insensitive part match
        self.assertEqual(set(result["player_name"]), {"Rahul"})

    def test_filter_by_round_and_attempt(self):
        result = analyzer.filter_results(self.dataframe, round_name="Round 1",
                                         attempt="2")
        self.assertEqual(len(result), 2)
        self.assertEqual(set(result["attempt"]), {2})

    def test_filter_with_no_match(self):
        result = analyzer.filter_results(self.dataframe, player_name="Nobody")
        self.assertEqual(len(result), 0)

    def test_filter_with_invalid_attempt(self):
        with self.assertRaises(ValueError):
            analyzer.filter_results(self.dataframe, attempt="two")
        with self.assertRaises(ValueError):
            analyzer.filter_results(self.dataframe, attempt="-1")

    def test_overall_summary(self):
        summary = analyzer.get_overall_summary(self.dataframe)
        self.assertEqual(summary["records"], 10)
        self.assertEqual(summary["players"], ["Priya", "Rahul"])
        self.assertEqual(summary["rounds"], ["Round 1", "Round 2", "Round 3"])
        self.assertEqual(summary["best_player"][0], "Priya")
        self.assertEqual(summary["easiest_round"][0], "Round 1")

    def test_empty_dataframe_is_reported(self):
        empty = data_manager.validate_dataframe(None)
        for function in (analyzer.find_difficult_rounds,
                         analyzer.find_best_player,
                         analyzer.get_overall_summary):
            with self.assertRaises(ValueError):
                function(empty)


# --------------------------------------------------------------------------- #
# 7. Input validation
# --------------------------------------------------------------------------- #

class TestInputValidation(unittest.TestCase):

    def test_valid_input(self):
        values = data_manager.validate_result("Rahul", "Round 1", "1", "10", "8",
                                              "2026-10-07")
        self.assertEqual(values, ("Rahul", "Round 1", 1, 10, 8, "2026-10-07"))

    def test_empty_names(self):
        with self.assertRaises(ValueError):
            data_manager.validate_result("  ", "Round 1", "1", "10", "8", "2026-10-07")
        with self.assertRaises(ValueError):
            data_manager.validate_result("Rahul", "", "1", "10", "8", "2026-10-07")

    def test_attempt_must_be_positive_integer(self):
        with self.assertRaises(ValueError):
            data_manager.validate_result("R", "Round 1", "0", "10", "8", "2026-10-07")
        with self.assertRaises(ValueError):
            data_manager.validate_result("R", "Round 1", "one", "10", "8", "2026-10-07")

    def test_total_questions_must_be_positive(self):
        with self.assertRaises(ValueError):
            data_manager.validate_result("R", "Round 1", "1", "0", "0", "2026-10-07")
        with self.assertRaises(ValueError):
            data_manager.validate_result("R", "Round 1", "1", "ten", "0", "2026-10-07")

    def test_correct_answers_limits(self):
        with self.assertRaises(ValueError):
            data_manager.validate_result("R", "Round 1", "1", "10", "-1", "2026-10-07")
        with self.assertRaises(ValueError):
            data_manager.validate_result("R", "Round 1", "1", "10", "11", "2026-10-07")

    def test_date_format(self):
        with self.assertRaises(ValueError):
            data_manager.validate_result("R", "Round 1", "1", "10", "8", "07-10-2026")
        with self.assertRaises(ValueError):
            data_manager.validate_result("R", "Round 1", "1", "10", "8", "")

    def test_build_record_calculates_score(self):
        record = data_manager.build_record("Rahul", "Round 1", "1", "10", "8",
                                          "2026-10-07")
        self.assertEqual(record["score"], 80.0)
        self.assertEqual(record["accuracy"], 80.0)
        self.assertEqual(record["attempt"], 1)


# --------------------------------------------------------------------------- #
# 8. File storage and persistence
# --------------------------------------------------------------------------- #

class TestDataManagerStorage(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="quiz_test_")
        self.file_path = os.path.join(self.folder, "quiz_results.csv")

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_file_is_created_automatically(self):
        self.assertFalse(data_manager.data_file_exists(self.file_path))
        data_manager.ensure_data_file(self.file_path)
        self.assertTrue(data_manager.data_file_exists(self.file_path))
        with open(self.file_path, encoding="utf-8") as handle:
            header = handle.readline().strip()
        self.assertEqual(header, ",".join(data_manager.FIELDS))

    def test_loading_a_missing_file_gives_an_empty_table(self):
        dataframe = data_manager.load_dataframe(self.file_path)
        self.assertTrue(dataframe.empty)

    def test_results_are_saved_and_stay_after_reloading(self):
        data_manager.add_result("Rahul", "Round 1", 1, 10, 8, "2026-10-07",
                                file_path=self.file_path)
        data_manager.add_result("Priya", "Round 1", 1, 10, 9, "2026-10-07",
                                file_path=self.file_path)

        # A new load simulates closing and reopening the program.
        dataframe = data_manager.load_dataframe(self.file_path)
        self.assertEqual(len(dataframe), 2)
        self.assertEqual(dataframe.loc[0, "player_name"], "Rahul")
        self.assertEqual(dataframe.loc[1, "score"], 90.0)
        self.assertEqual(data_manager.count_records(self.file_path), 2)

    def test_previous_records_are_preserved(self):
        for index in range(3):
            data_manager.add_result("Player %d" % index, "Round 1", 1, 10,
                                    index, "2026-10-07", file_path=self.file_path)
        records = data_manager.load_records(self.file_path)
        self.assertEqual(len(records), 3)
        self.assertEqual([row["player_name"] for row in records],
                         ["Player 0", "Player 1", "Player 2"])

    def test_invalid_result_is_not_written(self):
        with self.assertRaises(ValueError):
            data_manager.add_result("Rahul", "Round 1", 1, 10, 11, "2026-10-07",
                                    file_path=self.file_path)
        self.assertEqual(data_manager.count_records(self.file_path), 0)

    def test_default_date_is_today(self):
        record = data_manager.add_result("Rahul", "Round 1", 1, 10, 5,
                                         file_path=self.file_path)
        self.assertEqual(len(record["date"]), 10)         # YYYY-MM-DD

    def test_update_record_recalculates_score(self):
        data_manager.add_result("Rahul", "Round 1", 1, 10, 8, "2026-10-07",
                                file_path=self.file_path)
        updated = data_manager.update_record(0, file_path=self.file_path,
                                             correct_answers=5)
        self.assertEqual(updated["score"], 50.0)
        dataframe = data_manager.load_dataframe(self.file_path)
        self.assertEqual(dataframe.loc[0, "score"], 50.0)

    def test_delete_record(self):
        data_manager.add_result("Rahul", "Round 1", 1, 10, 8, "2026-10-07",
                                file_path=self.file_path)
        data_manager.add_result("Priya", "Round 1", 1, 10, 9, "2026-10-07",
                                file_path=self.file_path)
        data_manager.delete_record(0, file_path=self.file_path)
        dataframe = data_manager.load_dataframe(self.file_path)
        self.assertEqual(len(dataframe), 1)
        self.assertEqual(dataframe.loc[0, "player_name"], "Priya")

    def test_update_and_delete_need_existing_records(self):
        with self.assertRaises(data_manager.DataError):
            data_manager.update_record(0, file_path=self.file_path, correct_answers=1)
        with self.assertRaises(data_manager.DataError):
            data_manager.delete_record(0, file_path=self.file_path)

    def test_corrupted_rows_are_skipped(self):
        # Write a file that contains two broken rows and one correct row.
        with open(self.file_path, "w", newline="", encoding="utf-8") as handle:
            handle.write(",".join(data_manager.FIELDS) + "\n")
            handle.write("Rahul,Round 1,1,10,8,80,80,2026-10-07\n")
            handle.write("Priya,Round 1,one,ten,nine,90,90,2026-10-07\n")
            handle.write("Rahul,Round 2,1,10,11,110,110,2026-10-08\n")

        dataframe = data_manager.load_dataframe(self.file_path)
        self.assertEqual(len(dataframe), 1)
        report = data_manager.check_data_file(self.file_path)
        self.assertEqual(report["total_rows"], 3)
        self.assertEqual(report["valid_rows"], 1)
        self.assertEqual(report["skipped_rows"], 2)

    def test_missing_columns_raise_an_error(self):
        with open(self.file_path, "w", newline="", encoding="utf-8") as handle:
            handle.write("player_name,score\n")
            handle.write("Rahul,80\n")
        with self.assertRaises(data_manager.DataError):
            data_manager.load_dataframe(self.file_path)

    def test_unique_players_and_rounds(self):
        data_manager.add_result("Rahul", "Round 1", 1, 10, 8, "2026-10-07",
                                file_path=self.file_path)
        data_manager.add_result("Priya", "Round 2", 1, 10, 9, "2026-10-07",
                                file_path=self.file_path)
        self.assertEqual(data_manager.get_unique_players(
            data_manager.load_dataframe(self.file_path)), ["Priya", "Rahul"])
        self.assertEqual(data_manager.get_unique_rounds(
            data_manager.load_dataframe(self.file_path)), ["Round 1", "Round 2"])


# --------------------------------------------------------------------------- #
# 9. Visualizations
# --------------------------------------------------------------------------- #

class TestVisualizer(unittest.TestCase):

    def setUp(self):
        self.dataframe = sample_dataframe()
        self.folder = tempfile.mkdtemp(prefix="quiz_charts_")

    def tearDown(self):
        plt.close("all")            # keep the test run free of open figures
        shutil.rmtree(self.folder, ignore_errors=True)

    def _save(self, figure, name):
        """Save a figure to disk so the test proves the chart was drawn."""
        path = os.path.join(self.folder, name)
        figure.savefig(path)
        self.assertTrue(os.path.isfile(path))
        self.assertGreater(os.path.getsize(path), 1000)
        return path

    def test_player_performance_chart(self):
        figure = visualizer.plot_player_performance(self.dataframe, "Rahul", show=False)
        self.assertEqual(figure.axes[0].get_xlabel(), "Round and attempt")
        self.assertEqual(figure.axes[0].get_ylabel(), "Score / Accuracy (%)")
        self.assertIn("Rahul", figure.axes[0].get_title())
        self._save(figure, "player_performance.png")

    def test_round_difficulty_chart(self):
        figure = visualizer.plot_round_difficulty(self.dataframe, show=False)
        axes = figure.axes[0]
        self.assertIn("Difficulty", axes.get_title())
        self.assertEqual(axes.get_ylabel(), "Average accuracy (%)")
        # The x axis shows the rounds from the most difficult to the easiest.
        self.assertEqual([label.get_text() for label in axes.get_xticklabels()],
                         ["Round 3", "Round 2", "Round 1"])
        self._save(figure, "round_difficulty.png")

    def test_player_comparison_chart(self):
        figure = visualizer.plot_player_comparison(self.dataframe, show=False)
        self.assertIn("Comparison", figure.axes[0].get_title())
        self._save(figure, "player_comparison.png")

    def test_charts_reject_empty_data(self):
        empty = data_manager.validate_dataframe(None)
        with self.assertRaises(ValueError):
            visualizer.plot_round_difficulty(empty, show=False)
        with self.assertRaises(ValueError):
            visualizer.plot_player_performance(empty, "Rahul", show=False)
        with self.assertRaises(ValueError):
            visualizer.plot_player_comparison(empty, show=False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
