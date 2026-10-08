"""
visualizer.py
=============
Matplotlib reports for the Quiz Performance Analyzer.

Three meaningful reports are produced (all of them from the real stored data):

1. :func:`plot_player_performance` - line chart: how a player scored across
   rounds and attempts.
2. :func:`plot_round_difficulty` - bar chart: average accuracy of every round.
   A low bar means a difficult round.
3. :func:`plot_player_comparison` - bar chart: average score of every player.

Every chart has a title, labelled axes, a legend where it helps and readable
tick labels. Matplotlib is the only plotting library used.

Each function returns the Matplotlib ``Figure``. When ``show`` is True (the
default, used by the GUI) the chart is displayed in a normal Matplotlib window.
"""

from matplotlib import pyplot as plt
from matplotlib.patches import Patch

import analyzer

# Colours used for the three difficulty levels (kept to a minimum on purpose).
DIFFICULTY_COLOURS = {
    analyzer.LABEL_DIFFICULT: "#c0504d",   # red
    analyzer.LABEL_MODERATE: "#e0a030",    # amber
    analyzer.LABEL_EASY: "#4f9d69",        # green
}


def _prepare_figure(title):
    """Create a figure with a readable default size and title."""
    figure, axes = plt.subplots(figsize=(9, 5.5))
    # Give the chart window the same name as the chart title.
    if figure.canvas.manager is not None:
        figure.canvas.manager.set_window_title(title)
    axes.set_title(title, fontsize=13, fontweight="bold")
    axes.grid(True, linestyle="--", alpha=0.5)
    return figure, axes


def _finish(figure, show):
    """Show the figure or just return it (used by the tests)."""
    figure.tight_layout()
    if show:
        plt.show()
    return figure


# --------------------------------------------------------------------------- #
# Report 1 - player performance
# --------------------------------------------------------------------------- #

def plot_player_performance(dataframe, player_name, show=True):
    """Line chart of one player's score across rounds/attempts.

    X axis: each round + attempt, in date order.
    Y axis: score/accuracy in percent.
    """
    if dataframe is None or dataframe.empty:
        raise ValueError(analyzer.NO_DATA_MESSAGE)

    progress = analyzer.get_player_progress(dataframe, player_name)
    labels = [item[0] for item in progress]
    scores = [item[1] for item in progress]

    total_attempts = len(scores)
    player_average = analyzer.calculate_average_score(scores)

    figure, axes = _prepare_figure("Player Performance Across Attempts - %s" % player_name)
    axes.plot(range(total_attempts), scores, marker="o", linewidth=2,
              color="#3060a0", label="Score of %s" % player_name)
    axes.axhline(player_average, color="#a03030", linestyle="--", linewidth=1.2,
                 label="Player average (%.2f%%)" % player_average)
    axes.axhline(analyzer.DIFFICULT_MAX, color="#808080", linestyle=":", linewidth=1,
                 label="Difficult below %.0f%%" % analyzer.DIFFICULT_MAX)

    axes.set_xlabel("Round and attempt")
    axes.set_ylabel("Score / Accuracy (%)")
    axes.set_ylim(0, 105)
    axes.set_xticks(range(total_attempts))
    axes.set_xticklabels(labels, rotation=20, ha="right", fontsize=9)
    axes.legend(loc="lower right", fontsize=9)

    # Write the value next to every point.
    for position, value in enumerate(scores):
        axes.annotate("%.1f" % value, (position, value), textcoords="offset points",
                      xytext=(0, 8), ha="center", fontsize=8)

    return _finish(figure, show)


# --------------------------------------------------------------------------- #
# Report 2 - round difficulty
# --------------------------------------------------------------------------- #

def plot_round_difficulty(dataframe, show=True):
    """Bar chart of the average accuracy of every round.

    Bars are coloured by difficulty level, and two reference lines show the
    documented thresholds (50 % and 70 %).
    """
    if dataframe is None or dataframe.empty:
        raise ValueError(analyzer.NO_DATA_MESSAGE)

    round_stats = analyzer.find_difficult_rounds(dataframe)      # hardest first
    rounds = [item["round_name"] for item in round_stats]
    accuracies = [item["average_accuracy"] for item in round_stats]
    colours = [DIFFICULTY_COLOURS[item["difficulty"]] for item in round_stats]

    figure, axes = _prepare_figure("Quiz Round Difficulty (Average Accuracy)")
    bars = axes.bar(rounds, accuracies, color=colours, width=0.6,
                    edgecolor="black", linewidth=0.7)

    axes.axhline(analyzer.DIFFICULT_MAX, color="#a03030", linestyle="--", linewidth=1.2,
                 label="Difficult threshold (%.0f%%)" % analyzer.DIFFICULT_MAX)
    axes.axhline(analyzer.MODERATE_MAX, color="#4f7d4f", linestyle="--", linewidth=1.2,
                 label="Moderate/Easy threshold (%.0f%%)" % analyzer.MODERATE_MAX)

    axes.set_xlabel("Quiz round")
    axes.set_ylabel("Average accuracy (%)")
    axes.set_ylim(0, 110)

    # Legend entries for the colours of the difficulty levels.
    handles = [Patch(facecolor=DIFFICULTY_COLOURS[analyzer.LABEL_DIFFICULT], edgecolor="black",
                     label="Difficult (< %.0f%%)" % analyzer.DIFFICULT_MAX),
               Patch(facecolor=DIFFICULTY_COLOURS[analyzer.LABEL_MODERATE], edgecolor="black",
                     label="Moderate (%.0f%% - %.0f%%)" % (analyzer.DIFFICULT_MAX,
                                                           analyzer.MODERATE_MAX)),
               Patch(facecolor=DIFFICULTY_COLOURS[analyzer.LABEL_EASY], edgecolor="black",
                     label="Easy (> %.0f%%)" % analyzer.MODERATE_MAX)]
    axes.legend(handles=handles, loc="upper left", fontsize=9)

    for bar, value in zip(bars, accuracies):
        axes.annotate("%.1f%%" % value, (bar.get_x() + bar.get_width() / 2, value),
                      textcoords="offset points", xytext=(0, 5), ha="center", fontsize=9)

    return _finish(figure, show)


# --------------------------------------------------------------------------- #
# Report 3 (optional) - player comparison
# --------------------------------------------------------------------------- #

def plot_player_comparison(dataframe, show=True):
    """Bar chart of the average score of every player."""
    if dataframe is None or dataframe.empty:
        raise ValueError(analyzer.NO_DATA_MESSAGE)

    averages = analyzer.get_players_average_scores(dataframe)
    players = sorted(averages.keys())
    values = [averages[name] for name in players]

    figure, axes = _prepare_figure("Player Average Score Comparison")
    bars = axes.bar(players, values, color="#4f6d9d", width=0.55,
                    edgecolor="black", linewidth=0.7)

    overall_average = analyzer.calculate_average_score(
        list(dataframe["score"]))
    axes.axhline(overall_average, color="#a03030", linestyle="--", linewidth=1.2,
                 label="Overall average (%.2f%%)" % overall_average)

    axes.set_xlabel("Player")
    axes.set_ylabel("Average score (%)")
    axes.set_ylim(0, 110)
    axes.legend(loc="upper right", fontsize=9)

    for bar, value in zip(bars, values):
        axes.annotate("%.1f" % value, (bar.get_x() + bar.get_width() / 2, value),
                      textcoords="offset points", xytext=(0, 5), ha="center", fontsize=9)

    return _finish(figure, show)
