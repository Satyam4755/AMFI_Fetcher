import os
import shutil
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from scripts.calculate_performance import main as calculate_all_perf

PROJECT_ROOT = "/Users/smritisoni/Desktop/AMFI_Fetcher"
HISTORICAL_DIR = os.path.join(PROJECT_ROOT, "data", "sif", "scheme", "nav", "historical")
PERF_DIR = os.path.join(PROJECT_ROOT, "data", "sif", "scheme", "performance")
BACKUP_DIR = os.path.join(PROJECT_ROOT, "temp", "backup_nav")

TARGET_SIFS = ["sif_1", "sif_2", "sif_3"]

def generate_synthetic_data(sif_code, start_nav=10.0, days=90):
    # End date is today (e.g., 2026-07-13)
    end_date = datetime(2026, 7, 13)
    start_date = end_date - timedelta(days=days)
    
    dates = []
    navs = []
    current_nav = start_nav
    
    np.random.seed(hash(sif_code) % (2**32)) # deterministic random per SIF
    
    curr_date = start_date
    while curr_date <= end_date:
        # Skip weekends (Saturday=5, Sunday=6)
        if curr_date.weekday() < 5:
            dates.append(curr_date)
            # Drift between -0.5% and 0.6% daily
            daily_return = np.random.uniform(-0.005, 0.006)
            current_nav = current_nav * (1 + daily_return)
            navs.append(round(current_nav, 4))
        curr_date += timedelta(days=1)
        
    df = pd.DataFrame({
        "sif_code": [sif_code.upper().replace("_", "-")] * len(dates),
        "nav_date": [d.strftime("%d-%b-%Y") for d in dates],
        "nav": navs
    })
    return df

def backup_and_setup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    for sif in TARGET_SIFS:
        csv_path = os.path.join(HISTORICAL_DIR, f"{sif}.csv")
        backup_path = os.path.join(BACKUP_DIR, f"{sif}.csv")
        if os.path.exists(csv_path):
            shutil.copy(csv_path, backup_path)
            
        # Generate synthetic data
        df = generate_synthetic_data(sif)
        df.to_csv(csv_path, index=False)

def restore_and_cleanup():
    for sif in TARGET_SIFS:
        csv_path = os.path.join(HISTORICAL_DIR, f"{sif}.csv")
        backup_path = os.path.join(BACKUP_DIR, f"{sif}.csv")
        if os.path.exists(backup_path):
            shutil.copy(backup_path, csv_path)
            os.remove(backup_path)
        else:
            if os.path.exists(csv_path):
                os.remove(csv_path)
    
    if os.path.exists(BACKUP_DIR) and not os.listdir(BACKUP_DIR):
        os.rmdir(BACKUP_DIR)

def manual_calculation(df):
    df = df.copy()
    df['nav_date'] = pd.to_datetime(df['nav_date'], format='%d-%b-%Y')
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    latest_nav = latest['nav']
    prev_nav = prev['nav']
    latest_date = latest['nav_date']
    
    daily_change = latest_nav - prev_nav
    
    def get_past_nav(target_date):
        past = df[df['nav_date'] <= target_date]
        if past.empty: return None
        return past.iloc[-1]['nav']
        
    def get_return(past_nav):
        if past_nav is None: return None
        return round(((latest_nav / past_nav) - 1) * 100, 2)
        
    ret_1w = get_return(get_past_nav(latest_date - timedelta(days=7)))
    ret_1m = get_return(get_past_nav(latest_date - pd.DateOffset(months=1)))
    ret_3m = get_return(get_past_nav(latest_date - pd.DateOffset(months=3)))
    ret_since = get_return(df.iloc[0]['nav'])
    
    high = df['nav'].max()
    low = df['nav'].min()
    
    daily_returns = df['nav'].pct_change().dropna()
    vol = round(daily_returns.std() * np.sqrt(252) * 100, 2)
    
    df['peak'] = df['nav'].cummax()
    df['dd'] = (df['nav'] - df['peak']) / df['peak']
    dd = round(df['dd'].min() * 100, 2)
    
    return {
        "latest_nav": round(latest_nav, 4),
        "previous_nav": round(prev_nav, 4),
        "daily_change_absolute": round(daily_change, 4),
        "1_week": ret_1w,
        "1_month": ret_1m,
        "3_month": ret_3m,
        "since_launch": ret_since,
        "highest_nav": round(high, 4),
        "lowest_nav": round(low, 4),
        "volatility_annualized": vol,
        "max_drawdown_percentage": dd
    }

def main():
    print("# Performance Module Synthetic Validation Report\n")
    
    try:
        backup_and_setup()
        
        print("Running full pipeline on synthetic data...")
        # Direct function call instead of subprocess
        calculate_all_perf()
        
        all_match = True
        
        for sif in TARGET_SIFS:
            print(f"## Validation for {sif.upper()}")
            print("| Metric | Expected (Manual Calc) | Calculated (Pipeline JSON) | Match |")
            print("|---|---|---|---|")
            
            csv_path = os.path.join(HISTORICAL_DIR, f"{sif}.csv")
            df = pd.read_csv(csv_path)
            expected = manual_calculation(df)
            
            json_path = os.path.join(PERF_DIR, f"{sif}.json")
            with open(json_path, "r") as f:
                actual = json.load(f)
                
            metrics_to_check = [
                ("Latest NAV", expected["latest_nav"], actual["latest_nav"]),
                ("Previous NAV", expected["previous_nav"], actual["previous_nav"]),
                ("Daily Change Abs", expected["daily_change_absolute"], actual["daily_change_absolute"]),
                ("1 Week Return", expected["1_week"], actual["returns"]["1_week"]),
                ("1 Month Return", expected["1_month"], actual["returns"]["1_month"]),
                ("3 Month Return", expected["3_month"], actual["returns"]["3_month"]),
                ("Since Launch Return", expected["since_launch"], actual["returns"]["since_launch"]),
                ("Highest NAV", expected["highest_nav"], actual["highest_nav"]),
                ("Lowest NAV", expected["lowest_nav"], actual["lowest_nav"]),
                ("Volatility", expected["volatility_annualized"], actual["risk_metrics"]["volatility_annualized"]),
                ("Max Drawdown", expected["max_drawdown_percentage"], actual["risk_metrics"]["max_drawdown_percentage"])
            ]
            
            for name, exp, act in metrics_to_check:
                match = exp == act
                if not match:
                    all_match = False
                match_str = "✅ Yes" if match else "❌ No"
                print(f"| {name} | {exp} | {act} | {match_str} |")
            print("\n")
            
        if all_match:
            print("### Conclusion: All metrics perfectly matched exactly! The calculations are deterministic and verified.")
        else:
            print("### Conclusion: Some metrics did NOT match! Check logic.")
            
    finally:
        restore_and_cleanup()
        # Restore JSONs to their original state by running calculate_all_perf again
        calculate_all_perf()
        print("Restored original files and cleaned up.")

if __name__ == "__main__":
    main()
