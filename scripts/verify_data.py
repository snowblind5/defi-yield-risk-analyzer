"""
Verify that data collection was successful and database is properly populated.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database import get_session, Pool, PoolMetric, PoolRiskScore
from src.risk_calculator import RiskCalculator
from datetime import datetime, timedelta, timezone
import pandas as pd


def check_database():
    """Check database contents"""
    print("="*60)
    print("DATABASE VERIFICATION")
    print("="*60)
    
    session = get_session()
    
    # Count records
    pool_count = session.query(Pool).count()
    metric_count = session.query(PoolMetric).count()
    risk_count = session.query(PoolRiskScore).count()
    
    print(f"\n📊 Record Counts:")
    print(f"  Pools: {pool_count}")
    print(f"  Metrics: {metric_count}")
    print(f"  Risk Scores: {risk_count}")
    
    if pool_count == 0:
        print("\n❌ ERROR: No pools in database!")
        return False
    
    if metric_count == 0:
        print("\n❌ ERROR: No metrics in database!")
        return False
    
    # Check metrics per pool
    avg_metrics = metric_count / pool_count if pool_count > 0 else 0
    print(f"\n📈 Average metrics per pool: {avg_metrics:.1f}")
    
    # Check date range
    oldest_metric = session.query(PoolMetric).order_by(PoolMetric.date).first()
    newest_metric = session.query(PoolMetric).order_by(PoolMetric.date.desc()).first()
    
    if oldest_metric and newest_metric:
        date_range = (newest_metric.date - oldest_metric.date).days
        print(f"📅 Data range: {oldest_metric.date.date()} to {newest_metric.date.date()} ({date_range} days)")
    
    # Sample some pools
    print(f"\n🔍 Sample pools:")
    sample_pools = session.query(Pool).limit(5).all()
    for pool in sample_pools:
        pool_metrics = session.query(PoolMetric).filter_by(pool_id=pool.id).count()
        print(f"  {pool.project} - {pool.symbol} ({pool.chain}): {pool_metrics} metrics")
    
    return True


def test_risk_calculator():
    """Test risk calculator on sample pools"""
    print("\n" + "="*60)
    print("RISK CALCULATOR TEST")
    print("="*60)
    
    calculator = RiskCalculator()
    session = get_session()
    
    # Get pools with most metrics
    pools_with_data = []
    for pool in session.query(Pool).limit(10).all():
        metric_count = session.query(PoolMetric).filter_by(pool_id=pool.id).count()
        if metric_count >= 7:
            pools_with_data.append((pool, metric_count))
    
    if not pools_with_data:
        print("\n❌ ERROR: No pools with sufficient data (need 7+ days)")
        return False
    
    print(f"\n✓ Found {len(pools_with_data)} pools with sufficient data")
    
    # Test on first pool
    test_pool = pools_with_data[0][0]
    print(f"\n🧪 Testing risk calculation on: {test_pool.project} - {test_pool.symbol}")
    
    try:
        risk_score = calculator.calculate_risk_for_pool(test_pool)
        
        if risk_score:
            print(f"\n✓ Risk calculation successful!")
            print(f"  APY Volatility: {risk_score.apy_volatility_30d:.2f}%")
            print(f"  TVL Volatility: {risk_score.tvl_volatility_30d:.2f}%")
            print(f"  Liquidity Score: {risk_score.liquidity_score:.1f}/100")
            print(f"  Stability Score: {risk_score.stability_score:.1f}/100")
            print(f"  Composite Risk: {risk_score.composite_risk_score:.1f}/100")
            return True
        else:
            print(f"\n❌ Risk calculation returned None")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR during risk calculation: {e}")
        import traceback
        traceback.print_exc()
        return False


def calculate_all_risks():
    """Calculate risk scores for all pools"""
    print("\n" + "="*60)
    print("CALCULATING ALL RISK SCORES")
    print("="*60)
    
    calculator = RiskCalculator()
    calculator.calculate_all_risks()
    
    return True


def show_summary():
    """Show data summary"""
    print("\n" + "="*60)
    print("DATA SUMMARY")
    print("="*60)
    
    calculator = RiskCalculator()
    summary = calculator.get_risk_summary()
    
    if len(summary) == 0:
        print("\n⚠️ No risk scores calculated yet")
        return
    
    print(f"\n📊 Pools with risk scores: {len(summary)}")
    
    print(f"\n🎯 Risk Level Distribution:")
    risk_dist = summary['risk_level'].value_counts()
    for level, count in risk_dist.items():
        pct = (count / len(summary)) * 100
        print(f"  {level}: {count} ({pct:.1f}%)")
    
    print(f"\n💰 Top 10 Safest High-Yield Pools:")
    safe_pools = summary[summary['risk_score'] < 40].nlargest(10, 'apy_30d')
    if len(safe_pools) > 0:
        print(safe_pools[['project', 'symbol', 'chain', 'apy_30d', 'risk_score']].to_string(index=False))
    else:
        print("  (No pools with risk < 40)")
    
    print(f"\n⚠️ Top 10 Riskiest Pools:")
    risky_pools = summary.nlargest(10, 'risk_score')
    print(risky_pools[['project', 'symbol', 'chain', 'apy_30d', 'risk_score']].to_string(index=False))
    
    print(f"\n📈 Statistics:")
    print(f"  Mean APY: {summary['apy_30d'].mean():.2f}%")
    print(f"  Median APY: {summary['apy_30d'].median():.2f}%")
    print(f"  Mean Risk Score: {summary['risk_score'].mean():.2f}")
    print(f"  Mean TVL: ${summary['tvl_30d'].mean():,.0f}")


def main():
    """Run all verification checks"""
    print("\n" + "🔍 STARTING VERIFICATION..." + "\n")
    
    # Step 1: Check database
    if not check_database():
        print("\n❌ Database verification failed!")
        return False
    
    # Step 2: Test risk calculator
    if not test_risk_calculator():
        print("\n❌ Risk calculator test failed!")
        return False
    
    # Step 3: Calculate all risks
    if not calculate_all_risks():
        print("\n❌ Risk calculation failed!")
        return False
    
    # Step 4: Show summary
    show_summary()
    
    # Final verdict
    print("\n" + "="*60)
    print("✅ ALL CHECKS PASSED!")
    print("="*60)
    print("\nYou can now run the dashboard:")
    print("  streamlit run dashboard/app.py")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)