"""
analyzer.py
===========
All calculations and statistics of the Quiz Performance Analyzer.

This module contains no user interface code and no file handling code. It works
on a validated Pandas DataFrame (see :mod:`data_manager`) and returns plain
Python dictionaries, lists, tuples and sets, so the results are easy to display
in the GUI or in a chart.

Scoring scheme
--------------
    score    = correct_answers / total_questions * 100   (percentage, 0 - 100)
    accuracy = the same percentage

Difficulty scheme (based on the average accuracy of a round)
------------------------------------------------------------
    average accuracy <  50 %  -> Difficult
    50 % <= accuracy  <= 70 % -> Moderate
    average accuracy >  70 %  -> Easy
"""

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Constants (documented difficulty thresholds)
# --------------------------------------------------------------------------- #

#: Average accuracy below this value means the round was difficult.
DIFFICULT_MAX = 50.0

#: Average accuracy up to this value means the round was moderate.
MODERATE_MAX = 70.0

LABEL_DIFFICULT = "Difficult"
LABEL_MODERATE = "Moderate"
LABEL_EASY = "Easy"

#: Message used whenever an analysis is requested without any data.
NO_DATA_MESSAGE = "No quiz results available. Please add a result first."


def _require_data(dataframe):
    """Raise a clear error when there is nothing to analyse."""
    if dataframe is None or dataframe.empty:
        raise ValueError(NO_DATA_MESSAGE)
    return dataframe


def describe_thresholds():
    """Return a short human readable explanation of the difficulty levels."""
    return ("Average accuracy below %.0f%% = Difficult, "
            "%.0f%% to %.0f%% = Moderate, above %.0f%% = Easy."
            % (DIFFICULT_MAX, DIFFICULT_MAX, MODERATE_MAX, MODERATE_MAX))


# --------------------------------------------------------------------------- #
# 1. Core calculations
# --------------------------------------------------------------------------- #

def calculate_score(correct_answers, total_questions):
    """Return the score in percent: ``correct / total * 100``.

    Raises :class:`ValueError` for impossible input (division by zero,
    negative answers, more correct answers than questions).
    """
    try:
        correct = float(correct_answers)
        total = float(total_questions)
    except (TypeError, ValueError):
        raise ValueError("Correct answers and total questions must be numbers.") from None

    if total <= 0:
        raise ValueError("Total questions must be greater than zero.")
    if correct < 0:
        raise ValueError("Correct answers cannot be negative.")
    if correct > total:
        raise ValueError("Correct answers cannot exceed total questions.")

    return float(np.round(np.divide(correct, total) * 100.0, 2))


def calculate_accuracy(correct_answers, total_questions):
    """Return the accuracy in percent.

    In this project accuracy uses the same formula as the score
    (``correct / total * 100``).
    """
    return calculate_score(correct_answers, total_questions)


def calculate_score_array(correct_answers, total_questions):
    """Vectorised score calculation for whole columns (NumPy arrays).

    Returns a NumPy array of percentages. Used by :mod:`data_manager` when it
    recalculates the stored score/accuracy values of many rows at once.
    """
    correct = np.asarray(correct_answers, dtype="float64")
    total = np.asarray(total_questions, dtype="float64")
    # Guard against division by zero without raising on the whole column.
    safe_total = np.where(total > 0, total, np.nan)
    scores = np.divide(correct, safe_total) * 100.0
    return np.round(np.nan_to_num(scores, nan=0.0), 2)


def calculate_average_score(scores):
    """Return the average of a list/tuple of scores using NumPy."""
    values = np.asarray(list(scores), dtype="float64")
    if values.size == 0:
        raise ValueError("No scores available to calculate an average.")
    return float(np.round(np.mean(values), 2))


def calculate_average_accuracy(accuracies):
    """Return the average accuracy (percentage) using NumPy."""
    return calculate_average_score(accuracies)


