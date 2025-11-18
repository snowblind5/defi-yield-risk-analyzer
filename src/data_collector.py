"""
Data collector for fetching DeFi yield data from DeFi Llama API.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time

from src.config import (
    DEFILLAMA_BASE_URL,
    DEFILLAMA_YIELDS_URL,
    MIN_TVL_USD,
    MIN_APY,
    MAX_APY,
    TOP_POOLS_LIMIT,
    DAYS_OF_HISTORY
)
from src.database import get_session, Pool, PoolMetric
from sqlalchemy.exc import IntegrityError


class DeFiLlamaClient:
    """Client for interacting with DeFi Llama API with rate limiting"""
    
    def __init__(self):
        self.base_url = DEFILLAMA_BASE_URL
        self.yields_url = DEFILLAMA_YIELDS_URL
        self.session = requests.Session()
        self.max_retries = 3
        self.base_delay = 1.0  # Increased from 0.5s
    
    def get_all_pools(self) -> List[Dict]:
        """
        Fetch all pools from DeFi Llama yields API.
        
        Returns:
            List of pool dictionaries
        """
        try:
            response = self.session.get(f"{self.yields_url}/pools", timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Handle both direct list and nested 'data' key
            if isinstance(data, dict) and 'data' in data:
                pools = data['data']
            else:
                pools = data
                
            print(f"✓ Fetched {len(pools)} total pools from DeFi Llama")
            return pools
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Error fetching pools: {e}")
            return []
    
    def get_pool_historical_data(self, pool_id: str, retry_count: int = 0) -> Optional[pd.DataFrame]:
        """
        Fetch historical data for a specific pool with retry logic.
        
        Args:
            pool_id: DeFi Llama pool identifier
            retry_count: Current retry attempt
            
        Returns:
            DataFrame with historical metrics or None if error
        """
        try:
            response = self.session.get(
                f"{self.yields_url}/chart/{pool_id}",
                timeout=30
            )
            
            # Handle rate limiting with exponential backoff
            if response.status_code == 429:
                if retry_count < self.max_retries:
                    wait_time = self.base_delay * (2 ** retry_count)  # Exponential backoff
                    print(f"  ⚠ Rate limited. Waiting {wait_time:.1f}s before retry {retry_count + 1}/{self.max_retries}")
                    time.sleep(wait_time)
                    return self.get_pool_historical_data(pool_id, retry_count + 1)
                else:
                    print(f"  ✗ Max retries exceeded for {pool_id}")
                    return None
            
            response.raise_for_status()
            
            data = response.json()
            
            # Extract data array
            if isinstance(data, dict) and 'data' in data:
                historical = data['data']
            else:
                historical = data
            
            if not historical:
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(historical)
            
            # Parse dates
            if 'timestamp' in df.columns:
                df['date'] = pd.to_datetime(df['timestamp'])
            elif 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            
            return df
            
        except requests.exceptions.RequestException as e:
            if retry_count < self.max_retries:
                wait_time = self.base_delay * (2 ** retry_count)
                print(f"  ⚠ Error, retrying in {wait_time:.1f}s: {e}")
                time.sleep(wait_time)
                return self.get_pool_historical_data(pool_id, retry_count + 1)
            else:
                print(f"  ✗ Error fetching history for {pool_id}: {e}")
                return None
        except Exception as e:
            print(f"  ✗ Error parsing history for {pool_id}: {e}")
            return None


class DataCollector:
    """Main data collection and storage coordinator"""
    
    def __init__(self):
        self.client = DeFiLlamaClient()
        self.session = get_session()
    
    def filter_pools(self, pools: List[Dict]) -> pd.DataFrame:
        """
        Filter pools based on quality criteria.
        
        Args:
            pools: List of pool dictionaries from API
            
        Returns:
            Filtered DataFrame of pools
        """
        df = pd.DataFrame(pools)
        
        print(f"\nFiltering pools...")
        print(f"  Starting with: {len(df)} pools")
        
        # Apply filters
        filtered = df[
            (df['tvlUsd'] > MIN_TVL_USD) &
            (df['apy'] > MIN_APY) &
            (df['apy'] < MAX_APY) &
            (df['apy'].notna()) &
            (df['pool'].notna()) &
            (df['project'].notna())
        ].copy()
        
        print(f"  After TVL/APY filters: {len(filtered)} pools")
        
        # Take top N by TVL
        top_pools = filtered.nlargest(TOP_POOLS_LIMIT, 'tvlUsd')
        print(f"  Selected top {len(top_pools)} pools by TVL")
        
        return top_pools
    
    def store_pools(self, pools_df: pd.DataFrame) -> Dict[str, int]:
        """
        Store pool metadata in database.
        
        Args:
            pools_df: DataFrame of pools to store
            
        Returns:
            Dictionary with counts of inserted/updated/skipped pools
        """
        from datetime import timezone
        
        counts = {'inserted': 0, 'updated': 0, 'skipped': 0}
        
        print(f"\nStoring {len(pools_df)} pools in database...")
        
        for idx, row in pools_df.iterrows():
            try:
                # Check if pool exists
                existing_pool = self.session.query(Pool).filter_by(
                    pool_id=row['pool']
                ).first()
                
                if existing_pool:
                    # Update existing pool
                    existing_pool.symbol = row['symbol']
                    existing_pool.chain = row['chain']
                    existing_pool.project = row['project']
                    existing_pool.last_updated = datetime.now(timezone.utc).replace(tzinfo=None)
                    counts['updated'] += 1
                else:
                    # Insert new pool
                    pool = Pool(
                        pool_id=row['pool'],
                        symbol=row['symbol'],
                        chain=row['chain'],
                        project=row['project']
                    )
                    self.session.add(pool)
                    counts['inserted'] += 1
                
                # Commit every 50 pools
                if (counts['inserted'] + counts['updated']) % 50 == 0:
                    self.session.commit()
                    print(f"  Progress: {counts['inserted']} inserted, {counts['updated']} updated")
                    
            except Exception as e:
                self.session.rollback()
                print(f"  ✗ Error storing pool {row['pool']}: {e}")
                counts['skipped'] += 1
        
        # Final commit
        self.session.commit()
        
        print(f"\n✓ Pool storage complete:")
        print(f"  Inserted: {counts['inserted']}")
        print(f"  Updated: {counts['updated']}")
        print(f"  Skipped: {counts['skipped']}")
        
        return counts
    
    def store_historical_metrics(self, pool_id: str, df_history: pd.DataFrame) -> int:
        """
        Store historical metrics for a pool.
        
        Args:
            pool_id: DeFi Llama pool identifier
            df_history: DataFrame with historical data
            
        Returns:
            Number of metrics stored
        """
        from datetime import timezone
        
        # Get pool database ID
        pool = self.session.query(Pool).filter_by(pool_id=pool_id).first()
        if not pool:
            print(f"  ✗ Pool {pool_id} not found in database")
            return 0
        
        stored_count = 0
        
        # Limit to recent history to keep DB size manageable
        # Use timezone-aware datetime to match API data
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=DAYS_OF_HISTORY)
        
        # Ensure df_history dates are timezone-aware
        if df_history['date'].dt.tz is None:
            # If naive, localize to UTC
            df_history['date'] = df_history['date'].dt.tz_localize('UTC')
        
        df_recent = df_history[df_history['date'] >= cutoff_date].copy()
        
        for _, row in df_recent.iterrows():
            try:
                # Convert to naive datetime for storage (SQLite doesn't handle tz well)
                date_value = row['date']
                if hasattr(date_value, 'tz_localize'):
                    # It's a pandas Timestamp
                    date_naive = date_value.replace(tzinfo=None)
                elif hasattr(date_value, 'replace'):
                    # It's a datetime object
                    date_naive = date_value.replace(tzinfo=None)
                else:
                    date_naive = date_value
                
                # Check if metric already exists
                existing = self.session.query(PoolMetric).filter_by(
                    pool_id=pool.id,
                    date=date_naive
                ).first()
                
                if existing:
                    # Update existing metric
                    existing.apy = row.get('apy')
                    existing.apy_base = row.get('apyBase')
                    existing.apy_reward = row.get('apyReward')
                    existing.tvl_usd = row.get('tvlUsd')
                    existing.il7d = row.get('il7d')
                else:
                    # Insert new metric
                    metric = PoolMetric(
                        pool_id=pool.id,
                        date=date_naive,
                        apy=row.get('apy'),
                        apy_base=row.get('apyBase'),
                        apy_reward=row.get('apyReward'),
                        tvl_usd=row.get('tvlUsd'),
                        il7d=row.get('il7d')
                    )
                    self.session.add(metric)
                
                stored_count += 1
                
            except IntegrityError:
                self.session.rollback()
                continue
            except Exception as e:
                self.session.rollback()
                print(f"    ✗ Error storing metric: {e}")
                continue
        
        self.session.commit()
        return stored_count
    
    def collect_historical_data(self, limit: Optional[int] = None, resume: bool = True):
        """
        Fetch and store historical data for all pools in database.
        
        Args:
            limit: Optional limit on number of pools to process
            resume: If True, skip pools that already have recent metrics
        """
        from datetime import timezone
        
        pools = self.session.query(Pool).all()
        
        if limit:
            pools = pools[:limit]
        
        # Filter out pools that already have recent data if resuming
        if resume:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
            pools_to_process = []
            
            for pool in pools:
                # Check if pool has metrics from the last week
                recent_metric = self.session.query(PoolMetric).filter(
                    PoolMetric.pool_id == pool.id,
                    PoolMetric.date >= cutoff_date
                ).first()
                
                if not recent_metric:
                    pools_to_process.append(pool)
            
            if len(pools_to_process) < len(pools):
                print(f"ℹ Resume mode: Skipping {len(pools) - len(pools_to_process)} pools with recent data")
            
            pools = pools_to_process
        
        print(f"\n{'='*60}")
        print(f"Collecting historical data for {len(pools)} pools...")
        print(f"{'='*60}")
        
        total_metrics = 0
        successful = 0
        failed = 0
        
        for i, pool in enumerate(pools, 1):
            print(f"\n[{i}/{len(pools)}] {pool.project} - {pool.symbol} ({pool.chain})")
            
            # Fetch historical data
            df_history = self.client.get_pool_historical_data(pool.pool_id)
            
            if df_history is None or len(df_history) == 0:
                print(f"  ✗ No historical data available")
                failed += 1
                continue
            
            print(f"  ✓ Fetched {len(df_history)} days of history")
            
            # Store metrics
            count = self.store_historical_metrics(pool.pool_id, df_history)
            total_metrics += count
            
            if count > 0:
                print(f"  ✓ Stored {count} metrics")
                successful += 1
            else:
                failed += 1
            
            # Rate limiting - be nice to the API (increased delay)
            time.sleep(1.0)  # Increased from 0.5s
            
            # Save progress every 10 pools
            if i % 10 == 0:
                print(f"\n  💾 Progress checkpoint: {i}/{len(pools)} pools processed")
        
        print(f"\n{'='*60}")
        print(f"Historical data collection complete!")
        print(f"  Successful: {successful}/{len(pools)}")
        print(f"  Failed: {failed}/{len(pools)}")
        print(f"  Total metrics stored: {total_metrics}")
        print(f"{'='*60}")
    
    def run_full_collection(self):
        """Run complete data collection pipeline"""
        print("="*60)
        print("STARTING FULL DATA COLLECTION")
        print("="*60)
        
        # Step 1: Fetch all pools
        all_pools = self.client.get_all_pools()
        if not all_pools:
            print("✗ Failed to fetch pools. Exiting.")
            return
        
        # Step 2: Filter pools
        filtered_pools = self.filter_pools(all_pools)
        
        # Step 3: Store pool metadata
        self.store_pools(filtered_pools)
        
        # Step 4: Collect historical data
        self.collect_historical_data()
        
        print("\n" + "="*60)
        print("DATA COLLECTION COMPLETE!")
        print("="*60)


if __name__ == "__main__":
    # Run data collection when executed directly
    collector = DataCollector()
    collector.run_full_collection()