"""
Overview page - Market summary and top opportunities
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.database import get_session, Pool, PoolRiskScore, PoolMetric
from src.risk_calculator import RiskCalculator


def load_data():
    """Load summary data"""
    calculator = RiskCalculator()
    return calculator.get_risk_summary()


def show():
    """Render overview page"""
    st.title("🏠 DeFi Yield Market Overview")
    
    # Load data
    with st.spinner("Loading data..."):
        df = load_data()
    
    if len(df) == 0:
        st.error("No data available. Please run data collection first.")
        return
    
    # Key metrics at the top
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Pools",
            value=f"{len(df):,}",
            delta=None
        )
    
    with col2:
        avg_apy = df['apy_30d'].mean()
        st.metric(
            label="Average APY",
            value=f"{avg_apy:.2f}%",
            delta=None
        )
    
    with col3:
        total_tvl = df['tvl_30d'].sum()
        st.metric(
            label="Total TVL",
            value=f"${total_tvl/1e9:.2f}B",
            delta=None
        )
    
    with col4:
        low_risk_count = len(df[df['risk_level'] == 'Low'])
        st.metric(
            label="Low Risk Pools",
            value=f"{low_risk_count}",
            delta=None
        )
    
    st.markdown("---")
    
    # Two columns for visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Risk Distribution")
        
        # Risk level pie chart
        risk_counts = df['risk_level'].value_counts()
        fig = px.pie(
            values=risk_counts.values,
            names=risk_counts.index,
            color=risk_counts.index,
            color_discrete_map={'Low': '#2ecc71', 'Medium': '#f39c12', 'High': '#e74c3c'},
            hole=0.4
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🔗 Top Chains by Pool Count")
        
        # Chain distribution
        chain_counts = df['chain'].value_counts().head(10)
        fig = px.bar(
            x=chain_counts.values,
            y=chain_counts.index,
            orientation='h',
            color=chain_counts.values,
            color_continuous_scale='Blues'
        )
        fig.update_layout(
            showlegend=False,
            xaxis_title="Number of Pools",
            yaxis_title="",
            height=300,
            coloraxis_showscale=False
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Risk vs Return scatter plot
    st.subheader("⚖️ Risk vs Return Analysis")
    
    fig = px.scatter(
        df,
        x='risk_score',
        y='apy_30d',
        size='tvl_30d',
        color='risk_level',
        hover_data=['project', 'symbol', 'chain'],
        color_discrete_map={'Low': '#2ecc71', 'Medium': '#f39c12', 'High': '#e74c3c'},
        labels={
            'risk_score': 'Risk Score (Lower = Safer)',
            'apy_30d': 'APY (%)',
            'tvl_30d': 'TVL (USD)'
        }
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Top opportunities
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💎 Best Risk-Adjusted Returns")
        st.caption("High APY, Low Risk")
        
        # Calculate risk-adjusted return (APY / Risk Score)
        df['risk_adjusted_return'] = df['apy_30d'] / (df['risk_score'] + 1)
        top_adjusted = df.nlargest(10, 'risk_adjusted_return')[
            ['project', 'symbol', 'chain', 'apy_30d', 'risk_score', 'risk_level']
        ].copy()
        
        # Format for display
        top_adjusted['apy_30d'] = top_adjusted['apy_30d'].apply(lambda x: f"{x:.2f}%")
        top_adjusted['risk_score'] = top_adjusted['risk_score'].apply(lambda x: f"{x:.1f}")
        top_adjusted.columns = ['Project', 'Symbol', 'Chain', 'APY', 'Risk', 'Risk Level']
        
        st.dataframe(
            top_adjusted,
            hide_index=True,
            use_container_width=True
        )
    
    with col2:
        st.subheader("🔒 Safest High-TVL Pools")
        st.caption("Low Risk, High Liquidity")
        
        # Safest pools with TVL > $10M
        safe_liquid = df[df['tvl_30d'] > 10_000_000].nsmallest(10, 'risk_score')[
            ['project', 'symbol', 'chain', 'apy_30d', 'tvl_30d', 'risk_level']
        ].copy()
        
        # Format for display
        safe_liquid['apy_30d'] = safe_liquid['apy_30d'].apply(lambda x: f"{x:.2f}%")
        safe_liquid['tvl_30d'] = safe_liquid['tvl_30d'].apply(lambda x: f"${x/1e6:.1f}M")
        safe_liquid.columns = ['Project', 'Symbol', 'Chain', 'APY', 'TVL', 'Risk Level']
        
        st.dataframe(
            safe_liquid,
            hide_index=True,
            use_container_width=True
        )
    
    # Footer
    st.markdown("---")
    session = get_session()
    last_update = session.query(PoolMetric).order_by(PoolMetric.date.desc()).first()
    if last_update:
        st.caption(f"Last updated: {last_update.date.strftime('%Y-%m-%d %H:%M UTC')}")