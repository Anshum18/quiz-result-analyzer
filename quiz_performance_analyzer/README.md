# Quiz Performance Analyzer

An offline desktop application (Python + Tkinter) that stores quiz-game results in a
local CSV file and analyses them with Pandas and NumPy, with reports drawn using
Matplotlib.

**The application is completely local and offline. It never connects to the internet,
never calls an API, and never uses a database or a web server.**

---

## 1. Project title

**Quiz Performance Analyzer** — an offline desktop tool for analysing quiz-game results.

---

## 2. Problem statement

A quiz organizer runs multiple rounds and records the answers and scores of the players.
At the end of the quiz the organizer wants to know:

* which rounds were **difficult** for the players,
* how each **player performed** across attempts,
* how players and rounds **compare** with each other.

All of this information is normally kept in notes or spreadsheets, which makes it slow to
calculate averages for each round, compare two players, or decide which round will be
reused in the next event.

---

## 3. Objective

Develop a desktop application that:

* manages quiz-game results,
* stores player and quiz-round results persistently in local files,
* calculates scores and accuracy measures,
* allows searching and filtering of the stored results,
* compares players and compares quiz rounds,
* identifies difficult quiz rounds,
* generates at least two meaningful visual reports,
* runs completely offline on the local computer.

---

## 4. Features

| Feature | Description |
|---------|-------------|
| **Add Result** | Form to save one quiz result. Score and accuracy are calculated automatically and validated. |
| **View Results** | Table (`ttk.Treeview`) with every stored result. |
| **Search / Filter** | Filter by player name, round name and/or attempt number (case-insensitive part matching). |
| **Player Analysis** | Attempts, average score, average accuracy, best/lowest score, standard deviation, best attempt, per-round accuracy and complete attempt history. |
| **Round Analysis** | Number of attempts, players, average score, average accuracy, highest/lowest score, standard deviation and the difficulty level. |
| **Compare Players** | Side-by-side table of two players. |
| **Compare Rounds** | Side-by-side table of two rounds, including which round was harder. |
| **Round Difficulty** | All rounds ranked from the most difficult to the easiest, with the documented thresholds. |
| **Visual Reports** | Three Matplotlib charts (see section 12). |
| **Exit** | Closes the application (with a confirmation dialog). |

---

## 5. Technologies used

Only the approved technologies are used:

| Technology | Used for |
|------------|----------|
| **Python 3** | the whole application |
| **Tkinter** (`tkinter`, `ttk`, `messagebox`) | the desktop user interface |
| **Pandas** | reading the CSV file, filtering, grouping, averages |
| **NumPy** | numeric arrays, mean/max/min, standard deviation, vectorised score calculation |
| **Matplotlib** | the visual reports |
| **Standard library** | `csv`, `os`, `sys`, `math`-free calculations, `datetime` (date validation), `unittest` (tests), `tempfile`/`shutil` (used only by the tests) |

No web page technology, no web framework, no extra GUI toolkit, no database engine and no
online service is used — only the six entries in the table above.

---

## 6. Project structure

```text
quiz_performance_analyzer/
│
├── main.py               # starts the application (python main.py)
├── gui.py                # Tkinter user interface (all windows)
├── data_manager.py       # local CSV storage, validation, file handling
├── analyzer.py           # all calculations and statistics (Pandas + NumPy)
├── visualizer.py         # Matplotlib reports
│
├── data/
│   └── quiz_results.csv  # the local data file (created automatically)
│
├── tests/
│   └── test_analyzer.py  # unittest tests
│
└── README.md
```

Module responsibilities:

* **`main.py`** – creates the data file when missing and starts the GUI.
* **`data_manager.py`** – creates the data folder/file, reads and writes records, validates
  the stored data, validates the user input and loads everything into a Pandas DataFrame.
* **`analyzer.py`** – score/accuracy calculation, averages, standard deviation, difficulty
  levels, player statistics, round statistics, comparisons, searching and the overall
  summary. It contains no GUI code and no file-handling code.
* **`visualizer.py`** – builds the Matplotlib figures.
* **`gui.py`** – main window plus one small window per feature.

---

## 7. How to run

Requirements: Python 3.8 or newer with `numpy`, `pandas` and `matplotlib`
(Tkinter is included with the standard Python installer on Windows and macOS;
on Linux it may come from the `python3-tk` package).

```bash
# 1. open the project folder
cd quiz_performance_analyzer

# 2. (only if a package is missing)
pip install numpy pandas matplotlib

# 3. start the application
python main.py
```