def calculate_std_deviation(values):
    """Return the population standard deviation of a list of numbers.

    A low value means the player is consistent; a high value means the results
    vary a lot between attempts.
    """
    numbers = np.asarray(list(values), dtype="float64")
    if numbers.size == 0:
        raise ValueError("No values available to calculate a standard deviation.")
    return float(np.round(np.std(numbers), 2))


# --------------------------------------------------------------------------- #
# 2. Difficulty
# --------------------------------------------------------------------------- #

def classify_difficulty(average_accuracy):
    """Turn an average accuracy into a difficulty label.

    Returns one of ``"Difficult"``, ``"Moderate"`` or ``"Easy"``.
    """
    try:
        value = float(average_accuracy)
    except (TypeError, ValueError):
        raise ValueError("Average accuracy must be a number.") from None

    if value < DIFFICULT_MAX:
        return LABEL_DIFFICULT
    if value <= MODERATE_MAX:
        return LABEL_MODERATE
    return LABEL_EASY


def find_difficult_rounds(dataframe):
    """List every round from the hardest to the easiest.

    Returns a list of dictionaries with the round name, average accuracy,
    average score, number of attempts and its difficulty label.
    """
    df = _require_data(dataframe)

    rounds = []                       # list of dictionaries
    for round_name in sorted(set(df["round_name"].tolist())):   # set + sorted
        round_rows = df[df["round_name"] == round_name]
        accuracies = round_rows["accuracy"].tolist()
        scores = round_rows["score"].tolist()

        rounds.append({
            "round_name": round_name,
            "attempts": int(len(round_rows)),
            "average_accuracy": calculate_average_accuracy(accuracies),
            "average_score": calculate_average_score(scores),
            "difficulty": classify_difficulty(calculate_average_accuracy(accuracies)),
        })

    # Hardest round first (lowest average accuracy).
    rounds.sort(key=lambda item: item["average_accuracy"])
    return rounds


def get_round_difficulty_map(dataframe):
    """Return a dictionary ``{round_name: average_accuracy}``."""
    return {item["round_name"]: item["average_accuracy"]
            for item in find_difficult_rounds(dataframe)}


# --------------------------------------------------------------------------- #
# 3. Player statistics
# --------------------------------------------------------------------------- #

def get_player_statistics(dataframe, player_name):
    """Return a dictionary with all statistics of one player.

    Keys: ``player``, ``attempts``, ``average_score``, ``average_accuracy``,
    ``best_score``, ``lowest_score``, ``std_deviation``, ``rounds`` (a dict with
    the average accuracy per round), ``scores`` (a list), ``best_attempt``
    (a tuple), ``questions_answered`` and ``correct_answers``.
    """
    df = _require_data(dataframe)
    player_rows = df[df["player_name"] == player_name]
    if player_rows.empty:
        raise ValueError("Player '%s' was not found in the stored results." % player_name)

    scores = player_rows["score"].tolist()             # list
    accuracies = player_rows["accuracy"].tolist()      # list

    scores_array = np.asarray(scores, dtype="float64")
    best_position = int(np.argmax(scores_array))
    best_row = player_rows.iloc[best_position]

    # Average accuracy per round: dictionary comprehension with groupby.
    rounds = {}
    for round_name, group in player_rows.groupby("round_name"):
        rounds[str(round_name)] = {
            "attempts": int(len(group)),
            "average_accuracy": calculate_average_accuracy(group["accuracy"].tolist()),
            "average_score": calculate_average_score(group["score"].tolist()),
        }

    return {
        "player": player_name,
        "attempts": int(len(player_rows)),
        "average_score": calculate_average_score(scores),
        "average_accuracy": calculate_average_accuracy(accuracies),
        "best_score": float(np.max(scores_array)),
        "lowest_score": float(np.min(scores_array)),
        "std_deviation": calculate_std_deviation(scores),
        "rounds": rounds,
        # tuple: immutable grouped values
        "best_attempt": (str(best_row["round_name"]), int(best_row["attempt"]),
                         float(best_row["score"])),
        "scores": [float(value) for value in scores],
        "questions_answered": int(player_rows["total_questions"].sum()),
        "correct_answers": int(player_rows["correct_answers"].sum()),
    }


