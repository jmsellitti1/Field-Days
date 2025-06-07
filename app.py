from flask import Flask, render_template, jsonify
import pandas as pd
import os

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
    teams_data = teams.to_dict('records')
    return render_template('index.html', 
                         stats=stats.to_dict('records'),
                         teams=teams_data,
                         days=days.to_dict('records'))

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "message": "Application is running"})

if __name__ == '__main__':
    port = 5001
    app.run(host='0.0.0.0', port=port, debug=True) 