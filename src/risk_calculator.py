"""
Risk scoring calculator for DeFi yield pools.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from sqlalchemy import func

from src.database import get_session, Pool, PoolMetric, PoolRiskScore
from src.config import RISK_WEIGHTS, RISK_LEVELS


class RiskCalculator:
    """Calculate risk scores for DeFi yield pools"""
    
    def __init__(self):
        self.session = get_session()
    
    def get_pool_metrics_df(self, pool_id: int, days: int = 30) -> Optional[pd.DataFrame]:
        """
        Get historical metrics for a pool as DataFrame.
        
        Args:
            pool_id: Database pool ID
            days: Number of days of history to fetch
            
        Returns:
            DataFrame with metrics or None if insufficient data
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        metrics = self.session.query(PoolMetric).filter(
            PoolMetric.pool_id == pool_id,
            PoolMetric.date >= cutoff_date
        ).order_by(PoolMetric.date).all()
        
        if len(metrics) < 7:  # Need at least 1 week of data
            return None
        
        # Convert to DataFrame
        data = [{
            'date': m.date,
            'apy': m.apy,
            'tvl_usd': m.tvl_usd
        } for m in metrics]
        
        return pd.DataFrame(data)
    
    def calculate_apy_volatility(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate APY volatility metrics.
        
        Args:
            df: DataFrame with 'apy' column
            
        Returns:
            Dictionary with mean and std dev
        """
        apy_values = df['apy'].dropna()
        
        if len(apy_values) < 2:
            return {'mean': 0.0, 'std': 0.0}
        
        return {
            'mean': float(apy_values.mean()),
            'std': float(apy_values.std())
        }
    
    def calculate_tvl_volatility(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate TVL volatility metrics using coefficient of variation.
        
        Args:
            df: DataFrame with 'tvl_usd' column
            
        Returns:
            Dictionary with mean and coefficient of variation
        """
        tvl_values = df['tvl_usd'].dropna()
        
        if len(tvl_values) < 2:
            return {'mean': 0.0, 'cv': 0.0}
        
        mean_tvl = float(tvl_values.mean())
        std_tvl = float(tvl_values.std())
        
        # Coefficient of variation (lower is more stable)
        cv = (std_tvl / mean_tvl * 100) if mean_tvl > 0 else 0.0
        
        return {
            'mean': mean_tvl,
            'cv': cv
        }
    
    def calculate_liquidity_score(self, mean_tvl: float) -> float:
        """
        Calculate liquidity score based on TVL (0-100 scale).
        Higher TVL = higher score = lower risk
        
        Args:
            mean_tvl: Mean TVL in USD
            
        Returns:
            Liquidity score (0-100)
        """
        # Logarithmic scale for TVL
        # $100k TVL = ~30 score
        # $1M TVL = ~50 score
        # $10M TVL = ~70 score
        # $100M TVL = ~90 score
        # $1B TVL = ~100 score
        
        if mean_tvl <= 0:
            return 0.0
        
        # Log scale with floor at $10k
        log_tvl = np.log10(max(mean_tvl, 10_000))
        
        # Map log(10k) to log(1B) -> 0 to 100
        # log(10k) = 4, log(1B) = 9
        score = (log_tvl - 4) / (9 - 4) * 100
        
        return float(np.clip(score, 0, 100))
    
    def calculate_stability_score(self, apy_std: float, tvl_cv: float) -> float:
        """
        Calculate stability score based on APY and TVL volatility (0-100 scale).
        Lower volatility = higher score = lower risk
        
        Args:
            apy_std: Standard deviation of APY
            tvl_cv: Coefficient of variation of TVL
            
        Returns:
            Stability score (0-100)
        """
        # APY volatility component (inverse score)
        # 0% std = 100, 50% std = 0
        apy_component = max(0, 100 - (apy_std * 2))
        
        # TVL volatility component (inverse score)
        # 0% CV = 100, 100% CV = 0
        tvl_component = max(0, 100 - tvl_cv)
        
        # Weighted average (60% APY stability, 40% TVL stability)
        stability_score = apy_component * 0.6 + tvl_component * 0.4
        
        return float(np.clip(stability_score, 0, 100))
    
    def calculate_composite_risk_score(
        self, 
        liquidity_score: float, 
        stability_score: float
    ) -> float:
        """
        Calculate composite risk score (0-100 scale).
        Lower score = lower risk (safer)
        
        Args:
            liquidity_score: Liquidity score (0-100)
            stability_score: Stability score (0-100)
            
        Returns:
            Composite risk score (0-100, lower is safer)
        """
        # Invert scores so lower = safer
        liquidity_risk = 100 - liquidity_score
        stability_risk = 100 - stability_score
        
        # Weighted combination from config
        composite_risk = (
            stability_risk * (RISK_WEIGHTS['apy_volatility'] + RISK_WEIGHTS['tvl_volatility']) +
            liquidity_risk * RISK_WEIGHTS['liquidity']
        )
        
        return float(np.clip(composite_risk, 0, 100))
    
    def calculate_risk_for_pool(self, pool: Pool) -> Optional[PoolRiskScore]:
        """
        Calculate all risk metrics for a single pool.
        
        Args:
            pool: Pool object from database
            
        Returns:
            PoolRiskScore object or None if insufficient data
        """
        # Get 30 days of historical data
        df = self.get_pool_metrics_df(pool.id, days=30)
        
        if df is None or len(df) < 7:
            return None
        
        # Calculate metrics
        apy_metrics = self.calculate_apy_volatility(df)
        tvl_metrics = self.calculate_tvl_volatility(df)
        
        liquidity_score = self.calculate_liquidity_score(tvl_metrics['mean'])
        stability_score = self.calculate_stability_score(apy_metrics['std'], tvl_metrics['cv'])
        composite_risk = self.calculate_composite_risk_score(liquidity_score, stability_score)
        
        # Create risk score object
        risk_score = PoolRiskScore(
            pool_id=pool.id,
            calculation_date=datetime.now(timezone.utc).replace(tzinfo=None),
            apy_volatility_30d=apy_metrics['std'],
            tvl_volatility_30d=tvl_metrics['cv'],
            apy_mean_30d=apy_metrics['mean'],
            tvl_mean_30d=tvl_metrics['mean'],
            liquidity_score=liquidity_score,
            stability_score=stability_score,
            composite_risk_score=composite_risk
        )
        
        return risk_score
    
    def calculate_all_risks(self):
        """Calculate risk scores for all pools with sufficient data"""
        pools = self.session.query(Pool).all()
        
        print("="*60)
        print("CALCULATING RISK SCORES")
        print("="*60)
        print(f"\nProcessing {len(pools)} pools...")
        
        calculated = 0
        skipped = 0
        errors = 0
        
        for i, pool in enumerate(pools, 1):
            try:
                # Check if pool has enough data
                metric_count = self.session.query(PoolMetric).filter_by(pool_id=pool.id).count()
                
                if metric_count < 7:
                    skipped += 1
                    continue
                
                # Calculate risk score
                risk_score = self.calculate_risk_for_pool(pool)
                
                if risk_score is None:
                    skipped += 1
                    continue
                
                # Delete old risk scores for this pool
                self.session.query(PoolRiskScore).filter_by(pool_id=pool.id).delete()
                
                # Add new risk score
                self.session.add(risk_score)
                self.session.commit()
                
                calculated += 1
                
                if calculated % 50 == 0:
                    print(f"  Progress: {calculated} calculated, {skipped} skipped")
                
            except Exception as e:
                errors += 1
                self.session.rollback()
                if errors <= 5:  # Show first 5 errors
                    print(f"  ✗ Error calculating risk for {pool.project} - {pool.symbol}: {e}")
        
        print(f"\n{'='*60}")
        print(f"Risk calculation complete!")
        print(f"  Calculated: {calculated}")
        print(f"  Skipped (insufficient data): {skipped}")
        print(f"  Errors: {errors}")
        print(f"{'='*60}")
    
    def get_risk_summary(self) -> pd.DataFrame:
        """
        Get summary of risk scores across all pools.
        
        Returns:
            DataFrame with risk distribution
        """
        # Query all risk scores with pool info
        results = self.session.query(
            Pool.project,
            Pool.symbol,
            Pool.chain,
            PoolRiskScore.composite_risk_score,
            PoolRiskScore.apy_mean_30d,
            PoolRiskScore.tvl_mean_30d
        ).join(
            PoolRiskScore, Pool.id == PoolRiskScore.pool_id
        ).all()
        
        df = pd.DataFrame(results, columns=[
            'project', 'symbol', 'chain', 
            'risk_score', 'apy_30d', 'tvl_30d'
        ])
        
        # Add risk level classification
        def classify_risk(score):
            if score <= RISK_LEVELS['low'][1]:
                return 'Low'
            elif score <= RISK_LEVELS['medium'][1]:
                return 'Medium'
            else:
                return 'High'
        
        df['risk_level'] = df['risk_score'].apply(classify_risk)
        
        return df


if __name__ == "__main__":
    # Calculate risks when run directly
    calculator = RiskCalculator()
    calculator.calculate_all_risks()
    
    # Show summary
    print("\n" + "="*60)
    print("RISK SUMMARY")
    print("="*60)
    
    summary = calculator.get_risk_summary()
    
    if len(summary) > 0:
        print(f"\nTotal pools with risk scores: {len(summary)}")
        print(f"\nRisk distribution:")
        print(summary['risk_level'].value_counts())
        
        print(f"\nTop 10 safest pools (lowest risk):")
        print(summary.nsmallest(10, 'risk_score')[['project', 'symbol', 'risk_score', 'apy_30d']])
        
        print(f"\nTop 10 riskiest pools:")
        print(summary.nlargest(10, 'risk_score')[['project', 'symbol', 'risk_score', 'apy_30d']])