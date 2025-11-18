"""
Risk Analysis page - Deep dive into risk metrics
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.database import get_session, Pool, PoolRiskScore
from src.risk_calculator import RiskCalculator


def load_detailed_data():
    """Load detailed risk data"""
    session = get_session()
    
    results = session.query(
        Pool.project,
        Pool.symbol,
        Pool.chain,
        PoolRiskScore.apy_mean_30d,
        PoolRiskScore.apy_volatility_30d,
        PoolRiskScore.tvl_mean_30d,
        PoolRiskScore.tvl_volatility_30d,
        PoolRiskScore.liquidity_score,
        PoolRiskScore.stability_score,
        PoolRiskScore.composite_risk_score
    ).join(
        PoolRiskScore, Pool.id == PoolRiskScore.pool_id
    ).all()
    
    df = pd.DataFrame(results, columns=[
        'project', 'symbol', 'chain',
        'apy_mean', 'apy_volatility', 'tvl_mean', 'tvl_volatility',
        'liquidity_score', 'stability_score', 'risk_score'
    ])
    
    # Add risk level
    def classify_risk(score):
        if score <= 30:
            return 'Low'
        elif score <= 60:
            return 'Medium'
        else:
            return 'High'
    
    df['risk_level'] = df['risk_score'].apply(classify_risk)
    
    return df


def show():
    """Render risk analysis page"""
    st.title("📊 Risk Analysis")
    st.markdown("Detailed breakdown of risk components and protocol comparison")
    
    # Load data
    with st.spinner("Loading risk metrics..."):
        df = load_detailed_data()
    
    if len(df) == 0:
        st.error("No risk data available. Please run risk calculations first.")
        return
    
    # Tab layout
    tab1, tab2, tab3 = st.tabs(["📉 Risk Breakdown", "🔬 Protocol Comparison", "🎯 Risk Factors"])
    
    with tab1:
        st.subheader("Risk Score Components")
        st.markdown("Understanding what drives the composite risk score")
        
        # Component correlation heatmap
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Scatter: Liquidity vs Stability
            fig = px.scatter(
                df,
                x='stability_score',
                y='liquidity_score',
                size='tvl_mean',
                color='risk_level',
                hover_data=['project', 'symbol', 'risk_score'],
                color_discrete_map={'Low': '#2ecc71', 'Medium': '#f39c12', 'High': '#e74c3c'},
                labels={
                    'stability_score': 'Stability Score',
                    'liquidity_score': 'Liquidity Score'
                },
                title="Liquidity vs Stability Analysis"
            )
            fig.add_shape(
                type='line',
                x0=0, y0=0, x1=100, y1=100,
                line=dict(color='gray', dash='dash')
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### 📊 Score Distribution")
            
            # Box plots for scores
            fig = go.Figure()
            fig.add_trace(go.Box(y=df['liquidity_score'], name='Liquidity', marker_color='#3498db'))
            fig.add_trace(go.Box(y=df['stability_score'], name='Stability', marker_color='#9b59b6'))
            fig.add_trace(go.Box(y=df['risk_score'], name='Composite Risk', marker_color='#e74c3c'))
            
            fig.update_layout(
                showlegend=False,
                yaxis_title="Score",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Volatility analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### APY Volatility Distribution")
            fig = px.histogram(
                df,
                x='apy_volatility',
                nbins=50,
                color='risk_level',
                color_discrete_map={'Low': '#2ecc71', 'Medium': '#f39c12', 'High': '#e74c3c'},
                labels={'apy_volatility': 'APY Standard Deviation (%)'}
            )
            fig.update_layout(showlegend=True, height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### TVL Volatility Distribution")
            fig = px.histogram(
                df,
                x='tvl_volatility',
                nbins=50,
                color='risk_level',
                color_discrete_map={'Low': '#2ecc71', 'Medium': '#f39c12', 'High': '#e74c3c'},
                labels={'tvl_volatility': 'TVL Coefficient of Variation (%)'}
            )
            fig.update_layout(showlegend=True, height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("Protocol Comparison")
        
        # Protocol selector
        protocols = sorted(df['project'].unique())
        selected_protocols = st.multiselect(
            "Select protocols to compare (max 10)",
            protocols,
            default=protocols[:5] if len(protocols) >= 5 else protocols
        )
        
        if len(selected_protocols) == 0:
            st.warning("Please select at least one protocol")
            return
        
        if len(selected_protocols) > 10:
            st.warning("Please select maximum 10 protocols")
            selected_protocols = selected_protocols[:10]
        
        # Filter data
        protocol_df = df[df['project'].isin(selected_protocols)].groupby('project').agg({
            'apy_mean': 'mean',
            'risk_score': 'mean',
            'liquidity_score': 'mean',
            'stability_score': 'mean',
            'tvl_mean': 'sum'
        }).reset_index()
        
        # Radar chart
        fig = go.Figure()
        
        for protocol in selected_protocols:
            protocol_data = protocol_df[protocol_df['project'] == protocol].iloc[0]
            
            fig.add_trace(go.Scatterpolar(
                r=[
                    protocol_data['liquidity_score'],
                    protocol_data['stability_score'],
                    100 - protocol_data['risk_score'],  # Invert for intuitive view
                    min(protocol_data['apy_mean'] * 10, 100)  # Scale APY
                ],
                theta=['Liquidity', 'Stability', 'Safety', 'Yield'],
                fill='toself',
                name=protocol
            ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            showlegend=True,
            height=500,
            title="Protocol Risk Profile Comparison"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Comparison table
        st.markdown("### Detailed Metrics")
        
        comparison_df = protocol_df.copy()
        comparison_df['apy_mean'] = comparison_df['apy_mean'].apply(lambda x: f"{x:.2f}%")
        comparison_df['risk_score'] = comparison_df['risk_score'].apply(lambda x: f"{x:.1f}")
        comparison_df['liquidity_score'] = comparison_df['liquidity_score'].apply(lambda x: f"{x:.1f}")
        comparison_df['stability_score'] = comparison_df['stability_score'].apply(lambda x: f"{x:.1f}")
        comparison_df['tvl_mean'] = comparison_df['tvl_mean'].apply(
            lambda x: f"${x/1e6:.1f}M" if x < 1e9 else f"${x/1e9:.2f}B"
        )
        
        comparison_df.columns = ['Protocol', 'Avg APY', 'Risk Score', 'Liquidity', 'Stability', 'Total TVL']
        
        st.dataframe(comparison_df, hide_index=True, use_container_width=True)
    
    with tab3:
        st.subheader("Risk Factor Analysis")
        st.markdown("What makes a pool risky? Explore the key factors.")
        
        # Correlation analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Risk vs APY")
            fig = px.scatter(
                df,
                x='risk_score',
                y='apy_mean',
                size='tvl_mean',
                color='chain',
                hover_data=['project', 'symbol'],
                labels={
                    'risk_score': 'Risk Score',
                    'apy_mean': 'Mean APY (%)'
                },
                title="Is higher yield worth the risk?"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### TVL vs Risk")
            fig = px.scatter(
                df,
                x='tvl_mean',
                y='risk_score',
                color='risk_level',
                hover_data=['project', 'symbol'],
                log_x=True,
                color_discrete_map={'Low': '#2ecc71', 'Medium': '#f39c12', 'High': '#e74c3c'},
                labels={
                    'tvl_mean': 'TVL (USD, log scale)',
                    'risk_score': 'Risk Score'
                },
                title="Does higher TVL mean lower risk?"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Chain risk analysis
        st.markdown("### Risk by Chain")
        
        chain_stats = df.groupby('chain').agg({
            'risk_score': 'mean',
            'apy_mean': 'mean',
            'tvl_mean': 'sum'
        }).reset_index()
        
        chain_stats = chain_stats.sort_values('risk_score')
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=chain_stats['chain'],
            y=chain_stats['risk_score'],
            name='Avg Risk Score',
            marker_color='#e74c3c'
        ))
        
        fig.update_layout(
            yaxis_title="Average Risk Score",
            xaxis_title="Chain",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)