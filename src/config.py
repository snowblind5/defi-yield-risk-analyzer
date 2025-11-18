"""
Configuration settings for the DeFi Yield Risk Analyzer.
"""

# API Configuration
DEFILLAMA_BASE_URL = "https://api.llama.fi"
DEFILLAMA_YIELDS_URL = "https://yields.llama.fi"

# Database Configuration
DATABASE_PATH = "defi_yields.db"

# Data Collection Settings
MIN_TVL_USD = 100_000  # Minimum TVL to consider a pool
MIN_APY = 0.5  # Minimum APY to consider
MAX_APY = 200  # Maximum APY (filter outliers/scams)
TOP_POOLS_LIMIT = 500  # Number of top pools to track initially

# Historical Data Settings
DAYS_OF_HISTORY = 90  # How many days of historical data to fetch

# Risk Scoring Weights
RISK_WEIGHTS = {
    'apy_volatility': 0.3,      # 30% weight
    'tvl_volatility': 0.3,      # 30% weight
    'liquidity': 0.4,           # 40% weight
}

# Risk Score Thresholds (0-100 scale, lower is safer)
RISK_LEVELS = {
    'low': (0, 30),
    'medium': (30, 60),
    'high': (60, 100)
}

# Update frequency for GitHub Actions
UPDATE_SCHEDULE = "0 0 * * 0"  # Cron: Every Sunday at midnight UTC