# src/dashboard/pages/2_Statistics.py

"""
Statistics and Analytics Page

View comprehensive analytics, metrics, and system performance data.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from analytics.tracker import AnalyticsTracker

# ═══════════════════════════════════════════════════════════
# Page Configuration
# ═══════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Statistics - RAG System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════

tracker = AnalyticsTracker()

# Check authentication
if 'token' not in st.session_state or st.session_state.token is None:
    st.warning("⚠️ Please login to access statistics")
    st.stop()

# ═══════════════════════════════════════════════════════════
# Custom CSS
# ═══════════════════════════════════════════════════════════

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px;
        border-radius: 15px;
        color: white;
        margin-bottom: 30px;
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        text-align: center;
    }
    .section-card {
        background: white;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 25px;
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# Sidebar Navigation
# ═══════════════════════════════════════════════════════════

st.sidebar.title("🧭 Navigation")
st.sidebar.markdown("---")
st.sidebar.info("💡 Use the navigation above to switch between pages")

st.sidebar.markdown("---")
st.sidebar.success("✅ Authenticated")
if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.token = None
    st.session_state.page = 'login'
    st.rerun()

# ═══════════════════════════════════════════════════════════
# Main Header
# ═══════════════════════════════════════════════════════════

st.markdown("""
<div class="main-header">
    <h1 style="margin: 0; color: white;">📊 Statistics & Analytics</h1>
    <p style="margin: 10px 0 0 0; color: white; opacity: 0.9;">System performance and usage insights</p>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# Get Analytics Data
# ═══════════════════════════════════════════════════════════

try:
    summary = tracker.get_summary()
except Exception as e:
    st.error(f"❌ Failed to load analytics: {str(e)}")
    summary = {
        'total_queries': 0,
        'avg_latency_seconds': 0,
        'flagged_queries': 0,
        'top_users': [],
        'recent_queries': [],
        'events_summary': {}
    }

# ═══════════════════════════════════════════════════════════
# Section 1: Key Metrics
# ═══════════════════════════════════════════════════════════

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("📈 System Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total Queries",
        value=summary['total_queries'],
        help="Total number of questions asked"
    )

with col2:
    st.metric(
        label="Avg Latency",
        value=f"{summary['avg_latency_seconds']:.2f}s",
        help="Average time to generate answers"
    )

with col3:
    st.metric(
        label="Flagged Queries",
        value=summary['flagged_queries'],
        delta_color="inverse",
        help="Queries flagged by security guardrails"
    )

with col4:
    if summary['total_queries'] > 0:
        success_rate = ((summary['total_queries'] - summary['flagged_queries']) / 
                       summary['total_queries'] * 100)
    else:
        success_rate = 100
    st.metric(
        label="Success Rate",
        value=f"{success_rate:.1f}%",
        help="Percentage of successful queries"
    )

st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# Section 2: Visualizations
# ═══════════════════════════════════════════════════════════

col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("📊 Query Trends (Last 7 Days)")
    trends = tracker.get_query_trends(days=7)
    
    if trends and len(trends) > 0:
        df_trends = pd.DataFrame(trends)
        fig = px.line(
            df_trends,
            x='date',
            y='count',
            title='Daily Query Volume',
            markers=True,
            line_shape='spline'
        )
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Number of Queries",
            hovermode='x unified',
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        fig.update_traces(line_color='#667eea', marker=dict(size=8, color='#764ba2'))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📭 No query trend data available yet. Start asking questions!")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Recent Queries Table
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("🔍 Recent Queries")
    if summary['recent_queries']:
        df_recent = pd.DataFrame(summary['recent_queries'])
        df_recent['status'] = df_recent['flagged'].apply(lambda x: '⚠️' if x else '✅')
        
        st.dataframe(
            df_recent[['status', 'timestamp', 'user', 'question', 'latency']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "status": st.column_config.TextColumn("", width="small"),
                "timestamp": st.column_config.TextColumn("Time", width="medium"),
                "user": st.column_config.TextColumn("User", width="medium"),
                "question": st.column_config.TextColumn("Question", width="large"),
                "latency": st.column_config.NumberColumn("Latency (s)", format="%.3f")
            }
        )
    else:
        st.info("📭 No recent queries yet")
    st.markdown('</div>', unsafe_allow_html=True)

with col_right:
    # Top Users Chart
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("👥 Top Users")
    if summary['top_users']:
        users_data = pd.DataFrame(summary['top_users'])
        fig = px.bar(
            users_data,
            x='count',
            y='user',
            orientation='h',
            title='Most Active Users',
            color='count',
            color_continuous_scale='Viridis'
        )
        fig.update_layout(
            xaxis_title="Query Count",
            yaxis_title="",
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("👤 No user data yet")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Events Summary
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("📋 System Events")
    if summary['events_summary']:
        events_df = pd.DataFrame([
            {"Event": k.replace('_', ' ').title(), "Count": v}
            for k, v in summary['events_summary'].items()
        ])
        st.dataframe(
            events_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Event": st.column_config.TextColumn("Event Type"),
                "Count": st.column_config.NumberColumn("Count", format="%d")
            }
        )
    else:
        st.info("📋 No events logged yet")
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption(f"🕐 Last updated: {summary.get('generated_at', 'N/A')}")
st.caption("💡 Refresh the page to see the latest statistics")