A small window with ten buttons opens. Everything else happens inside that window —
no browser, no server, no internet connection.

Run the tests with:

```bash
python -m unittest discover -s tests -v
```

---

## 8. How data is stored

All results are stored in one plain local CSV file:

```text
data/quiz_results.csv
```

| Column | Meaning |
|--------|---------|
| `player_name` | name of the player |
| `round_name` | name of the quiz round |
| `attempt` | attempt number inside that round (1, 2, 3 …) |
| `total_questions` | number of questions asked |
| `correct_answers` | number of correct answers |
| `score` | calculated score in percent |
| `accuracy` | calculated accuracy in percent |
| `date` | date of the attempt (`YYYY-MM-DD`) |

Example:

```text
player_name,round_name,attempt,total_questions,correct_answers,score,accuracy,date
Rahul,Round 1,1,10,8,80.00,80.00,2026-10-01
Priya,Round 1,1,10,9,90.00,90.00,2026-10-01
Rahul,Round 2,1,10,6,60.00,60.00,2026-10-03
```

Details:

* The `data` folder and the CSV file are **created automatically** when they do not exist.
* New results are **appended** to the file, so earlier results are never lost and they are
  still available after closing and reopening the program.
* The file is read with the standard `csv` module and then loaded into a **Pandas
  DataFrame** for analysis.
* While loading, every row is validated: rows with text where a number is expected, an
  unknown question count or an impossible result (`correct_answers > total_questions`) are
  skipped, and the GUI reports how many rows were skipped.
* `score` and `accuracy` are recalculated from `correct_answers` and `total_questions` when
  the file is loaded, so the stored values always match the score formula.
* The file is never touched by anything except this application (no database, no network,
  no cloud storage).

**Sample data:** the repository ships with 22 sample rows in `data/quiz_results.csv`
(4 players × 3 rounds) so that the analysis and the charts are immediately demonstrable.
Delete the rows (or the whole file) at any time — the application recreates the file and
works with an empty dataset as well.

---

## 9. Score calculation

```text
score = correct_answers / total_questions * 100
```

The result is rounded to two decimals, so it always lies between 0 and 100.

Example: 8 correct answers out of 10 questions → `8 / 10 * 100 = 80.00` (score 80).

The function `analyzer.calculate_score()` performs this calculation and raises a clear
`ValueError` for impossible input (division by zero, negative answers, more correct
answers than questions). A vectorised version (`analyzer.calculate_score_array()`) does the
same for whole columns with NumPy.

---

## 10. Accuracy calculation

In this project accuracy uses the same percentage formula as the score:

```text
accuracy = correct_answers / total_questions * 100   (%)
```

`analyzer.calculate_accuracy()` calls the score function, so both values are always equal
(the CSV file therefore stores the same number twice — once as `score` and once as
`accuracy`). Keeping the two columns separate makes it easy to switch to a different
scoring scheme later (for example marks per question), without changing the rest of the
program.

---

## 11. Difficulty calculation

A round is judged by the **average accuracy of all its attempts**:

```text
average accuracy < 50 %        -> Difficult
50 % <= average accuracy <= 70 % -> Moderate
average accuracy > 70 %        -> Easy
```

The thresholds are defined once in `analyzer.py`
(`DIFFICULT_MAX = 50.0`, `MODERATE_MAX = 70.0`) and are shown inside the application, so
they can be changed in a single place:

```python
DIFFICULT_MAX = 50.0     # below this value a round is Difficult
MODERATE_MAX = 70.0      # up to this value a round is Moderate, above it Easy
```

`analyzer.find_difficult_rounds()` returns every round with its average accuracy, average
score, number of attempts and difficulty label, sorted from the hardest to the easiest.

---

## 12. Visualization details

Matplotlib is the only plotting library used. Each report opens in its own chart window and
is based on the real stored data (when there is no data, a message is shown instead of an
empty chart).

**Report 1 — Player Performance Across Attempts** (`visualizer.plot_player_performance`)

* a line chart: X axis = round + attempt in date order, Y axis = score/accuracy in percent,
* one point per attempt with its value written next to it,
* the player's average is drawn as a dashed line, the 50 % difficulty threshold as a dotted
  line, both explained in the legend.

**Report 2 — Quiz Round Difficulty** (`visualizer.plot_round_difficulty`)

* a bar chart: X axis = quiz round (hardest first), Y axis = average accuracy in percent,
* bars are coloured by difficulty level (red = Difficult, amber = Moderate, green = Easy)
  and the legend explains the colours and the two threshold lines (50 % and 70 %),
