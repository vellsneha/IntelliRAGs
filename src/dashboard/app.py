# src/dashboard/app.py

"""
Main Login Page for Enterprise RAG System

Handles authentication and navigation to other pages.
"""

import streamlit as st
import requests
import sys
import os
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ═══════════════════════════════════════════════════════════
# Page Configuration
# ═══════════════════════════════════════════════════════════

st.set_page_config(
    page_title="RAG System - Login",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"  # Show sidebar so navigation is visible
)

# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════

API_BASE_URL = "http://localhost:8000"

# Initialize session state
if 'token' not in st.session_state:
    st.session_state.token = None

# Show authenticated state - Streamlit will auto-create navigation in sidebar
if st.session_state.token:
    st.success("✅ You are logged in!")
    st.info("👈 **Click on 'Dashboard' or 'Statistics' in the sidebar above to get started!**")
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🎉 Ready to get started?")
        st.markdown("""
        **Available Pages:**
        - **🏠 Dashboard** - Upload documents and ask questions
        - **📊 Statistics** - View analytics and metrics
        """)
        st.markdown("""
        <div style="text-align: center; margin-top: 20px;">
            <p style="font-size: 1.1rem; color: #666;">
                Use the sidebar navigation menu to switch between pages
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Stop rendering the login form
    st.stop()

# ═══════════════════════════════════════════════════════════
# Custom CSS for better styling
# ═══════════════════════════════════════════════════════════

st.markdown("""
<style>
    .login-container {
        max-width: 500px;
        margin: 100px auto;
        padding: 40px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }
    .login-header {
        text-align: center;
        color: white;
        margin-bottom: 30px;
    }
    .login-header h1 {
        font-size: 2.5rem;
        margin-bottom: 10px;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        padding: 0.75rem;
        font-size: 1.1rem;
        font-weight: 600;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        color: white;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
    }
    [data-testid="stTextInput"]>div>div>input {
        border-radius: 10px;
        padding: 12px;
    }
    .error-box {
        padding: 15px;
        border-radius: 10px;
        background-color: #fee;
        border-left: 4px solid #f33;
        margin: 15px 0;
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# Login Page
# ═══════════════════════════════════════════════════════════

# Center the login form
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown("""
    <div class="login-header">
        <h1>🚀 Enterprise RAG System</h1>
        <p style="font-size: 1.2rem; opacity: 0.9;">Intelligent Document Q&A Platform</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Login Form
    with st.form("login_form"):
        st.markdown("### 🔐 Sign In")
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submit = st.form_submit_button("Login", use_container_width=True)
        
        if submit:
            if not username or not password:
                st.error("⚠️ Please enter both username and password")
            else:
                try:
                    with st.spinner("🔐 Authenticating..."):
                        response = requests.post(
                            f"{API_BASE_URL}/auth/login",
                            json={"username": username, "password": password},
                            timeout=5
                        )
                        
                        if response.status_code == 200:
                            st.session_state.token = response.json()["access_token"]
                            st.success("✅ Login successful!")
                            st.balloons()  # Celebrate the login!
                            st.info("👈 **Look at the sidebar above - click on 'Dashboard' or 'Statistics' to continue!**")
                            st.markdown("---")
                            st.markdown("### 🎯 Quick Navigation")
                            st.markdown("""
                            After login, Streamlit automatically shows page navigation in the sidebar:
                            - Click **🏠 Dashboard** to upload documents and ask questions
                            - Click **📊 Statistics** to view analytics
                            """)
                        else:
                            st.error("❌ Invalid username or password")
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to API server")
                    st.info("💡 Make sure the API is running:\n```bash\nuvicorn src.api.main:app --reload\n```")
                except Exception as e:
                    st.error(f"❌ Login failed: {str(e)}")
    
    # Demo credentials info
    st.markdown("---")
    with st.expander("📋 Demo Credentials", expanded=False):
        st.code("""
Username: demo
Password: demo123
        """)
    
    # Check API status
    with st.expander("🔧 System Status"):
        try:
            response = requests.get(f"{API_BASE_URL}/", timeout=2)
            if response.status_code == 200:
                st.success("✅ API Server: Online")
            else:
                st.error("❌ API Server: Error")
        except:
            st.error("❌ API Server: Offline")
            st.info("Start the API server to continue")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; padding: 20px;'>"
    "Enterprise RAG System v1.0 | Powered by Streamlit & FastAPI"
    "</div>",
    unsafe_allow_html=True
)
