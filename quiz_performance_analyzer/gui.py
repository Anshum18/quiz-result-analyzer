"""
gui.py
======
Tkinter user interface of the Quiz Performance Analyzer.

The main window contains only a short list of buttons. Every feature opens its
own small and simple window:

    Add Result | View Results | Search / Filter | Player Analysis
    Round Analysis | Compare Players | Compare Rounds | Round Difficulty
    Visual Reports | Exit

Only standard Tkinter widgets are used (``tkinter``, ``ttk``, ``messagebox``).
The design is deliberately plain and academic: one font family, no animation,
no custom colours, no extra screens.
"""

import tkinter as tk
import tkinter.font as tkfont
from datetime import date
from tkinter import messagebox, ttk

import analyzer
import data_manager
import visualizer

APP_TITLE = "Quiz Performance Analyzer"

#: Columns shown in the result tables: (heading, width in pixels).
RESULT_COLUMNS = [
    ("Player", 110),
    ("Round", 100),
    ("Attempt", 70),
    ("Correct", 70),
    ("Total", 60),
    ("Score", 70),
    ("Accuracy", 80),
    ("Date", 90),
]


class QuizAnalyzerGUI:
    """Main window of the application."""

    def __init__(self, master=None):
        self.root = master if master is not None else tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry("500x600")
        self.root.minsize(460, 560)

        # Fonts are derived from the standard Tk fonts, so they always exist.
        self.title_font = tkfont.nametofont("TkDefaultFont").copy()
        self.title_font.configure(size=14, weight="bold")
        self.subtitle_font = tkfont.nametofont("TkDefaultFont").copy()
        self.subtitle_font.configure(size=9)
        self.mono_font = "TkFixedFont"

        #: Validated data of the whole application (Pandas DataFrame).
        self.df = data_manager.validate_dataframe(None)

        #: Text shown at the bottom of the main window.
        self.status_text = tk.StringVar(value="Loading data ...")

        self._build_main_window()
        self.reload_data()

    # ------------------------------------------------------------------ #
    # Main window
    # ------------------------------------------------------------------ #

    def _build_main_window(self):
        """Create the static part of the main window."""
        header = ttk.Frame(self.root, padding=(16, 14, 16, 6))
        header.pack(fill="x")

        ttk.Label(header, text="QUIZ PERFORMANCE ANALYZER",
                  font=self.title_font).pack()
        # wraplength keeps the long subtitle inside the window instead of
        # stretching the layout and clipping the header.
        ttk.Label(header, text="Offline desktop application - data stored in data/quiz_results.csv",
                  font=self.subtitle_font, wraplength=430, justify="center",
                  anchor="center").pack(pady=(4, 0), fill="x")

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=16, pady=8)

        menu = ttk.Frame(self.root, padding=(16, 0, 16, 8))
        menu.pack(fill="both", expand=True)

        buttons = [
            ("Add Result", self.open_add_result_window),
            ("View Results", self.open_view_results_window),
            ("Search / Filter", self.open_search_window),
            ("Player Analysis", self.open_player_analysis_window),
            ("Round Analysis", self.open_round_analysis_window),
            ("Compare Players", self.open_compare_players_window),
            ("Compare Rounds", self.open_compare_rounds_window),
            ("Round Difficulty", self.open_difficulty_window),
            ("Visual Reports", self.open_visual_reports_window),
            ("Exit", self.on_exit),
        ]
        for label, command in buttons:
            # pack() centres the buttons horizontally inside the menu frame.
            ttk.Button(menu, text=label, command=command, width=30).pack(pady=4)

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=16)
        ttk.Label(self.root, textvariable=self.status_text,
                  font=self.subtitle_font, anchor="w").pack(fill="x", padx=16, pady=6)

    def run(self):
        """Start the Tkinter event loop."""
        self.root.mainloop()

    def on_exit(self):
        """Ask for confirmation and close the application."""
        if messagebox.askyesno(APP_TITLE, "Close the Quiz Performance Analyzer?"):
            self.root.destroy()

    # ------------------------------------------------------------------ #
    # Data helpers
    # ------------------------------------------------------------------ #

    def reload_data(self):
        """Reload the stored results from the CSV file and refresh the status."""
        try:
            self.df = data_manager.load_dataframe()
            report = data_manager.check_data_file()
        except (data_manager.DataError, OSError) as error:
            self.df = data_manager.validate_dataframe(None)
            self.status_text.set("Data file problem - see the error message.")
            messagebox.showerror("Data File Error", str(error))
            return

        if self.df.empty:
            self.status_text.set("No results stored yet. Use 'Add Result' to start.")
            return

        try:
            summary = analyzer.get_overall_summary(self.df)
        except ValueError:
            summary = None

        # sets are used to count the distinct players and rounds
        players = set(self.df["player_name"].tolist())
        rounds = set(self.df["round_name"].tolist())
        status = "Stored results: %d | Players: %d | Rounds: %d" % (
            len(self.df), len(players), len(rounds))
        if summary is not None:
            status += " | Average score: %s" % self._format_number(summary["average_score"])
        if report["skipped_rows"] > 0:
            status += " | Skipped corrupted rows: %d" % report["skipped_rows"]
        self.status_text.set(status)

    def _has_data(self):
        """Return True when results are available, otherwise inform the user."""
        if self.df is None or self.df.empty:
            messagebox.showinfo("No Data", analyzer.NO_DATA_MESSAGE)
            return False
        return True

    @staticmethod
    def _format_number(value):
        """Format 80.0 as '80' and 76.4 as '76.4' for a clean display."""
        number = float(value)
        if number == int(number):
            return str(int(number))
        return ("%.2f" % number).rstrip("0").rstrip(".")

    # ------------------------------------------------------------------ #
    # Small widget builders
    # ------------------------------------------------------------------ #

    def _open_child_window(self, title, width, height):
        """Create a simple child window of the main window."""
        window = tk.Toplevel(self.root)
        window.title(title)
        window.geometry("%dx%d" % (width, height))
        window.minsize(width, 220)
        window.transient(self.root)
        return window

    def _add_close_button(self, parent, window, row=None, columnspan=1):
        """Add a Close button to a child window.

        ``row`` is used when the parent frame is managed with ``grid``; when it
        is left empty the button is packed instead.
        """
        button = ttk.Button(parent, text="Close", command=window.destroy)
        if row is None:
            button.pack(pady=(4, 10))
        else:
            button.grid(row=row, column=0, columnspan=columnspan,
                        sticky="ew", pady=(4, 10))
        return button

    def _create_treeview(self, parent, columns=None, height=14):
        """Create a scrollable ttk.Treeview table.

        ``columns`` is a list of tuples ``(heading, width)``.
        """
        columns = columns or RESULT_COLUMNS
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=10, pady=(4, 6))

        headings = [heading for heading, _ in columns]
        tree = ttk.Treeview(frame, columns=headings, show="headings", height=height)
        for heading, width in columns:
            tree.heading(heading, text=heading)
            tree.column(heading, width=width, anchor="center", stretch=True)

        vertical = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        return tree

    def _fill_treeview(self, tree, dataframe):
        """Show the rows of a DataFrame inside a Treeview."""
        for item in tree.get_children():
            tree.delete(item)
        for _, row in dataframe.iterrows():
            tree.insert("", "end", values=(
                row["player_name"],
                row["round_name"],
                int(row["attempt"]),
                int(row["correct_answers"]),
                int(row["total_questions"]),
                self._format_number(row["score"]),
                self._format_number(row["accuracy"]) + "%",
                row["date"],
            ))

    def _create_text_area(self, parent, height=16):
        """Create a read-only text area with a scrollbar."""
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=10, pady=(4, 6))

        # width=1 lets the window decide the width; the text wraps automatically.
        text = tk.Text(frame, width=1, height=height, wrap="word",
                       font=self.mono_font, padx=8, pady=6,
                       relief="solid", borderwidth=1)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)

        text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        text.configure(state="disabled")
        return text

    @staticmethod
    def _write_text(text_widget, content):
        """Replace the content of a read-only text area."""
        text_widget.configure(state="normal")
        text_widget.delete("1.0", "end")
        text_widget.insert("1.0", content)
        text_widget.configure(state="disabled")

    @staticmethod
    def _choice_box(parent, label, values, row=0):
        """Create a labelled read-only Combobox with the given values."""
        ttk.Label(parent, text=label + ":").grid(row=row, column=0, sticky="w", pady=4)
        box = ttk.Combobox(parent, values=values, state="readonly", width=24)
        if values:
            box.current(0)
        box.grid(row=row, column=1, sticky="w", padx=(8, 0), pady=4)
        return box

    # ------------------------------------------------------------------ #
    # 1. Add result
    # ------------------------------------------------------------------ #

    def open_add_result_window(self):
        """Form used to enter one quiz result."""
        window = self._open_child_window("Add Quiz Result", 430, 400)
        frame = ttk.Frame(window, padding=16)
        frame.pack(fill="both", expand=True)

        fields = [
            ("Player name", "player_name", ""),
            ("Round name", "round_name", ""),
            ("Attempt number", "attempt", "1"),
            ("Total questions", "total_questions", ""),
            ("Correct answers", "correct_answers", ""),
            ("Date (YYYY-MM-DD)", "date", date.today().strftime(data_manager.DATE_FORMAT)),
        ]

        self.add_entries = {}
        for index, (label, key, default) in enumerate(fields):
            ttk.Label(frame, text=label + ":").grid(row=index, column=0, sticky="w", pady=5)
            entry = ttk.Entry(frame, width=22)
            entry.insert(0, default)
            entry.grid(row=index, column=1, sticky="ew", padx=(10, 0), pady=5)
            self.add_entries[key] = entry

        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Score and accuracy are calculated automatically.",
                  font=self.subtitle_font, wraplength=380).grid(
                      row=len(fields), column=0, columnspan=2, sticky="w", pady=(12, 4))

        ttk.Button(frame, text="Save Result", command=self._save_result).grid(
            row=len(fields) + 1, column=0, columnspan=2, sticky="ew", pady=8)
        self._add_close_button(frame, window, row=len(fields) + 2, columnspan=2)

        self.add_entries["player_name"].focus_set()
        return window

    def _save_result(self):
        """Validate and store the values typed in the Add Result form."""
        values = {key: entry.get() for key, entry in self.add_entries.items()}
        try:
            data_manager.add_result(
                player_name=values["player_name"],
                round_name=values["round_name"],
                attempt=values["attempt"],
                total_questions=values["total_questions"],
                correct_answers=values["correct_answers"],
                date_text=values["date"],
            )
        except ValueError as error:
            # Wrong or impossible input from the user.
            messagebox.showerror("Invalid Input", str(error))
            return
        except (data_manager.DataError, OSError) as error:
            messagebox.showerror("File Error", str(error))
            return
        except Exception as error:  # unexpected problem - never crash silently
            messagebox.showerror("Unexpected Error", "The result could not be saved.\n%s" % error)
            return

        messagebox.showinfo("Saved", "Result saved successfully.")
        # Clear the name fields, keep the date to make several entries easy.
        for key in ("player_name", "round_name", "correct_answers"):
            self.add_entries[key].delete(0, "end")
        self.add_entries["player_name"].focus_set()
        self.reload_data()

    # ------------------------------------------------------------------ #
    # 2. View results
    # ------------------------------------------------------------------ #

    def open_view_results_window(self):
        """Show every stored quiz result in a table."""
        window = self._open_child_window("Stored Quiz Results", 800, 440)

        ttk.Label(window, text="All stored results (score and accuracy are calculated)",
                  font=self.subtitle_font).pack(anchor="w", padx=12, pady=(10, 0))

        tree = self._create_treeview(window)
        ttk.Button(window, text="Refresh", command=lambda: self._refresh_table(tree)).pack(pady=(0, 10))

        self._refresh_table(tree)
        return window

    def _refresh_table(self, tree):
        """Reload the data file and refill a table (used by View/Search)."""
        self.reload_data()
        self._fill_treeview(tree, self.df)

    # ------------------------------------------------------------------ #
    # 3. Search / filter
    # ------------------------------------------------------------------ #

    def open_search_window(self):
        """Filter the results by player, round and attempt number."""
        window = self._open_child_window("Search / Filter Results", 800, 500)

        form = ttk.Frame(window, padding=(12, 10, 12, 4))
        form.pack(fill="x")

        ttk.Label(form, text="Player:").grid(row=0, column=0, sticky="w", pady=3)
        player_entry = ttk.Entry(form, width=18)
        player_entry.grid(row=0, column=1, padx=(6, 14), pady=3)

        ttk.Label(form, text="Round:").grid(row=0, column=2, sticky="w", pady=3)
        round_entry = ttk.Entry(form, width=18)
        round_entry.grid(row=0, column=3, padx=(6, 14), pady=3)

        ttk.Label(form, text="Attempt:").grid(row=0, column=4, sticky="w", pady=3)
        attempt_entry = ttk.Entry(form, width=8)
        attempt_entry.grid(row=0, column=5, padx=(6, 0), pady=3)

        result_label = ttk.Label(window, text="", font=self.subtitle_font)
        result_label.pack(anchor="w", padx=12)

        tree = self._create_treeview(window, height=14)

        def run_search():
            if not self._has_data():
                return
            try:
                filtered = analyzer.filter_results(
                    self.df,
                    player_name=player_entry.get(),
                    round_name=round_entry.get(),
                    attempt=attempt_entry.get())
            except ValueError as error:
                messagebox.showerror("Invalid Input", str(error))
                return
            except Exception as error:
                messagebox.showerror("Unexpected Error", str(error))
                return

            self._fill_treeview(tree, filtered)
            result_label.configure(text="%d result(s) found." % len(filtered))

        def reset_search():
            player_entry.delete(0, "end")
            round_entry.delete(0, "end")
            attempt_entry.delete(0, "end")
            self._refresh_table(tree)
            result_label.configure(text="Showing all %d result(s)." % len(self.df))

        buttons = ttk.Frame(window, padding=(12, 2, 12, 8))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Search", command=run_search, width=14).pack(side="left")
        ttk.Button(buttons, text="Reset", command=reset_search, width=14).pack(side="left", padx=8)

        self._fill_treeview(tree, self.df)
        result_label.configure(text="Showing all %d result(s)." % len(self.df))
        return window

    # ------------------------------------------------------------------ #
    # 4. Player analysis
    # ------------------------------------------------------------------ #

    def open_player_analysis_window(self):
        """Show the statistics of one player."""
        window = self._open_child_window("Player Performance Analysis", 620, 560)

        form = ttk.Frame(window, padding=(12, 10, 12, 0))
        form.pack(fill="x")
        players = data_manager.get_unique_players(self.df)
        player_box = self._choice_box(form, "Player", players)

        text = self._create_text_area(window, height=20)

        def analyse():
            if not self._has_data():
                return
            player = player_box.get()
            if not player:
                messagebox.showerror("Invalid Input", "Please choose a player.")
                return
            try:
                self._write_text(text, self._player_report(player))
            except ValueError as error:
                messagebox.showerror("Analyser Error", str(error))

        def show_chart():
            if not self._has_data():
                return
            player = player_box.get()
            if not player:
                messagebox.showerror("Invalid Input", "Please choose a player.")
                return
            try:
                visualizer.plot_player_performance(self.df, player)
            except ValueError as error:
                messagebox.showinfo("No Chart", str(error))
            except Exception as error:
                messagebox.showerror("Plot Error", "The chart could not be created.\n%s" % error)

        buttons = ttk.Frame(window, padding=(12, 8, 12, 6))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Analyse", command=analyse, width=18).pack(side="left")
        ttk.Button(buttons, text="Show Performance Chart", command=show_chart,
                   width=24).pack(side="left", padx=8)
        ttk.Button(buttons, text="Close", command=window.destroy, width=10).pack(side="right")

        if players:
            analyse()
        else:
            self._write_text(text, analyzer.NO_DATA_MESSAGE)
        return window

    def _player_report(self, player):
        """Build the text report of one player (uses analyzer + dictionaries)."""
        stats = analyzer.get_player_statistics(self.df, player)
        progress = analyzer.get_player_progress(self.df, player)
        number = self._format_number

        # the best attempt is stored as an immutable tuple: (round, attempt, score)
        best_round, best_attempt, best_score = stats["best_attempt"]

        lines = ["Player: %s" % stats["player"], "", "Attempts: %d" % stats["attempts"]]
        lines.append("Average score: %s" % number(stats["average_score"]))
        lines.append("Average accuracy: %s%%" % number(stats["average_accuracy"]))
        lines.append("Best score: %s" % number(stats["best_score"]))
        lines.append("Lowest score: %s" % number(stats["lowest_score"]))
        lines.append("Standard deviation: %s" % number(stats["std_deviation"]))
        lines.append("Best attempt: %s, attempt %d (score %s)"
                     % (best_round, best_attempt, number(best_score)))
        lines.append("Questions answered: %d" % stats["questions_answered"])
        lines.append("Correct answers: %d" % stats["correct_answers"])

        lines.append("")
        lines.append("Performance by round")
        for round_name in sorted(stats["rounds"]):
            info = stats["rounds"][round_name]
            lines.append("  %-12s %6s%% average accuracy over %d attempt(s)" % (
                round_name, number(info["average_accuracy"]), info["attempts"]))

        lines.append("")
        lines.append("Attempt history (oldest first)")
        for label, score_value, accuracy in progress:
            lines.append("  %-24s score %6s   accuracy %6s%%" % (
                label, number(score_value), number(accuracy)))

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # 5. Round analysis
    # ------------------------------------------------------------------ #

    def open_round_analysis_window(self):
        """Show the statistics of one quiz round."""
        window = self._open_child_window("Quiz Round Analysis", 620, 560)

        form = ttk.Frame(window, padding=(12, 10, 12, 0))
        form.pack(fill="x")
        rounds = data_manager.get_unique_rounds(self.df)
        round_box = self._choice_box(form, "Round", rounds)

        text = self._create_text_area(window, height=20)

        def analyse():
            if not self._has_data():
                return
            round_name = round_box.get()
            if not round_name:
                messagebox.showerror("Invalid Input", "Please choose a round.")
                return
            try:
                self._write_text(text, self._round_report(round_name))
            except ValueError as error:
                messagebox.showerror("Analyser Error", str(error))

        def show_chart():
            if not self._has_data():
                return
            try:
                visualizer.plot_round_difficulty(self.df)
            except ValueError as error:
                messagebox.showinfo("No Chart", str(error))
            except Exception as error:
                messagebox.showerror("Plot Error", "The chart could not be created.\n%s" % error)

        buttons = ttk.Frame(window, padding=(12, 8, 12, 6))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Analyse", command=analyse, width=18).pack(side="left")
        ttk.Button(buttons, text="Show Difficulty Chart", command=show_chart,
                   width=24).pack(side="left", padx=8)
        ttk.Button(buttons, text="Close", command=window.destroy, width=10).pack(side="right")

        if rounds:
            analyse()
        else:
            self._write_text(text, analyzer.NO_DATA_MESSAGE)
        return window

    def _round_report(self, round_name):
        """Build the text report of one round."""
        stats = analyzer.get_round_statistics(self.df, round_name)
        number = self._format_number

        lines = ["Round: %s" % stats["round"], "",
                 "Number of attempts: %d" % stats["attempts"],
                 "Players: %s" % ", ".join(stats["players"]),
                 "Average score: %s" % number(stats["average_score"]),
                 "Average accuracy: %s%%" % number(stats["average_accuracy"]),
                 "Highest score: %s" % number(stats["highest_score"]),
                 "Lowest score: %s" % number(stats["lowest_score"]),
                 "Standard deviation: %s" % number(stats["std_deviation"]),
                 "Difficulty: %s" % stats["difficulty"],
                 "",
                 "Thresholds: %s" % analyzer.describe_thresholds(),
                 "",
                 "Average score by player"]
        for player in sorted(stats["player_averages"]):
            lines.append("  %-12s %6s" % (player, number(stats["player_averages"][player])))
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # 6. Compare players
    # ------------------------------------------------------------------ #

    def open_compare_players_window(self):
        """Compare two players side by side."""
        window = self._open_child_window("Compare Players", 620, 480)

        form = ttk.Frame(window, padding=(12, 10, 12, 0))
        form.pack(fill="x")
        players = data_manager.get_unique_players(self.df)
        box_a = self._choice_box(form, "Player A", players, row=0)
        box_b = self._choice_box(form, "Player B", players, row=1)
        if len(players) > 1:
            box_b.current(1)

        text = self._create_text_area(window, height=16)

        def compare():
            if not self._has_data():
                return
            if box_a.get() == box_b.get():
                messagebox.showerror("Invalid Input", "Please choose two different players.")
                return
            try:
                self._write_text(text, self._comparison_table(box_a.get(), box_b.get()))
            except ValueError as error:
                messagebox.showerror("Analyser Error", str(error))

        ttk.Button(window, text="Compare", command=compare, width=18).pack(pady=4)

        if players:
            compare()
        else:
            self._write_text(text, analyzer.NO_DATA_MESSAGE)
        self._add_close_button(window, window)
        return window

    def _comparison_table(self, player_a, player_b):
        """Build a text table that compares two players."""
        comparison = analyzer.compare_players(self.df, [player_a, player_b])
        number = self._format_number
        left, right = comparison[player_a], comparison[player_b]

        rows = [
            ("Average score", number(left["average_score"]), number(right["average_score"])),
            ("Average accuracy", number(left["average_accuracy"]) + "%",
             number(right["average_accuracy"]) + "%"),
            ("Best score", number(left["best_score"]), number(right["best_score"])),
            ("Lowest score", number(left["lowest_score"]), number(right["lowest_score"])),
            ("Attempts", str(left["attempts"]), str(right["attempts"])),
            ("Rounds played", str(len(left["rounds_played"])), str(len(right["rounds_played"]))),
            ("Standard deviation", number(left["std_deviation"]), number(right["std_deviation"])),
        ]

        lines = ["%-22s %-12s %-12s" % ("", player_a, player_b)]
        for title, value_a, value_b in rows:
            lines.append("%-22s %-12s %-12s" % (title, value_a, value_b))

        # Simple conclusion, based on the average score.
        leader = player_a if left["average_score"] >= right["average_score"] else player_b
        lines.append("")
        lines.append("Higher average score: %s" % leader)
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # 7. Compare rounds
    # ------------------------------------------------------------------ #

    def open_compare_rounds_window(self):
        """Compare two quiz rounds side by side."""
        window = self._open_child_window("Compare Rounds", 620, 480)

        form = ttk.Frame(window, padding=(12, 10, 12, 0))
        form.pack(fill="x")
        rounds = data_manager.get_unique_rounds(self.df)
        box_a = self._choice_box(form, "Round A", rounds, row=0)
        box_b = self._choice_box(form, "Round B", rounds, row=1)
        if len(rounds) > 1:
            box_b.current(1)

        text = self._create_text_area(window, height=16)

        def compare():
            if not self._has_data():
                return
            if box_a.get() == box_b.get():
                messagebox.showerror("Invalid Input", "Please choose two different rounds.")
                return
            try:
                self._write_text(text, self._round_comparison_table(box_a.get(), box_b.get()))
            except ValueError as error:
                messagebox.showerror("Analyser Error", str(error))

        ttk.Button(window, text="Compare", command=compare, width=18).pack(pady=4)

        if rounds:
            compare()
        else:
            self._write_text(text, analyzer.NO_DATA_MESSAGE)
        self._add_close_button(window, window)
        return window

    def _round_comparison_table(self, round_a, round_b):
        """Build a text table that compares two rounds."""
        comparison = analyzer.compare_rounds(self.df, [round_a, round_b])
        number = self._format_number
        left, right = comparison[round_a], comparison[round_b]

        rows = [
            ("Average score", number(left["average_score"]), number(right["average_score"])),
            ("Average accuracy", number(left["average_accuracy"]) + "%",
             number(right["average_accuracy"]) + "%"),
            ("Highest score", number(left["highest_score"]), number(right["highest_score"])),
            ("Lowest score", number(left["lowest_score"]), number(right["lowest_score"])),
            ("Attempts", str(left["attempts"]), str(right["attempts"])),
            ("Difficulty", left["difficulty"], right["difficulty"]),
        ]

        lines = ["%-22s %-16s %-16s" % ("", round_a, round_b)]
        for title, value_a, value_b in rows:
            lines.append("%-22s %-16s %-16s" % (title, value_a, value_b))

        harder = round_a if left["average_accuracy"] <= right["average_accuracy"] else round_b
        lines.append("")
        lines.append("More difficult round (lower average accuracy): %s" % harder)
        lines.append(analyzer.describe_thresholds())
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # 8. Difficult rounds
    # ------------------------------------------------------------------ #

    def open_difficulty_window(self):
        """List all rounds from the hardest to the easiest."""
        window = self._open_child_window("Round Difficulty Report", 620, 480)

        ttk.Label(window, text="Difficulty: %s" % analyzer.describe_thresholds(),
                  font=self.subtitle_font, wraplength=560,
                  justify="left").pack(anchor="w", padx=12, pady=(10, 0))

        text = self._create_text_area(window, height=16)

        def refresh():
            if not self._has_data():
                return
            try:
                rounds = analyzer.find_difficult_rounds(self.df)
            except ValueError as error:
                messagebox.showerror("Analyser Error", str(error))
                return

            lines = ["Rounds from the most difficult to the easiest", ""]
            for item in rounds:
                lines.append("%-12s %-10s %6s%% average accuracy   (%d attempt(s), avg score %s)" % (
                    item["round_name"], item["difficulty"],
                    self._format_number(item["average_accuracy"]),
                    item["attempts"], self._format_number(item["average_score"])))
            lines.append("")
            lines.append("A low average accuracy means the round was difficult for the players.")
            self._write_text(text, "\n".join(lines))

        def show_chart():
            try:
                visualizer.plot_round_difficulty(self.df)
            except ValueError as error:
                messagebox.showinfo("No Chart", str(error))
            except Exception as error:
                messagebox.showerror("Plot Error", "The chart could not be created.\n%s" % error)

        ttk.Button(window, text="Show Difficulty Chart", command=show_chart,
                   width=24).pack(pady=4)

        if self.df is not None and not self.df.empty:
            refresh()
        else:
            self._write_text(text, analyzer.NO_DATA_MESSAGE)
        self._add_close_button(window, window)
        return window

    # ------------------------------------------------------------------ #
    # 9. Visual reports
    # ------------------------------------------------------------------ #

    def open_visual_reports_window(self):
        """Open the Matplotlib reports."""
        window = self._open_child_window("Visual Reports", 460, 330)

        frame = ttk.Frame(window, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Matplotlib reports", font=self.title_font).pack(anchor="w")
        ttk.Label(frame, text="Each report opens in its own chart window and uses the stored data.",
                  font=self.subtitle_font, wraplength=400,
                  justify="left").pack(anchor="w", pady=(4, 12))

        players = data_manager.get_unique_players(self.df)
        choice = ttk.Frame(frame)
        choice.pack(fill="x", pady=(0, 10))
        player_box = self._choice_box(choice, "Player for report 1", players)

        def open_chart(plot_function, argument=None):
            try:
                if argument is None:
                    plot_function(self.df)
                else:
                    plot_function(self.df, argument)
            except ValueError as error:
                messagebox.showinfo("No Chart", str(error))
            except Exception as error:
                messagebox.showerror("Plot Error", "The chart could not be created.\n%s" % error)

        ttk.Button(frame, text="1. Player Performance Across Attempts",
                   command=lambda: open_chart(visualizer.plot_player_performance, player_box.get()),
                   width=40).pack(pady=4)
        ttk.Button(frame, text="2. Quiz Round Difficulty",
                   command=lambda: open_chart(visualizer.plot_round_difficulty),
                   width=40).pack(pady=4)
        ttk.Button(frame, text="3. Player Average Score Comparison",
                   command=lambda: open_chart(visualizer.plot_player_comparison),
                   width=40).pack(pady=4)

        self._add_close_button(frame, window)
        return window
