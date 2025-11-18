"""
Database models and utilities for the DeFi Yield Risk Analyzer.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import os

from src.config import DATABASE_PATH

Base = declarative_base()


class Protocol(Base):
    """Protocol/Project information (e.g., Aave, Uniswap)"""
    __tablename__ = 'protocols'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    slug = Column(String, unique=True)
    category = Column(String)
    chain = Column(String)
    created_date = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    pools = relationship("Pool", back_populates="protocol")
    
    def __repr__(self):
        return f"<Protocol(name='{self.name}', category='{self.category}')>"


class Pool(Base):
    """Individual yield pool (e.g., Aave USDC lending)"""
    __tablename__ = 'pools'
    
    id = Column(Integer, primary_key=True)
    pool_id = Column(String, unique=True, nullable=False, index=True)
    protocol_id = Column(Integer, ForeignKey('protocols.id'), nullable=True)
    symbol = Column(String)
    chain = Column(String)
    project = Column(String)  # Protocol name from DeFi Llama
    created_date = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    protocol = relationship("Protocol", back_populates="pools")
    metrics = relationship("PoolMetric", back_populates="pool", cascade="all, delete-orphan")
    risk_scores = relationship("PoolRiskScore", back_populates="pool", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Pool(project='{self.project}', symbol='{self.symbol}', chain='{self.chain}')>"


class PoolMetric(Base):
    """Daily metrics for each pool"""
    __tablename__ = 'pool_metrics_daily'
    
    id = Column(Integer, primary_key=True)
    pool_id = Column(Integer, ForeignKey('pools.id'), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    apy = Column(Float)
    apy_base = Column(Float)
    apy_reward = Column(Float)
    tvl_usd = Column(Float)
    il7d = Column(Float)  # 7-day impermanent loss (if available)
    
    # Relationships
    pool = relationship("Pool", back_populates="metrics")
    
    # Ensure unique constraint on pool_id + date
    __table_args__ = (UniqueConstraint('pool_id', 'date', name='_pool_date_uc'),)
    
    def __repr__(self):
        return f"<PoolMetric(pool_id={self.pool_id}, date={self.date}, apy={self.apy})>"


class PoolRiskScore(Base):
    """Calculated risk scores for each pool"""
    __tablename__ = 'pool_risk_scores'
    
    id = Column(Integer, primary_key=True)
    pool_id = Column(Integer, ForeignKey('pools.id'), nullable=False, index=True)
    calculation_date = Column(DateTime, default=datetime.utcnow)
    
    # Risk metrics (calculated from historical data)
    apy_volatility_30d = Column(Float)  # Standard deviation of APY
    tvl_volatility_30d = Column(Float)  # Coefficient of variation of TVL
    apy_mean_30d = Column(Float)        # Mean APY over 30 days
    tvl_mean_30d = Column(Float)        # Mean TVL over 30 days
    
    # Scores (0-100 scale)
    liquidity_score = Column(Float)     # Based on TVL magnitude
    stability_score = Column(Float)     # Based on APY/TVL volatility
    composite_risk_score = Column(Float)  # Weighted composite (lower = safer)
    
    # Relationships
    pool = relationship("Pool", back_populates="risk_scores")
    
    def __repr__(self):
        return f"<PoolRiskScore(pool_id={self.pool_id}, risk={self.composite_risk_score})>"


# Database connection utilities
def get_engine(echo=False):
    """Create and return SQLAlchemy engine"""
    return create_engine(f'sqlite:///{DATABASE_PATH}', echo=echo)


def get_session():
    """Create and return a new database session"""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_database():
    """Initialize database and create all tables"""
    db_exists = os.path.exists(DATABASE_PATH)
    
    if db_exists:
        print(f"ℹ Database already exists: {DATABASE_PATH}")
    else:
        print(f"Creating new database: {DATABASE_PATH}")
    
    engine = get_engine()
    Base.metadata.create_all(engine)
    
    print(f"✓ Database ready: {DATABASE_PATH}")
    print(f"✓ Tables: {', '.join(Base.metadata.tables.keys())}")
    
    # Show table counts
    session = get_session()
    print(f"\nCurrent record counts:")
    print(f"  Protocols: {session.query(Protocol).count()}")
    print(f"  Pools: {session.query(Pool).count()}")
    print(f"  Metrics: {session.query(PoolMetric).count()}")
    print(f"  Risk Scores: {session.query(PoolRiskScore).count()}")
    session.close()


def drop_all_tables():
    """Drop all tables (use with caution!)"""
    engine = get_engine()
    Base.metadata.drop_all(engine)
    print("⚠ All tables dropped")


if __name__ == "__main__":
    # Initialize database when run directly
    init_database()