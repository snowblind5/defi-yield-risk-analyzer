"""
Pool Explorer page - Filter and search pools
"""

import streamlit as st
import pandas as pd
import plotly.express as px

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.database import get_session, Pool, PoolRiskScore
from src.risk_calculator import RiskCalculator


def load_data():
    """Load pool data with risk scores"""
    calculator = RiskCalculator()
    return calculator.get_risk_summary()


def show():
    """Render pool explorer page"""
    st.title("🔍 Pool Explorer")
    st.markdown("Filter and explore DeFi yield pools with detailed metrics")
    
    # Load data
    with st.spinner("Loading pools..."):
        df = load_data()
    
    if len(df) == 0:
        st.error("No data available. Please run data collection first.")
        return
    
    # Sidebar filters
    st.sidebar.markdown("### 🎛️ Filters")
    
    # Chain filter
    chains = ['All'] + sorted(df['chain'].unique().tolist())
    selected_chain = st.sidebar.selectbox("Chain", chains)
    
    # Protocol filter
    protocols = ['All'] + sorted(df['project'].unique().tolist())
    selected_protocol = st.sidebar.selectbox("Protocol", protocols)
    
    # Risk level filter
    risk_levels = st.sidebar.multiselect(
        "Risk Level",
        ['Low', 'Medium', 'High'],
        default=['Low', 'Medium', 'High']
    )
    
    # APY range
    min_apy, max_apy = float(df['apy_30d'].min()), float(df['apy_30d'].max())
    apy_range = st.sidebar.slider(
        "APY Range (%)",
        min_value=min_apy,
        max_value=max_apy,
        value=(min_apy, max_apy),
        step=0.5
    )
    
    # TVL range (log scale)
    min_tvl_log = 4  # $10k
    max_tvl_log = 10  # $10B
    tvl_range_log = st.sidebar.slider(
        "TVL Range",
        min_value=min_tvl_log,
        max_value=max_tvl_log,
        value=(min_tvl_log, max_tvl_log),
        format="$%.0fM",
        help="Logarithmic scale: 4=$10k, 5=$100k, 6=$1M, 7=$10M, 8=$100M, 9=$1B"
    )
    
    # Risk score range
    risk_range = st.sidebar.slider(
        "Risk Score",
        min_value=0,
        max_value=100,
        value=(0, 100),
        help="Lower score = Lower risk"
    )
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_chain != 'All':
        filtered_df = filtered_df[filtered_df['chain'] == selected_chain]
    
    if selected_protocol != 'All':
        filtered_df = filtered_df[filtered_df['project'] == selected_protocol]
    
    filtered_df = filtered_df[filtered_df['risk_level'].isin(risk_levels)]
    filtered_df = filtered_df[
        (filtered_df['apy_30d'] >= apy_range[0]) &
        (filtered_df['apy_30d'] <= apy_range[1])
    ]
    filtered_df = filtered_df[
        (filtered_df['tvl_30d'] >= 10**tvl_range_log[0]) &
        (filtered_df['tvl_30d'] <= 10**tvl_range_log[1])
    ]
    filtered_df = filtered_df[
        (filtered_df['risk_score'] >= risk_range[0]) &
        (filtered_df['risk_score'] <= risk_range[1])
    ]
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Pools Found", len(filtered_df))
    
    with col2:
        if len(filtered_df) > 0:
            avg_apy = filtered_df['apy_30d'].mean()
            st.metric("Avg APY", f"{avg_apy:.2f}%")
        else:
            st.metric("Avg APY", "N/A")
    
    with col3:
        if len(filtered_df) > 0:
            avg_risk = filtered_df['risk_score'].mean()
            st.metric("Avg Risk Score", f"{avg_risk:.1f}")
        else:
            st.metric("Avg Risk Score", "N/A")
    
    with col4:
        if len(filtered_df) > 0:
            total_tvl = filtered_df['tvl_30d'].sum()
            st.metric("Total TVL", f"${total_tvl/1e9:.2f}B")
        else:
            st.metric("Total TVL", "N/A")
    
    st.markdown("---")
    
    if len(filtered_df) == 0:
        st.warning("No pools match the selected filters. Try adjusting the criteria.")
        return
    
    # Sorting options
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader(f"📋 Pool List ({len(filtered_df)} pools)")
    
    with col2:
        sort_by = st.selectbox(
            "Sort by",
            ['APY (High to Low)', 'APY (Low to High)', 
             'Risk (Low to High)', 'Risk (High to Low)',
             'TVL (High to Low)', 'TVL (Low to High)']
        )
    
    # Apply sorting
    if sort_by == 'APY (High to Low)':
        filtered_df = filtered_df.sort_values('apy_30d', ascending=False)
    elif sort_by == 'APY (Low to High)':
        filtered_df = filtered_df.sort_values('apy_30d', ascending=True)
    elif sort_by == 'Risk (Low to High)':
        filtered_df = filtered_df.sort_values('risk_score', ascending=True)
    elif sort_by == 'Risk (High to Low)':
        filtered_df = filtered_df.sort_values('risk_score', ascending=False)
    elif sort_by == 'TVL (High to Low)':
        filtered_df = filtered_df.sort_values('tvl_30d', ascending=False)
    elif sort_by == 'TVL (Low to High)':
        filtered_df = filtered_df.sort_values('tvl_30d', ascending=True)
    
    # Prepare display dataframe
    display_df = filtered_df.copy()
    display_df['apy_display'] = display_df['apy_30d'].apply(lambda x: f"{x:.2f}%")
    display_df['tvl_display'] = display_df['tvl_30d'].apply(
        lambda x: f"${x/1e6:.1f}M" if x < 1e9 else f"${x/1e9:.2f}B"
    )
    display_df['risk_display'] = display_df['risk_score'].apply(lambda x: f"{x:.1f}")
    
    # Color-code risk levels
    def risk_color(risk_level):
        colors = {'Low': '🟢', 'Medium': '🟡', 'High': '🔴'}
        return colors.get(risk_level, '')
    
    display_df['risk_indicator'] = display_df['risk_level'].apply(risk_color)
    
    # Select columns for display
    table_df = display_df[[
        'project', 'symbol', 'chain', 
        'apy_display', 'tvl_display', 
        'risk_display', 'risk_indicator', 'risk_level'
    ]].copy()
    
    table_df.columns = [
        'Project', 'Symbol', 'Chain', 
        'APY', 'TVL', 
        'Risk Score', '', 'Risk Level'
    ]
    
    # Display table with formatting
    st.dataframe(
        table_df,
        hide_index=True,
        use_container_width=True,
        height=600
    )
    
    # Export option
    st.markdown("---")
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        st.caption(f"Showing {len(filtered_df)} of {len(df)} total pools")
    
    with col2:
        # CSV export
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Export CSV",
            data=csv,
            file_name="defi_pools_export.csv",
            mime="text/csv"
        )