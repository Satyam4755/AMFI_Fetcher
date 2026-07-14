import pandas as pd
import numpy as np
from datetime import datetime

def calculate_performance_metrics(df):
    """
    Calculates performance metrics for a SIF from a pandas DataFrame of historical NAV data.
    Expected DataFrame columns: 'sif_code', 'nav_date', 'nav'
    """
    if df is None or df.empty:
        return None
        
    df = df.copy()
    
    # Ensure correct data types (AMFI date format is usually dd-MMM-yyyy)
    df['nav_date'] = pd.to_datetime(df['nav_date'], format='%d-%b-%Y')
    df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
    
    # Drop rows with invalid NAV
    df = df.dropna(subset=['nav'])
    
    if df.empty:
        return None
        
    # Sort chronologically
    df = df.sort_values('nav_date').reset_index(drop=True)
    
    sif_code = df['sif_code'].iloc[0]
    latest_row = df.iloc[-1]
    latest_nav = float(latest_row['nav'])
    latest_date = latest_row['nav_date']
    
    previous_nav = float(df.iloc[-2]['nav']) if len(df) > 1 else None
    daily_change_percentage = round(((latest_nav / previous_nav) - 1) * 100, 2) if previous_nav and previous_nav > 0 else None
    
    def get_return(horizon_date):
        # Find closest date that is <= horizon_date
        past_df = df[df['nav_date'] <= horizon_date]
        if past_df.empty:
            return None
        past_nav = float(past_df.iloc[-1]['nav'])
        if past_nav <= 0:
            return None
        return round(((latest_nav / past_nav) - 1) * 100, 2)
        
    first_date = df.iloc[0]['nav_date']
        
    metrics = {
        "sif_code": sif_code,
        "returns": {
            "1_day": daily_change_percentage,
            "1_week": get_return(latest_date - pd.Timedelta(days=7)),
            "1_month": get_return(latest_date - pd.DateOffset(months=1)),
            "3_month": get_return(latest_date - pd.DateOffset(months=3)),
            "6_month": get_return(latest_date - pd.DateOffset(months=6)),
            "1_year": get_return(latest_date - pd.DateOffset(years=1)),
            "2_year": get_return(latest_date - pd.DateOffset(years=2)),
            "3_year": get_return(latest_date - pd.DateOffset(years=3)),
            "5_year": get_return(latest_date - pd.DateOffset(years=5)),
            "7_year": get_return(latest_date - pd.DateOffset(years=7)),
            "10_year": get_return(latest_date - pd.DateOffset(years=10)),
            "since_launch": get_return(first_date)
        },
        "last_updated": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    }
    
    # Handle NaNs from Pandas calculations (convert to None for JSON serialization)
    def clean_dict(d):
        for k, v in d.items():
            if isinstance(v, dict):
                clean_dict(v)
            elif isinstance(v, float) and np.isnan(v):
                d[k] = None
        return d
        
    return clean_dict(metrics)
