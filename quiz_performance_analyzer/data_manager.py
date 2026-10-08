"""
data_manager.py
================
Local file storage for the Quiz Performance Analyzer.

All quiz results are stored in a plain local CSV file (``data/quiz_results.csv``).
No database and no network access is used anywhere in this module.

The module is responsible for:

* creating the data directory and the CSV file when they do not exist,
* reading the stored quiz results,
* adding, updating and deleting records,
* validating raw user input and stored data,
* loading the records into a Pandas DataFrame for analysis,
* handling file related exceptions in a clear way.

Stored columns (defined once in :data:`FIELDS`):

    player_name, round_name, attempt, total_questions,
    correct_answers, score, accuracy, date

``score`` and ``accuracy`` are always derived from ``correct_answers`` and
``total_questions``; they are never typed in by the user.
"""

import csv
import os
from datetime import datetime

import pandas as pd

import analyzer

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

#: Folder that holds the local data file.
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

#: Default location of the quiz results file.
DATA_FILE = os.path.join(DATA_DIR, "quiz_results.csv")

#: Column order used both in the CSV file and in the DataFrame.
FIELDS = [
    "player_name",
    "round_name",
    "attempt",
    "total_questions",
    "correct_answers",
    "score",
    "accuracy",
    "date",
]

#: Date format expected from the user (also used for sorting).
DATE_FORMAT = "%Y-%m-%d"

#: Columns that must contain numbers.
NUMERIC_FIELDS = ["attempt", "total_questions", "correct_answers", "score", "accuracy"]

#: Columns that must contain text.
TEXT_FIELDS = ["player_name", "round_name", "date"]


class DataError(Exception):
    """Raised when the quiz data file cannot be read, written or validated."""


# --------------------------------------------------------------------------- #
# File handling helpers
# --------------------------------------------------------------------------- #

def ensure_data_file(file_path=None):
    """Create the data directory and the CSV file (with header) if missing.

    Returns the path of the data file. Raises :class:`DataError` when the
    directory or the file cannot be created (for example, no permission).
    """
    path = file_path or DATA_FILE
    try:
        directory = os.path.dirname(os.path.abspath(path))
        if directory and not os.path.isdir(directory):
            os.makedirs(directory, exist_ok=True)

        # Write the header only when the file does not exist or is empty.
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            with open(path, "w", newline="", encoding="utf-8") as file_handle:
                writer = csv.writer(file_handle)
                writer.writerow(FIELDS)
    except OSError as error:
        raise DataError("Could not create the data file.\n"
                        "Location: %s\nReason: %s" % (path, error)) from error
    return path


def data_file_exists(file_path=None):
    """Return True when the data file already exists on disk."""
    return os.path.isfile(file_path or DATA_FILE)


# --------------------------------------------------------------------------- #
# Reading
# --------------------------------------------------------------------------- #

def load_records(file_path=None):
    """Read every record from the CSV file using the standard ``csv`` module.

    Returns a list of dictionaries (one dictionary per row). A missing file is
    created first, so the result is an empty list instead of an error. Blank
    lines are ignored and numeric values are converted when possible.
    """
    path = ensure_data_file(file_path)
    records = []
    try:
        with open(path, "r", newline="", encoding="utf-8") as file_handle:
            reader = csv.DictReader(file_handle)
            header = [name.strip() for name in (reader.fieldnames or []) if name and name.strip()]
            if not header:
                return []           # the file exists but is still empty

            # Validate the CSV contents: every required column must be present.
            missing_columns = [field for field in FIELDS if field not in header]
            if missing_columns:
                raise DataError("The data file has an unexpected format.\n"
                                "File: %s\nMissing column(s): %s"
                                % (path, ", ".join(missing_columns)))

            for row in reader:
                if not row or not any((value or "").strip() for value in row.values()):
                    continue  # skip fully blank lines
                record = {field: (row.get(field) or "").strip() for field in FIELDS}
                for field in NUMERIC_FIELDS:
                    try:
                        record[field] = float(record[field])
                    except (TypeError, ValueError):
                        record[field] = None  # corrupted value, fixed on load
                records.append(record)
    except FileNotFoundError:
        return []  # nothing stored yet
    except DataError:
        raise      # already a clear message from the column check
    except PermissionError as error:
        raise DataError("Permission denied while reading the data file:\n%s" % path) from error
    except (csv.Error, UnicodeDecodeError) as error:
        raise DataError("The data file is corrupted and cannot be read:\n%s\n%s"
                        % (path, error)) from error
    except OSError as error:
        raise DataError("Unexpected file error while reading:\n%s\n%s" % (path, error)) from error
    return records


