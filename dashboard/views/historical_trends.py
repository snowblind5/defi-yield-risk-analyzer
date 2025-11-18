"""
Historical Trends page - Time series analysis
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.database import get_session, Pool, PoolMetric


def load_pool_history(pool_id: int, days: int = 90):
    """Load historical metrics for a pool"""
    from datetime import datetime, timedelta, timezone
    
    session = get_session()
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    metrics = session.query(PoolMetric).filter(
        PoolMetric.pool_id == pool_id,
        PoolMetric.date >= cutoff_date
    ).order_by(PoolMetric.date).all()
    
    data = [{
        'date': m.date,
        'apy': m.apy,
        'tvl_usd': m.tvl_usd
    } for m in metrics]
    
    return pd.DataFrame(data)


def show():
    """Render historical trends page"""
    st.title("📈 Historical Trends")
    st.markdown("Analyze how yields and liquidity have evolved over time")
    
    session = get_session()
    
    # Get pools with sufficient data
    pools = session.query(Pool).all()
    pools_with_data = []
    
    for pool in pools:
        metric_count = session.query(PoolMetric).filter_by(pool_id=pool.id).count()
        if metric_count >= 7:
            pools_with_data.append(pool)
    
    if len(pools_with_data) == 0:
        st.error("No pools with historical data available.")
        return
    
    # Pool selector
    pool_options = {f"{p.project} - {p.symbol} ({p.chain})": p for p in pools_with_data}
    selected_pool_name = st.selectbox(
        "Select Pool",
        options=list(pool_options.keys())
    )
    
    selected_pool = pool_options[selected_pool_name]
    
    # Time range selector
    col1, col2 = st.columns([3, 1])
    
    with col1:
        time_range = st.slider(
            "Time Range (days)",
            min_value=7,
            max_value=90,
            value=30,
            step=7
        )
    
    with col2:
        st.markdown("")
        st.markdown("")
        show_tvl = st.checkbox("Show TVL", value=True)
    
    # Load data
    with st.spinner("Loading historical data..."):
        df = load_pool_history(selected_pool.id, days=time_range)
    
    if len(df) == 0:
        st.warning("No historical data available for this pool.")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        current_apy = df.iloc[-1]['apy']
        prev_apy = df.iloc[0]['apy']
        apy_change = current_apy - prev_apy
        st.metric(
            "Current APY",
            f"{current_apy:.2f}%",
            delta=f"{apy_change:+.2f}%"
        )
    
    with col2:
        avg_apy = df['apy'].mean()
        st.metric(
            "Average APY",
            f"{avg_apy:.2f}%"
        )
    
    with col3:
        apy_volatility = df['apy'].std()
        st.metric(
            "APY Volatility",
            f"{apy_volatility:.2f}%"
        )
    
    with col4:
        current_tvl = df.iloc[-1]['tvl_usd']
        tvl_display = f"${current_tvl/1e6:.1f}M" if current_tvl < 1e9 else f"${current_tvl/1e9:.2f}B"
        st.metric(
            "Current TVL",
            tvl_display
        )
    
    st.markdown("---")
    
    # APY Chart
    st.subheader("📊 APY Over Time")
    
    fig = go.Figure()
    
    # APY line
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['apy'],
        mode='lines',
        name='APY',
        line=dict(color='#3498db', width=2),
        fill='tozeroy',
        fillcolor='rgba(52, 152, 219, 0.1)'
    ))
    
    # Add moving average
    df['apy_ma7'] = df['apy'].rolling(window=7, min_periods=1).mean()
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['apy_ma7'],
        mode='lines',
        name='7-day MA',
        line=dict(color='#e74c3c', width=1, dash='dash')
    ))
    
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="APY (%)",
        hovermode='x unified',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # TVL Chart (if enabled)
    if show_tvl:
        st.subheader("💰 TVL Over Time")
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['tvl_usd'],
            mode='lines',
            name='TVL',
            line=dict(color='#2ecc71', width=2),
            fill='tozeroy',
            fillcolor='rgba(46, 204, 113, 0.1)'
        ))
        
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="TVL (USD)",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Statistics
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📉 APY Statistics")
        
        stats_df = pd.DataFrame({
            'Metric': ['Min', 'Max', 'Mean', 'Median', 'Std Dev'],
            'Value': [
                f"{df['apy'].min():.2f}%",
                f"{df['apy'].max():.2f}%",
                f"{df['apy'].mean():.2f}%",
                f"{df['apy'].median():.2f}%",
                f"{df['apy'].std():.2f}%"
            ]
        })
        
        st.dataframe(stats_df, hide_index=True, use_container_width=True)
    
    with col2:
        st.subheader("💎 TVL Statistics")
        
        def format_usd(value):
            if value < 1e6:
                return f"${value/1e3:.1f}K"
            elif value < 1e9:
                return f"${value/1e6:.1f}M"
            else:
                return f"${value/1e9:.2f}B"
        
        stats_df = pd.DataFrame({
            'Metric': ['Min', 'Max', 'Mean', 'Median', 'Change'],
            'Value': [
                format_usd(df['tvl_usd'].min()),
                format_usd(df['tvl_usd'].max()),
                format_usd(df['tvl_usd'].mean()),
                format_usd(df['tvl_usd'].median()),
                f"{((df.iloc[-1]['tvl_usd'] / df.iloc[0]['tvl_usd']) - 1) * 100:+.1f}%"
            ]
        })
        
        st.dataframe(stats_df, hide_index=True, use_container_width=True)
    
    # Export option
    st.markdown("---")
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Export Historical Data",
        data=csv,
        file_name=f"{selected_pool.project}_{selected_pool.symbol}_history.csv",
        mime="text/csv"
    )