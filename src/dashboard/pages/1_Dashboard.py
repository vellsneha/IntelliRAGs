# src/dashboard/pages/1_Dashboard.py

"""
Main Dashboard Page

Shows list of all chats and allows creating new chats.
"""

import streamlit as st
import requests
import sys
import os
import time
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ═══════════════════════════════════════════════════════════
# Page Configuration
# ═══════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Dashboard - RAG System",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════

API_BASE_URL = "http://localhost:8000"

# Check authentication
if 'token' not in st.session_state or st.session_state.token is None:
    st.warning("⚠️ Please login to access the dashboard")
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
    .chat-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 15px;
        border-left: 4px solid #667eea;
        transition: transform 0.2s;
    }
    .chat-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(0,0,0,0.15);
    }
    .stButton>button {
        border-radius: 10px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
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
    <h1 style="margin: 0; color: white;">🏠 Dashboard</h1>
    <p style="margin: 10px 0 0 0; color: white; opacity: 0.9;">Manage your retrieval chats</p>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# Start New Chat Section
# ═══════════════════════════════════════════════════════════

headers = {"Authorization": f"Bearer {st.session_state.token}"}

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("### 🆕 Start New Retrieval Chat")
    
    with st.form("new_chat_form"):
        chat_title = st.text_input(
            "Chat Title (optional):",
            placeholder="e.g., Company Policies Q&A",
            help="Leave empty for default title"
        )
        create_chat = st.form_submit_button("✨ Create New Chat", use_container_width=True, type="primary")
        
        if create_chat:
            with st.spinner("Creating chat..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/chats",
                        json={"title": chat_title if chat_title else None},
                        headers=headers,
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        chat_id = result['chat_id']
                        st.success(f"✅ Chat created! Opening chat...")
                        
                        # Navigate to chat page by setting session state
                        st.session_state.current_chat_id = chat_id
                        # Reload page to show updated chat list
                        time.sleep(0.5)  # Brief delay for user feedback
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to create chat: {response.json().get('detail', 'Unknown error')}")
                        
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

st.markdown("---")

# ═══════════════════════════════════════════════════════════
# Chat List Section
# ═══════════════════════════════════════════════════════════

st.markdown("### 📋 Your Chats")

# Fetch chats
try:
    response = requests.get(f"{API_BASE_URL}/chats", headers=headers, timeout=5)
    
    if response.status_code == 200:
        chats_data = response.json()
        chats = chats_data.get('chats', [])
        
        if not chats:
            st.info("""
            📭 **No chats yet!**
            
            Click "Create New Chat" above to start your first retrieval chat.
            Each chat can have its own documents and conversation history.
            """)
        else:
            st.write(f"**{len(chats)} chat(s) found:**")
            st.markdown("")
            
            # Display chats in a list
            for chat in chats:
                # Format date
                updated_date = datetime.fromisoformat(chat['updated_at'])
                created_date = datetime.fromisoformat(chat['created_at'])
                
                # Create chat card
                with st.container():
                    col_info, col_action = st.columns([4, 1])
                    
                    with col_info:
                        st.markdown(f"""
                        <div class="chat-card">
                            <h3 style="margin: 0;">💬 {chat['title']}</h3>
                            <p style="margin: 5px 0; color: #666;">
                                📄 {chat.get('document_count', 0)} documents | 
                                💬 {chat.get('message_count', 0)} messages
                            </p>
                            <p style="margin: 5px 0; color: #999; font-size: 0.9em;">
                                Updated: {updated_date.strftime('%Y-%m-%d %H:%M')} | 
                                Created: {created_date.strftime('%Y-%m-%d')}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col_action:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("▶️ Open", key=f"open_{chat['chat_id']}", use_container_width=True):
                            # Navigate to chat page by setting session state
                            st.session_state.current_chat_id = chat['chat_id']
                            st.rerun()
                    
                    st.markdown("")
    
    elif response.status_code == 401:
        st.error("❌ Authentication failed. Please login again.")
        st.session_state.token = None
        st.rerun()
    else:
        st.error(f"❌ Failed to load chats: {response.json().get('detail', 'Unknown error')}")

except requests.exceptions.ConnectionError:
    st.error("❌ Cannot connect to API server")
    st.info("💡 Make sure the API is running:\n```bash\nuvicorn src.api.main:app --reload\n```")
except Exception as e:
    st.error(f"❌ Error loading chats: {str(e)}")