def validate_dataframe(dataframe):
    """Clean a raw DataFrame and keep only usable rows.

    Corrupted rows (text where a number is expected, unknown question counts,
    impossible results) are removed. ``score`` and ``accuracy`` are recalculated
    from ``correct_answers`` / ``total_questions`` so the stored values always
    stay consistent with the score formula.
    """
    if dataframe is None:
        return pd.DataFrame(columns=FIELDS)

    missing = [field for field in FIELDS if field not in dataframe.columns]
    if missing:
        raise DataError("The data file is missing the column(s): %s" % ", ".join(missing))

    clean = dataframe[FIELDS].copy()

    for field in TEXT_FIELDS:
        clean[field] = clean[field].astype("string").fillna("")
        clean[field] = clean[field].str.strip()

    for field in ["attempt", "total_questions", "correct_answers"]:
        clean[field] = pd.to_numeric(clean[field], errors="coerce")

    # Drop rows that cannot be used for analysis.
    clean = clean.dropna(subset=["attempt", "total_questions", "correct_answers"])
    clean = clean[clean["total_questions"] > 0]
    clean = clean[clean["attempt"] > 0]
    clean = clean[clean["correct_answers"] >= 0]
    clean = clean[clean["correct_answers"] <= clean["total_questions"]]
    clean = clean[(clean["player_name"] != "") & (clean["round_name"] != "")]

    clean["attempt"] = clean["attempt"].astype(int)
    clean["total_questions"] = clean["total_questions"].astype(int)
    clean["correct_answers"] = clean["correct_answers"].astype(int)

    # Recalculate score and accuracy with the single scoring formula.
    clean["score"] = analyzer.calculate_score_array(clean["correct_answers"],
                                                    clean["total_questions"])
    clean["accuracy"] = clean["score"]

    clean["date"] = clean["date"].replace("", datetime.today().strftime(DATE_FORMAT))
    clean = clean.reset_index(drop=True)
    return clean


def load_dataframe(file_path=None):
    """Load all quiz results into a validated Pandas DataFrame.

    The data file is created automatically when it does not exist. Structural
    problems raise :class:`DataError`; individual corrupted rows are dropped.
    """
    records = load_records(file_path)
    if not records:
        return pd.DataFrame(columns=FIELDS)
    return validate_dataframe(pd.DataFrame(records, columns=FIELDS))


def check_data_file(file_path=None):
    """Verify the stored file and report how many rows are valid.

    Returns a dictionary with the total number of rows, the valid rows, the
    skipped (corrupted) rows and a list of readable messages. This is used by
    the GUI to warn the user about damaged records.
    """
    path = ensure_data_file(file_path)
    report = {"path": path, "total_rows": 0, "valid_rows": 0, "skipped_rows": 0, "messages": []}

    records = load_records(path)
    report["total_rows"] = len(records)

    dataframe = validate_dataframe(pd.DataFrame(records, columns=FIELDS)) if records \
        else pd.DataFrame(columns=FIELDS)
    report["valid_rows"] = len(dataframe)
    report["skipped_rows"] = report["total_rows"] - report["valid_rows"]

    if report["skipped_rows"] > 0:
        report["messages"].append(
            "%d corrupted row(s) were skipped while loading." % report["skipped_rows"])
    if report["total_rows"] == 0:
        report["messages"].append("No quiz results stored yet.")
    return report


def get_unique_players(dataframe=None):
    """Return a sorted list of the distinct player names (built from a set)."""
    if dataframe is None:
        dataframe = load_dataframe()
    if dataframe.empty:
        return []
    return sorted(set(dataframe["player_name"].tolist()))


def get_unique_rounds(dataframe=None):
    """Return a sorted list of the distinct round names (built from a set)."""
    if dataframe is None:
        dataframe = load_dataframe()
    if dataframe.empty:
        return []
    return sorted(set(dataframe["round_name"].tolist()))


# --------------------------------------------------------------------------- #
# Validation of user input
# --------------------------------------------------------------------------- #

def validate_result(player_name, round_name, attempt, total_questions,
                    correct_answers, date_text):
    """Validate one quiz result typed by the user.

    Returns a tuple ``(player_name, round_name, attempt, total_questions,
    correct_answers, date_text)`` with clean values. Raises :class:`ValueError`
    with a readable message when something is wrong.
    """
    player = str(player_name or "").strip()
    round_label = str(round_name or "").strip()
    date_value = str(date_text or "").strip()

    if not player:
        raise ValueError("Player name cannot be empty.")
    if not round_label:
        raise ValueError("Round name cannot be empty.")

    def to_positive_int(value, label):
        """Convert a text value to an integer greater than zero."""
        text = str(value if value is not None else "").strip()
        if text == "":
            raise ValueError("%s is required and must be a whole number." % label)
        try:
            number = int(text)
        except ValueError:
            raise ValueError("%s must be a whole number (digits only)." % label) from None
        if number <= 0:
            raise ValueError("%s must be greater than zero." % label)
        return number

    attempt_number = to_positive_int(attempt, "Attempt number")
    total = to_positive_int(total_questions, "Total questions")

    correct_text = str(correct_answers if correct_answers is not None else "").strip()
    if correct_text == "":
        raise ValueError("Correct answers is required and must be a whole number.")
    try:
        correct = int(correct_text)
    except ValueError:
        raise ValueError("Correct answers must be a whole number (digits only).") from None
    if correct < 0:
        raise ValueError("Correct answers cannot be negative.")
    if correct > total:
        raise ValueError("Correct answers cannot exceed total questions.")

    if not date_value:
        raise ValueError("Date is required (format YYYY-MM-DD, for example 2026-10-07).")
    try:
        datetime.strptime(date_value, DATE_FORMAT)
    except ValueError:
        raise ValueError("Date must be in the format YYYY-MM-DD "
                         "(for example 2026-10-07).") from None

    return player, round_label, attempt_number, total, correct, date_value


