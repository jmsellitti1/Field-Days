from flask import Flask, render_template, jsonify
import pandas as pd
import os

app = Flask(__name__)

def load_data():
    excel_file = "Field_Days.xlsx"
    teams = pd.read_excel(excel_file, sheet_name="Teams")
    days = pd.read_excel(excel_file, sheet_name="Days")
    
    # Get all sheet names
    all_sheets = pd.ExcelFile(excel_file).sheet_names
    
    # Load all stats sheets including total stats
    season_stats = {
        'total': pd.read_excel(excel_file, sheet_name="Stats")
    }
    
    # Load season-specific stats by finding sheets that end with "Stats" (excluding the total "Stats" sheet)
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
    
    # Convert dates to datetime if they aren't already
    days['Date'] = pd.to_datetime(days['Date'])
    
    # Sort days by date in descending order (newest first)
    days = days.sort_values('Date', ascending=False)
    
    # Add year to each day's data
    days_data = days.to_dict('records')
    for day in days_data:
        day['year'] = day['Date'].year
        # Convert datetime to string for JSON serialization
        day['Date'] = day['Date'].strftime('%m/%d/%Y')
    
    return render_template('index.html', 
                         teams=teams_data,
                         days=days_data,
                         season_stats={year: data.to_dict('records') for year, data in season_stats.items()})

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "message": "Application is running"})

if __name__ == '__main__':
    port = 5001
    app.run(host='0.0.0.0', port=port, debug=True) 