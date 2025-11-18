"""
DeFi Yield Risk Analyzer - Streamlit Dashboard
Main entry point for the dashboard application.
"""

import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Page configuration
st.set_page_config(
    page_title="DeFi Yield Risk Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding-top: 2rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    h1 {
        color: #1f77b4;
    }
    .risk-low {
        color: #2ecc71;
        font-weight: bold;
    }
    .risk-medium {
        color: #f39c12;
        font-weight: bold;
    }
    .risk-high {
        color: #e74c3c;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("📊 DeFi Yield Risk Analyzer")
    st.markdown("---")
    
    # Navigation
    page = st.radio(
        "Navigation",
        ["🏠 Overview", "🔍 Pool Explorer", "📊 Risk Analysis", "📈 Historical Trends"]
    )
    
    st.markdown("---")
    st.markdown("""
    **About:**
    Real-time DeFi yield opportunities with quantitative risk assessment.
    
    Data source: [DeFi Llama](https://defillama.com)
    """)


# Import page modules
from views import overview, pool_explorer, risk_analysis, historical_trends, methodology

# Route to appropriate page
if page == "🏠 Overview":
    overview.show()
elif page == "🔍 Pool Explorer":
    pool_explorer.show()
elif page == "📊 Risk Analysis":
    risk_analysis.show()
elif page == "📈 Historical Trends":
    historical_trends.show()
elif page == "📖 Methodology":
    methodology.show()