def build_record(player_name, round_name, attempt, total_questions,
                 correct_answers, date_text):
    """Validate the input and build a complete record dictionary.

    Score and accuracy are calculated here, so the user never types them.
    """
    player, round_label, attempt_number, total, correct, date_value = validate_result(
        player_name, round_name, attempt, total_questions, correct_answers, date_text)

    score = analyzer.calculate_score(correct, total)
    accuracy = analyzer.calculate_accuracy(correct, total)
    return {
        "player_name": player,
        "round_name": round_label,
        "attempt": attempt_number,
        "total_questions": total,
        "correct_answers": correct,
        "score": score,
        # accuracy uses the same percentage formula in this scoring scheme
        "accuracy": accuracy,
        "date": date_value,
    }


# --------------------------------------------------------------------------- #
# Writing
# --------------------------------------------------------------------------- #

def add_result(player_name, round_name, attempt, total_questions,
               correct_answers, date_text=None, file_path=None):
    """Validate and append one quiz result to the CSV file.

    ``date_text`` defaults to today's date. The previously stored records are
    preserved: only one row is appended. Returns the saved record dictionary.
    """
    path = ensure_data_file(file_path)
    if date_text is None or str(date_text).strip() == "":
        date_text = datetime.today().strftime(DATE_FORMAT)

    record = build_record(player_name, round_name, attempt, total_questions,
                          correct_answers, date_text)

    try:
        # Mode "a" keeps all existing rows; the header is already written.
        with open(path, "a", newline="", encoding="utf-8") as file_handle:
            writer = csv.writer(file_handle)
            writer.writerow([
                record["player_name"],
                record["round_name"],
                record["attempt"],
                record["total_questions"],
                record["correct_answers"],
                "%.2f" % record["score"],
                "%.2f" % record["accuracy"],
                record["date"],
            ])
    except PermissionError as error:
        raise DataError("Permission denied. The result could not be saved to:\n%s"
                        % path) from error
    except OSError as error:
        raise DataError("The result could not be saved to:\n%s\n%s" % (path, error)) from error

    return record


def save_dataframe(dataframe, file_path=None):
    """Write a whole (already validated) DataFrame back to the CSV file."""
    path = ensure_data_file(file_path)
    try:
        clean = validate_dataframe(dataframe)
        clean.to_csv(path, index=False, encoding="utf-8")
    except DataError:
        raise
    except OSError as error:
        raise DataError("Could not write the data file:\n%s\n%s" % (path, error)) from error
    return path


def update_record(row_index, file_path=None, **changes):
    """Update the record at ``row_index`` (0 based, file order).

    Only the given fields are changed; score and accuracy are recalculated
    automatically. Returns the updated record dictionary.
    """
    dataframe = load_dataframe(file_path)
    if dataframe.empty:
        raise DataError("There are no stored results to update.")
    if row_index < 0 or row_index >= len(dataframe):
        raise DataError("Record number %s does not exist." % row_index)

    record = dataframe.iloc[row_index].to_dict()

    allowed = ["player_name", "round_name", "attempt", "total_questions",
               "correct_answers", "date"]
    for key, value in changes.items():
        if key in allowed:
            record[key] = value

    updated = build_record(record["player_name"], record["round_name"],
                           record["attempt"], record["total_questions"],
                           record["correct_answers"], record["date"])
    dataframe.iloc[row_index] = [updated[field] for field in FIELDS]
    save_dataframe(dataframe, file_path)
    return updated


def delete_record(row_index, file_path=None):
    """Delete the record at ``row_index`` (0 based, file order)."""
    dataframe = load_dataframe(file_path)
    if dataframe.empty:
        raise DataError("There are no stored results to delete.")
    if row_index < 0 or row_index >= len(dataframe):
        raise DataError("Record number %s does not exist." % row_index)

    dataframe = dataframe.drop(index=row_index).reset_index(drop=True)
    save_dataframe(dataframe, file_path)
    return True


def count_records(file_path=None):
    """Return the number of valid records stored in the data file."""
    return len(load_dataframe(file_path))
