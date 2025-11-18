# 📊 DeFi Yield Risk Analyzer

A comprehensive data pipeline and interactive dashboard for analyzing DeFi yield farming opportunities with quantitative risk assessment.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🎯 Overview

This project provides institutional-grade risk analysis for DeFi yield farming by:
- Tracking 500+ top yield pools across multiple blockchains
- Calculating quantitative risk scores based on volatility and liquidity
- Providing interactive visualizations for opportunity discovery
- Automating weekly data updates via GitHub Actions

**Built for the Dialectic internship application** to demonstrate full-stack data engineering, quantitative analysis, and production deployment skills.

## ✨ Features

### 📊 Data Pipeline
- **Automated Collection**: Fetches data from DeFi Llama API
- **Historical Analysis**: 90 days of APY and TVL metrics
- **Smart Filtering**: Focuses on liquid, established pools (TVL > $100k)
- **Incremental Updates**: Resume capability for interrupted collections

### 🎲 Risk Scoring Engine
- **APY Volatility**: Standard deviation over 30-day rolling window
- **TVL Stability**: Coefficient of variation for liquidity assessment
- **Liquidity Score**: Logarithmic scale based on pool depth
- **Composite Risk**: Weighted score (0-100, lower = safer)

### 🖥️ Interactive Dashboard
- **Overview**: Market summary with key metrics and visualizations
- **Pool Explorer**: Filter 500+ pools by chain, protocol, risk, APY, TVL
- **Risk Analysis**: Deep dive into risk components and protocol comparison
- **Historical Trends**: Time series charts for individual pools

### 🔄 CI/CD Pipeline
- **GitHub Actions**: Automated weekly data refresh
- **Version Control**: Database committed to repository
- **Auto-Deploy**: Streamlit Cloud updates on push

## 🏗️ Architecture
```
┌─────────────────┐
│  DeFi Llama API │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  Data Collector     │
│  - Rate limiting    │
│  - Retry logic      │
│  - Resume support   │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  SQLite Database    │
│  - Pools (500)      │
│  - Metrics (45k+)   │
│  - Risk Scores      │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Risk Calculator    │
│  - Volatility       │
│  - Liquidity        │
│  - Composite score  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Streamlit Dashboard │
│  - 4 pages          │
│  - Interactive viz  │
│  - Filters & export │
└─────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Git
- Virtual environment (recommended)

### Installation
```bash
# Clone repository
git clone https://github.com/yourusername/defi-yield-risk-analyzer.git
cd defi-yield-risk-analyzer

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Initialize Database (First Time Only)
```bash
# Run full initialization (~15-20 minutes)
python scripts/initialize_db.py

# Or run steps individually:
python -m src.database              # Create tables
python -m src.data_collector        # Collect data
python -m src.risk_calculator       # Calculate risks
```

### Run Dashboard
```bash
streamlit run dashboard/app.py
```

Navigate to `http://localhost:8501`

### Update Data
```bash
# Incremental update (runs weekly via GitHub Actions)
python scripts/update_data.py
```

## 📊 Risk Methodology

### Composite Risk Score Formula
```
Risk Score = 0.4 × Liquidity Risk + 0.6 × Stability Risk
```

Where:
- **Liquidity Risk** = 100 - Liquidity Score
- **Stability Risk** = 100 - Stability Score

### Component Calculations

#### 1. Liquidity Score (0-100)
```python
log_tvl = log10(max(TVL, $10k))
score = (log_tvl - 4) / (9 - 4) × 100
```
- $100k TVL ≈ 30 score
- $1M TVL ≈ 50 score
- $100M TVL ≈ 90 score

#### 2. Stability Score (0-100)
```python
apy_component = max(0, 100 - APY_std × 2)
tvl_component = max(0, 100 - TVL_cv)
stability = apy_component × 0.6 + tvl_component × 0.4
```

#### 3. Risk Levels
- **Low**: 0-30 (Stable, liquid pools)
- **Medium**: 30-60 (Moderate risk/reward)
- **High**: 60-100 (Volatile or illiquid)

### Validation
Risk scores validated against:
- Historical DeFi incidents
- Professional fund methodologies
- Academic research on yield farming

