"""
main.py
=======
Entry point of the Quiz Performance Analyzer.

Run the application with:
 
    python main.py

The program works completely offline: it only reads and writes the local CSV
file inside the ``data`` folder.
"""

from gui import QuizAnalyzerGUI
import data_manager


def main():
    """Prepare the local data file and start the Tkinter application."""
    try:
        # Create the data folder and file when they do not exist yet.
        data_manager.ensure_data_file()
    except data_manager.DataError as error:
        print("Warning: %s" % error)
        print("The application will start, but saving results may fail.")

    app = QuizAnalyzerGUI()
    app.run()


if __name__ == "__main__":
    main()
