from flask import Flask, render_template
import pandas as pd

app = Flask(__name__)

def load_data():
    excel_file = "Field_Days.xlsx"
    stats = pd.read_excel(excel_file, sheet_name="Stats")
    teams = pd.read_excel(excel_file, sheet_name="Teams")
    days = pd.read_excel(excel_file, sheet_name="Days")
    return stats, teams, days

@app.route('/')
def index():
    stats, teams, days = load_data()
    return render_template('index.html', 
                         stats=stats.to_dict('records'),
                         teams=teams.to_dict('records'),
                         days=days.to_dict('records'))

if __name__ == '__main__':
    app.run(debug=True) 