## 📁 Project Structure
```
defi-yield-risk-analyzer/
├── .github/
│   └── workflows/
│       └── update_data.yml      # GitHub Actions CI/CD
├── dashboard/
│   ├── app.py                   # Main dashboard entry
│   └── views/                   # Dashboard pages
│       ├── overview.py
│       ├── pool_explorer.py
│       ├── risk_analysis.py
│       └── historical_trends.py
├── src/
│   ├── __init__.py
│   ├── config.py                # Configuration
│   ├── database.py              # SQLAlchemy models
│   ├── data_collector.py        # API client & ETL
│   └── risk_calculator.py       # Risk metrics engine
├── scripts/
│   ├── initialize_db.py         # One-time setup
│   ├── update_data.py           # Incremental updates
│   └── verify_data.py           # Data validation
├── .gitignore
├── requirements.txt
├── TODO.md
├── README.md
└── defi_yields.db               # SQLite database (committed)
```

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Data Source | DeFi Llama API | Pool metrics & historical data |
| Database | SQLite + SQLAlchemy | Persistent storage |
| Analytics | Pandas, NumPy | Data processing & calculations |
| Visualization | Plotly, Streamlit | Interactive dashboard |
| CI/CD | GitHub Actions | Automated updates |
| Deployment | Streamlit Cloud | Hosting |

## 🔄 Automated Updates

### GitHub Actions Workflow

Runs every **Sunday at midnight UTC**:

1. Fetch latest pool data
2. Update historical metrics (last 7 days)
3. Recalculate risk scores
4. Commit updated database
5. Trigger Streamlit redeploy

**Manual trigger**: Actions tab → "Update DeFi Data" → Run workflow

### Rate Limiting Strategy
- 1 second delay between requests
- Exponential backoff on 429 errors (1s → 2s → 4s)
- Retry up to 3 times
- Resume capability for interrupted collections

## 📈 Usage Examples

### Find Low-Risk Stablecoin Yields
```python
from src.risk_calculator import RiskCalculator

calc = RiskCalculator()
summary = calc.get_risk_summary()

safe_stables = summary[
    (summary['risk_score'] < 30) &
    (summary['symbol'].str.contains('USD'))
].nlargest(10, 'apy_30d')

print(safe_stables[['project', 'symbol', 'apy_30d', 'risk_score']])
```

### Export Pool Data
```python
from src.database import get_session, Pool, PoolRiskScore

session = get_session()
pools = session.query(Pool, PoolRiskScore).join(PoolRiskScore).all()

# Process as needed...
```

## 🧪 Testing
```bash
# Verify data integrity
python scripts/verify_data.py

# Check database
python -m src.database

# Test data collection (small sample)
python -c "
from src.data_collector import DataCollector
collector = DataCollector()
collector.collect_historical_data(limit=5)
"
```

## 🚢 Deployment

### Deploy to Streamlit Cloud

1. **Push to GitHub**
```bash
git add .
git commit -m "Initial commit"
git push origin main
```

2. **Connect to Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Select repository: `yourusername/defi-yield-risk-analyzer`
   - Main file path: `dashboard/app.py`
   - Click "Deploy"

3. **Configure Settings** (if needed)
   - Python version: 3.10
   - No secrets needed (public API)

4. **Monitor Logs**
   - Check deployment logs for errors
   - Database loads from committed `defi_yields.db`

### Local Production Testing
```bash
# Test with production-like settings
streamlit run dashboard/app.py --server.port 8501 --server.headless true
```

## 📝 Configuration

Edit `src/config.py` to adjust:
- Pool filtering criteria (TVL, APY thresholds)
- Historical data range (default: 90 days)
- Risk score weights
- Update schedule

## 🤝 Contributing

This is a portfolio project, but suggestions are welcome:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📋 TODO

See [TODO.md](TODO.md) for planned enhancements:
- [ ] Impermanent loss calculations
- [ ] Protocol-specific risk factors
- [ ] Portfolio simulation tool
- [ ] Email/Telegram alerts
- [ ] Historical strategy backtesting

## 🐛 Known Limitations

- **Data Freshness**: Weekly updates (suitable for strategic analysis, not day-trading)
- **Risk Model**: Does not include smart contract audit status (not in API)
- **Database Size**: Limited to 90 days to stay under GitHub 100MB limit
- **API Limits**: DeFi Llama rate limits require slow collection (~15 min for 500 pools)

## 📚 References

- [DeFi Llama API Documentation](https://defillama.com/docs/api)
- [Streamlit Documentation](https://docs.streamlit.io)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org)

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details

## 👤 Author

- GitHub: [@snowblind5](https://github.com/snowblind5)