* the average accuracy is written above every bar — a low bar means a difficult round.

**Report 3 (optional) — Player Average Score Comparison** (`visualizer.plot_player_comparison`)

* a bar chart with the average score of every player and the overall average as a dashed
  line.

Every chart has a meaningful title, labelled axes, readable tick labels and a legend.
Tick labels of the first report are rotated so that long round names stay readable.

---

## 13. Testing

The tests live in `tests/test_analyzer.py` and use **only Python's built-in `unittest`**
(no pytest and no other testing framework):

```bash
python -m unittest discover -s tests -v
# or
python tests/test_analyzer.py
```

53 test cases cover:

| Test group | What is verified |
|------------|------------------|
| `TestScoreCalculation` | score/accuracy formula, rounding, division by zero, negative and impossible answers, the vectorised version, automatic calculation while loading |
| `TestStatistics` | average score/accuracy, empty lists, standard deviation, difficulty limits (49.99 / 50 / 70 / 70.01) |
| `TestPlayerStatistics` | attempts, averages, best/lowest score, best attempt tuple, per-round accuracy, unknown player, ordered progress, best player |
| `TestRoundAnalysis` | round statistics, unknown round, difficult-round detection and ordering, difficulty map, best round |
| `TestComparison` | player comparison, round comparison, "at least two" checks |
| `TestSearchAndSummary` | filtering by player/round/attempt, no-match results, invalid attempt numbers, overall summary, empty dataset |
| `TestInputValidation` | every validation rule (empty names, non-integer attempt, total questions = 0, negative or too large correct answers, wrong date format) |
| `TestDataManagerStorage` | automatic file creation, loading a missing file, saving and re-loading (persistence), appended records are preserved, invalid input is not written, default date, update/delete, corrupted rows are skipped, missing columns raise `DataError` |
| `TestVisualizer` | all three charts are produced, titles/axis labels/x-axis order are correct, images are written to disk, empty data raises a clear error |

The tests use a temporary folder for the file tests and the `Agg` backend for the charts, so
they never modify `data/quiz_results.csv` and never open a window.

---

## 14. Offline operation

* The application starts with `python main.py` and runs on the local computer only.
* It does **not** need an internet connection and works with the network cable unplugged.
* It does not connect to any server, does not call any API, does not upload or download
  anything, does not use a browser and does not use an online database.
* All persistent data is kept in the local file `data/quiz_results.csv`.
* A search through the whole project finds no web address, no networking library, no API
  client, no cloud service call and no database code — the only imports are `csv`, `os`,
  `sys`, `datetime`, `unittest`, `tempfile`, `shutil`, `tkinter`, `numpy`, `pandas` and
  `matplotlib`.

---

## 15. Limitations and future improvements

Current limitations (kept simple on purpose, as required for an academic project):

* The result file is a CSV file, so it is fine for hundreds or a few thousand rows but was
  not designed for very large datasets.
* Only one scoring scheme is implemented (percentage of correct answers).
* The application stores results of rounds that already happened; it does not run the quiz
  itself, and there is no timer or question bank.
* Deleting/updating a record is available in `data_manager.py` (and covered by tests) but is
  not exposed as a button in the GUI, to keep the interface minimal.
* Reports are shown as separate chart windows; they cannot be exported from inside the
  application (Matplotlib's own toolbar can still be used to save an image).
* Lines are not drawn for a player who has only one attempt — the single point is shown.

Possible future improvements:

* Export a report to a text/CSV file or to a picture with one button.
* Per-question difficulty (which needs per-question data in the CSV file).
* A configurable scoring scheme (marks per question, negative marking).
* A simple "edit / delete row" dialog in the GUI.

---

## Quick reference — what each button does

| Button | Result |
|--------|--------|
| **Add Result** | Opens the entry form. Nothing is stored until *Save Result* is pressed; the score and accuracy are calculated for you. |
| **View Results** | Shows every stored result in a table with a *Refresh* button. |
| **Search / Filter** | Filters the stored results by player, round and/or attempt. |
| **Player Analysis** | Text report of one player + button for the performance chart. |
| **Round Analysis** | Text report of one round + button for the difficulty chart. |
| **Compare Players** | Table comparing two players. |
| **Compare Rounds** | Table comparing two rounds. |
| **Round Difficulty** | Ranking of all rounds from the hardest to the easiest. |
| **Visual Reports** | Opens the three Matplotlib reports. |
| **Exit** | Closes the application after a confirmation. |
