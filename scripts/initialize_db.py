"""
Initialize database and perform initial data collection.
Run this once to set up the project.
"""

import sys
import os

# Add parent directory to path so we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database import init_database
from src.data_collector import DataCollector
from src.risk_calculator import RiskCalculator


def main():
    print("="*60)
    print("DEFI YIELD RISK ANALYZER - INITIALIZATION")
    print("="*60)
    
    # Step 1: Initialize database
    print("\nStep 1: Initializing database...")
    init_database()
    
    # Step 2: Collect data
    print("\nStep 2: Collecting pool data and historical metrics...")
    print("(This will take 10-15 minutes for 500 pools)")
    
    collector = DataCollector()
    collector.run_full_collection()
    
    # Step 3: Calculate risk scores
    print("\nStep 3: Calculating risk scores...")
    
    calculator = RiskCalculator()
    calculator.calculate_all_risks()
    
    # Step 4: Show summary
    print("\n" + "="*60)
    print("INITIALIZATION COMPLETE!")
    print("="*60)
    
    summary = calculator.get_risk_summary()
    
    if len(summary) > 0:
        print(f"\n✓ Database populated with {len(summary)} pools")
        print(f"✓ Risk scores calculated")
        print(f"\nRisk distribution:")
        print(summary['risk_level'].value_counts())
        
        print(f"\nYou can now run the dashboard:")
        print(f"  streamlit run dashboard/app.py")
    else:
        print("\n⚠ No pools processed. Check for errors above.")


if __name__ == "__main__":
    main()