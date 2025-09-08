from flask import Flask, render_template, jsonify
import pandas as pd
import os

app = Flask(__name__)

def load_data():
    excel_file = "Field_Days.xlsx"
    teams = pd.read_excel(excel_file, sheet_name="Teams")
    days = pd.read_excel(excel_file, sheet_name="Days")
    
    all_sheets = pd.ExcelFile(excel_file).sheet_names
    
    season_stats = {
        'total': pd.read_excel(excel_file, sheet_name="Stats")
    }
    
    for sheet in all_sheets:
        if sheet.endswith("Stats") and sheet != "Stats":
            year = sheet.replace(" Stats", "")
            try:
                season_stats[year] = pd.read_excel(excel_file, sheet_name=sheet)
            except:
                continue
            
    return teams, days, season_stats

@app.route('/')
def index():
    teams, days, season_stats = load_data()
    teams_data = teams.to_dict('records')
    
    days['Date'] = pd.to_datetime(days['Date'], format='%m/%d/%y')
    
    days = days.sort_values('Date', ascending=False)
    
    days_data = days.to_dict('records')
    for day in days_data:
        day['year'] = day['Date'].year
        day['Date'] = day['Date'].strftime('%m/%d/%Y')
    
    cleaned_season_stats = {}
    for year, data in season_stats.items():
        records = data.to_dict('records')
        cleaned_records = []
        for record in records:
            cleaned_record = {}
            for key, value in record.items():
                if pd.isna(value):
                    cleaned_record[key] = None
                else:
                    cleaned_record[key] = value
            cleaned_records.append(cleaned_record)
        cleaned_season_stats[year] = cleaned_records
    
    return render_template('index.html', 
                         teams=teams_data,
                         days=days_data,
                         season_stats=cleaned_season_stats)

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "message": "Application is running"})

if __name__ == '__main__':
    port = 5001
    app.run(host='0.0.0.0', port=port, debug=True) 