def get_player_progress(dataframe, player_name):
    """Return the ordered performance history of one player.

    Returns a list of tuples ``(label, score, accuracy)`` sorted by date, round
    and attempt - ready to be plotted as a line chart.
    """
    df = _require_data(dataframe)
    player_rows = df[df["player_name"] == player_name].copy()
    if player_rows.empty:
        raise ValueError("Player '%s' was not found in the stored results." % player_name)

    player_rows = player_rows.sort_values(by=["date", "round_name", "attempt"])

    progress = []                      # list of tuples
    for _, row in player_rows.iterrows():
        label = "%s (attempt %d)" % (row["round_name"], int(row["attempt"]))
        progress.append((label, float(row["score"]), float(row["accuracy"])))
    return progress


def get_players_average_scores(dataframe):
    """Return a dictionary ``{player_name: average_score}`` for every player."""
    df = _require_data(dataframe)
    return {str(name): calculate_average_score(group["score"].tolist())
            for name, group in df.groupby("player_name")}


def find_best_player(dataframe):
    """Return the tuple ``(player_name, average_score)`` of the best player."""
    averages = get_players_average_scores(dataframe)
    if not averages:
        raise ValueError(NO_DATA_MESSAGE)
    names = list(averages.keys())                       # list
    values = np.asarray(list(averages.values()), dtype="float64")   # numpy array
    best_index = int(np.argmax(values))                 # numpy argmax
    return (names[best_index], float(values[best_index]))


# --------------------------------------------------------------------------- #
# 4. Round statistics
# --------------------------------------------------------------------------- #

def get_round_statistics(dataframe, round_name):
    """Return a dictionary with all statistics of one quiz round.

    Keys: ``round``, ``attempts``, ``players`` (sorted list), ``average_score``,
    ``average_accuracy``, ``highest_score``, ``lowest_score``,
    ``std_deviation``, ``difficulty`` and ``player_averages`` (a dictionary).
    """
    df = _require_data(dataframe)
    round_rows = df[df["round_name"] == round_name]
    if round_rows.empty:
        raise ValueError("Round '%s' was not found in the stored results." % round_name)

    scores = round_rows["score"].tolist()
    accuracies = round_rows["accuracy"].tolist()
    average_accuracy = calculate_average_accuracy(accuracies)

    player_averages = {}
    for name, group in round_rows.groupby("player_name"):
        player_averages[str(name)] = calculate_average_score(group["score"].tolist())

    return {
        "round": round_name,
        "attempts": int(len(round_rows)),
        "players": sorted(set(round_rows["player_name"].tolist())),   # set
        "average_score": calculate_average_score(scores),
        "average_accuracy": average_accuracy,
        "highest_score": float(np.max(np.asarray(scores, dtype="float64"))),
        "lowest_score": float(np.min(np.asarray(scores, dtype="float64"))),
        "std_deviation": calculate_std_deviation(scores),
        "difficulty": classify_difficulty(average_accuracy),
        "player_averages": player_averages,
    }


def find_best_round(dataframe):
    """Return the tuple ``(round_name, average_accuracy)`` of the best round."""
    rounds = find_difficult_rounds(dataframe)          # sorted hardest first
    best = rounds[-1]
    return (best["round_name"], best["average_accuracy"])


# --------------------------------------------------------------------------- #
# 5. Comparisons
# --------------------------------------------------------------------------- #

