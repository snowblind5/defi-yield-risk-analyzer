"""
Update existing data with latest metrics.
This script is designed to be run by GitHub Actions on a schedule.
"""

import sys
import os
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database import get_session, Pool
from src.data_collector import DataCollector, DeFiLlamaClient
from src.risk_calculator import RiskCalculator


def update_current_metrics():
    """Update current APY/TVL for all pools"""
    print("="*60)
    print("UPDATING CURRENT POOL METRICS")
    print("="*60)
    
    client = DeFiLlamaClient()
    session = get_session()
    
    # Fetch current pool data
    all_pools = client.get_all_pools()
    
    if not all_pools:
        print("✗ Failed to fetch current pool data")
        return False
    
    print(f"✓ Fetched {len(all_pools)} pools from API")
    
    # Create lookup dictionary
    pools_dict = {p['pool']: p for p in all_pools}
    
    # Update pools in database
    db_pools = session.query(Pool).all()
    updated = 0
    
    for pool in db_pools:
        if pool.pool_id in pools_dict:
            api_data = pools_dict[pool.pool_id]
            pool.last_updated = datetime.now(timezone.utc).replace(tzinfo=None)
            updated += 1
    
    session.commit()
    print(f"✓ Updated {updated} pools")
    
    return True


def collect_recent_history():
    """Collect last 7 days of historical data for all pools"""
    print("\n" + "="*60)
    print("COLLECTING RECENT HISTORICAL DATA")
    print("="*60)
    
    collector = DataCollector()
    
    # Collect with resume=True to skip pools with very recent data
    collector.collect_historical_data(resume=True)
    
    return True


def recalculate_risks():
    """Recalculate risk scores for all pools"""
    print("\n" + "="*60)
    print("RECALCULATING RISK SCORES")
    print("="*60)
    
    calculator = RiskCalculator()
    calculator.calculate_all_risks()
    
    return True


def main():
    """Run full update pipeline"""
    print("="*60)
    print("DEFI YIELD RISK ANALYZER - DATA UPDATE")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("="*60)
    
    success = True
    
    # Step 1: Update current metrics
    if not update_current_metrics():
        success = False
    
    # Step 2: Collect recent history
    if not collect_recent_history():
        success = False
    
    # Step 3: Recalculate risks
    if not recalculate_risks():
        success = False
    
    # Summary
    print("\n" + "="*60)
    if success:
        print("✓ UPDATE COMPLETE!")
    else:
        print("⚠ UPDATE COMPLETED WITH ERRORS")
    print("="*60)
    
    calculator = RiskCalculator()
    summary = calculator.get_risk_summary()
    
    if len(summary) > 0:
        print(f"\nPools with risk scores: {len(summary)}")
        print(f"\nRisk distribution:")
        print(summary['risk_level'].value_counts())
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)