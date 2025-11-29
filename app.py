from flask import Flask, render_template, jsonify
import pandas as pd

app = Flask(__name__)

def load_data():
    excel_file = "Field_Days.xlsx"
    excel = pd.ExcelFile(excel_file)
    
    teams = excel.parse(sheet_name="Teams")
    days = excel.parse(sheet_name="Days")
    
    season_stats = {
        'total': excel.parse(sheet_name="Stats")
    }
    
    for sheet in excel.sheet_names:
        if sheet.endswith(" Stats") and sheet != "Stats":
            year = sheet.replace(" Stats", "")
            try:
                season_stats[year] = excel.parse(sheet_name=sheet)
            except (ValueError, KeyError) as e:
                continue
            
    return teams, days, season_stats

@app.route('/')
def index():
    teams, days, season_stats = load_data()
    teams_data = teams.to_dict('records')

    days['Date'] = pd.to_datetime(days['Date'], format='mixed', errors='coerce')
    days = days.sort_values('Date', ascending=False)
    
    days_data = days.to_dict('records')
    for day in days_data:
        date_obj = day['Date']
        if pd.isna(date_obj):
            day['year'] = None
            day['Date'] = ''
        else:
            if not isinstance(date_obj, pd.Timestamp):
                date_obj = pd.to_datetime(date_obj, format='mixed', errors='coerce')
            if pd.isna(date_obj):
                day['year'] = None
                day['Date'] = ''
            else:
                day['year'] = date_obj.year
                day['Date'] = date_obj.strftime('%m/%d/%Y')
    
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