def compare_players(dataframe, player_names):
    """Compare two or more players.

    Returns a dictionary keyed by player name. Every value is a dictionary with
    ``average_score``, ``average_accuracy``, ``best_score``, ``lowest_score``,
    ``attempts``, ``rounds_played`` and ``std_deviation``.
    """
    df = _require_data(dataframe)
    names = list(player_names)
    if len(names) < 2:
        raise ValueError("Please choose at least two players to compare.")

    comparison = {}
    for name in names:
        rows = df[df["player_name"] == name]
        if rows.empty:
            raise ValueError("Player '%s' was not found in the stored results." % name)
        comparison[name] = {
            "average_score": calculate_average_score(rows["score"].tolist()),
            "average_accuracy": calculate_average_accuracy(rows["accuracy"].tolist()),
            "best_score": float(np.max(np.asarray(rows["score"].tolist(), dtype="float64"))),
            "lowest_score": float(np.min(np.asarray(rows["score"].tolist(), dtype="float64"))),
            "attempts": int(len(rows)),
            "rounds_played": sorted(set(rows["round_name"].tolist())),
            "std_deviation": calculate_std_deviation(rows["score"].tolist()),
        }
    return comparison


def compare_rounds(dataframe, round_names):
    """Compare two or more quiz rounds.

    Returns a dictionary keyed by round name. Every value is a dictionary with
    ``average_score``, ``average_accuracy``, ``attempts``, ``highest_score``,
    ``lowest_score`` and ``difficulty``.
    """
    df = _require_data(dataframe)
    names = list(round_names)
    if len(names) < 2:
        raise ValueError("Please choose at least two rounds to compare.")

    comparison = {}
    for name in names:
        statistics = get_round_statistics(df, name)
        comparison[name] = {
            "average_score": statistics["average_score"],
            "average_accuracy": statistics["average_accuracy"],
            "attempts": statistics["attempts"],
            "highest_score": statistics["highest_score"],
            "lowest_score": statistics["lowest_score"],
            "difficulty": statistics["difficulty"],
        }
    return comparison


# --------------------------------------------------------------------------- #
# 6. Searching / filtering and overall summary
# --------------------------------------------------------------------------- #

def filter_results(dataframe, player_name="", round_name="", attempt=None):
    """Search the stored results.

    ``player_name`` and ``round_name`` are matched as case insensitive parts of
    the name; ``attempt`` must be a whole number when given. Empty values are
    ignored. The filtered DataFrame is returned.
    """
    df = _require_data(dataframe)
    result = df.copy()

    if str(player_name or "").strip():
        result = result[result["player_name"].str.contains(
            str(player_name).strip(), case=False, na=False, regex=False)]

    if str(round_name or "").strip():
        result = result[result["round_name"].str.contains(
            str(round_name).strip(), case=False, na=False, regex=False)]

    if attempt is not None and str(attempt).strip() != "":
        text = str(attempt).strip()
        try:
            attempt_number = int(text)
        except ValueError:
            raise ValueError("Attempt number must be a whole number (digits only).") from None
        if attempt_number <= 0:
            raise ValueError("Attempt number must be greater than zero.")
        result = result[result["attempt"] == attempt_number]

    return result.reset_index(drop=True)


def get_overall_summary(dataframe):
    """Return a dictionary summarising the whole dataset.

    Keys: ``records``, ``players``, ``rounds``, ``attempts``,
    ``average_score``, ``average_accuracy``, ``best_player`` (tuple) and
    ``easiest_round`` (tuple).
    """
    df = _require_data(dataframe)
    players = sorted(set(df["player_name"].tolist()))
    rounds = sorted(set(df["round_name"].tolist()))

    return {
        "records": int(len(df)),
        "players": players,
        "rounds": rounds,
        "attempts": int(df["attempt"].nunique()),
        "average_score": calculate_average_score(df["score"].tolist()),
        "average_accuracy": calculate_average_accuracy(df["accuracy"].tolist()),
        "best_player": find_best_player(df),
        "easiest_round": find_best_round(df),
    }
