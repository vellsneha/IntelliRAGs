# src/dashboard/pages/1_Dashboard.py

"""
Main Dashboard Page

Upload documents and ask questions using the RAG system.
"""

import streamlit as st
import requests
import sys
import os

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
    .section-card {
        background: white;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 25px;
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
    <p style="margin: 10px 0 0 0; color: white; opacity: 0.9;">Upload documents and ask questions</p>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# Section 1: Document Upload
# ═══════════════════════════════════════════════════════════

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("📄 Upload Document")

col_info, col_upload = st.columns([1, 1])

with col_info:
    st.info("""
    **📌 Supported Formats:**
    - PDF documents (.pdf)
    - Word documents (.docx)
    - Text files (.txt)
    
    **💡 Tip:** Upload your documents to build your knowledge base!
    """)

with col_upload:
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['pdf', 'docx', 'txt'],
        help="Upload documents to add to the knowledge base",
        label_visibility="collapsed"
    )
    
    if uploaded_file:
        file_col1, file_col2 = st.columns(2)
        with file_col1:
            st.metric("📄 Filename", uploaded_file.name)
        with file_col2:
            file_size_mb = uploaded_file.size / (1024 * 1024)
            st.metric("📦 Size", f"{file_size_mb:.2f} MB")
        
        if st.button("📤 Upload and Process", use_container_width=True, type="primary"):
            with st.spinner("📤 Processing document..."):
                try:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    uploaded_file.seek(0)
                    files = {
                        "file": (uploaded_file.name, uploaded_file, uploaded_file.type)
                    }
                    
                    response = requests.post(
                        f"{API_BASE_URL}/documents/upload",
                        headers=headers,
                        files=files,
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success(f"✅ {result['message']}")
                        
                        with st.expander("📊 View Processing Details"):
                            details = result['details']
                            st.write(f"**Document ID:** `{details['doc_id']}`")
                            st.write(f"**Chunks Created:** {details['chunks_created']}")
                            st.write(f"**Status:** {details['status']}")
                    else:
                        st.error(f"❌ Upload failed: {response.json().get('detail', 'Unknown error')}")
                        
                except Exception as e:
                    st.error(f"❌ Upload failed: {str(e)}")
st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# Section 2: Question & Answer Interface
# ═══════════════════════════════════════════════════════════

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("💬 Ask a Question")

with st.form("query_form", clear_on_submit=True):
    question = st.text_area(
        "Enter your question:",
        height=120,
        placeholder="e.g., What is our vacation policy? How many sick days do employees get?",
        help="Ask questions about your uploaded documents"
    )
    submit_query = st.form_submit_button("🚀 Get Answer", use_container_width=True, type="primary")
    
    if submit_query and question:
        with st.spinner("🤔 Thinking..."):
            try:
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                response = requests.post(
                    f"{API_BASE_URL}/query",
                    json={"question": question},
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Display answer in a nice card
                    st.success("✅ Answer Generated")
                    
                    st.markdown("### 📝 Answer")
                    st.info(result['answer'])
                    
                    # Display sources
                    st.markdown("### 📚 Sources")
                    unique_sources = list(set(result['sources']))
                    for i, source in enumerate(unique_sources, 1):
                        st.markdown(f"{i}. 📄 `{source}`")
                    
                    # Show confidence
                    confidence_pct = result['confidence'] * 100
                    st.progress(result['confidence'], text=f"Confidence: {confidence_pct:.0f}%")
                    
                    # Warning if flagged
                    if result.get('flagged', False):
                        st.warning("⚠️ This response contains potentially sensitive information and has been flagged for review.")
                    
                    # Store result for feedback
                    st.session_state.last_query_result = result
                
                elif response.status_code == 400:
                    st.error(f"❌ {response.json().get('detail', 'Bad request')}")
                elif response.status_code == 401:
                    st.error("❌ Authentication failed. Please login again.")
                    st.session_state.token = None
                    st.rerun()
                else:
                    st.error(f"❌ Error: {response.json().get('detail', 'Unknown error')}")
                    
            except requests.exceptions.Timeout:
                st.error("❌ Request timed out. The query took too long to process.")
            except requests.exceptions.ConnectionError:
                st.error("❌ Cannot connect to API server")
            except Exception as e:
                st.error(f"❌ Failed to get answer: {str(e)}")

st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# Feedback Section (outside form)
# ═══════════════════════════════════════════════════════════

if 'last_query_result' in st.session_state:
    st.markdown("### Was this helpful?")
    col_fb1, col_fb2 = st.columns(2)
    with col_fb1:
        if st.button("👍 Yes, helpful", key="helpful", use_container_width=True):
            st.success("Thank you for your feedback! 💙")
            if 'last_query_result' in st.session_state:
                del st.session_state.last_query_result
            st.rerun()
    with col_fb2:
        if st.button("👎 Not helpful", key="not_helpful", use_container_width=True):
            st.info("We'll work on improving our answers! 💪")
            if 'last_query_result' in st.session_state:
                del st.session_state.last_query_result
            st.rerun()

