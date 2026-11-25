### Python file to parse and update (attached) excel sheet with field day data

Because my friends and I are too competitive

2023 Update: Hosted on Heroku app at https://jeffs-field-days-app-abb1b7e00ee5.herokuapp.com/

2025 Update: Yeah I ain't paying for that anymore. Hosted on your computer with python app.py

2026 Update: Still ain't paying for that, but hosted for free at https://jmsellitti1.github.io/Field-Days/ now!

## Project overview

Field Days tracks players, team combinations, game results, MVP and Clown of the Match awards
across each season. The source data is stored in `Field_Days.xlsx`; `app.py` provides a local
Flask view, while `program.py` updates the spreadsheet, recalculates statistics, and exports
JSON used by the GitHub Pages site in `docs/`.

## Startup guide

1. From the project directory, install the Python dependencies:

   ```bash
   python3 -m pip install -r requirements.txt
   ```

2. For the Flask application, start the local server:

   ```bash
   python3 app.py
   ```

   Open `http://localhost:5001`.

3. To regenerate the spreadsheet statistics and static site data, run:

   ```bash
   python3 program.py
   ```

4. To preview the GitHub Pages site locally:

   ```bash
   cd docs
   python3 -m http.server 8000
   ```

   Open `http://localhost:8000`.

## Adding a new day

1. Make sure `Field_Days.xlsx` is present and close it if it is open in another application.
2. Run `python3 program.py`.
3. Answer `y` when asked whether to add a new day.
4. Enter the date, both teams (comma-separated player names), overall score, game results,
   MVP, and Clown of the Match when prompted. The program validates the entries and asks for
   confirmation before saving.
5. Let the program finish recalculating all-time and season statistics and exporting the
   updated JSON files under `docs/data/`.
6. Review the changes, then commit and push `Field_Days.xlsx` and the files in `docs/data/`.
