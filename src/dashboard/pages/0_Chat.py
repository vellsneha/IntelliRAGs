# src/dashboard/pages/0_Chat.py

"""
Chat Space Page

Individual chat interface with document management and query interface.
"""

import streamlit as st
import requests
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ═══════════════════════════════════════════════════════════
# Page Configuration
# ═══════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Chat - RAG System",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════

API_BASE_URL = "http://localhost:8000"

# Check authentication
if 'token' not in st.session_state or st.session_state.token is None:
    st.warning("⚠️ Please login to access the chat")
    st.stop()

# Get chat_id from session state (set by Dashboard page)
chat_id = st.session_state.get('current_chat_id')

if not chat_id:
    st.error("❌ No chat selected. Please select a chat from the Dashboard.")
    st.info("👈 Use the sidebar navigation to go to **Dashboard** and select a chat.")
    if 'current_chat_id' in st.session_state:
        del st.session_state.current_chat_id
    st.stop()

# ═══════════════════════════════════════════════════════════
# Custom CSS
# ═══════════════════════════════════════════════════════════

st.markdown("""
<style>
    .chat-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin-bottom: 20px;
    }
    .document-card {
        background: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 10px;
        border-left: 4px solid #667eea;
    }
    .message-user {
        background: #e3f2fd;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .message-assistant {
        background: #f5f5f5;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# Load Chat Data
# ═══════════════════════════════════════════════════════════

headers = {"Authorization": f"Bearer {st.session_state.token}"}

# Fetch chat details
try:
    response = requests.get(f"{API_BASE_URL}/chats/{chat_id}", headers=headers, timeout=5)
    if response.status_code != 200:
        st.error(f"❌ Failed to load chat: {response.json().get('detail', 'Unknown error')}")
        st.stop()
    chat_data = response.json()
except Exception as e:
    st.error(f"❌ Error loading chat: {str(e)}")
    st.stop()

# ═══════════════════════════════════════════════════════════
# Sidebar Navigation
# ═══════════════════════════════════════════════════════════

st.sidebar.title("🧭 Navigation")
st.sidebar.markdown("---")

if st.sidebar.button("← Back to Dashboard", use_container_width=True):
    if 'current_chat_id' in st.session_state:
        del st.session_state.current_chat_id
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.success("✅ Authenticated")

if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.token = None
    st.rerun()

# ═══════════════════════════════════════════════════════════
# Chat Header
# ═══════════════════════════════════════════════════════════

col_title, col_actions = st.columns([3, 1])
with col_title:
    st.markdown(f"""
    <div class="chat-header">
        <h2 style="margin: 0; color: white;">💬 {chat_data.get('title', 'Chat')}</h2>
        <p style="margin: 5px 0 0 0; color: white; opacity: 0.9;">
            Created: {datetime.fromisoformat(chat_data['created_at']).strftime('%Y-%m-%d %H:%M')}
        </p>
    </div>
    """, unsafe_allow_html=True)

with col_actions:
    if st.button("🗑️ Delete Chat", type="secondary"):
        if st.session_state.get('confirm_delete') == chat_id:
            # Delete chat
            response = requests.delete(f"{API_BASE_URL}/chats/{chat_id}", headers=headers)
            if response.status_code == 200:
                st.success("✅ Chat deleted")
                if 'current_chat_id' in st.session_state:
                    del st.session_state.current_chat_id
                st.rerun()
        else:
            st.session_state.confirm_delete = chat_id
            st.warning("⚠️ Click again to confirm deletion")

# ═══════════════════════════════════════════════════════════
# Main Content: Two Columns
# ═══════════════════════════════════════════════════════════

col_docs, col_chat = st.columns([1, 2])

# ═══════════════════════════════════════════════════════════
# Left Column: Document Management
# ═══════════════════════════════════════════════════════════

with col_docs:
    st.subheader("📄 Documents")
    
    # Upload new document
    with st.expander("➕ Upload New Document", expanded=False):
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['pdf', 'docx', 'txt'],
            key=f"upload_{chat_id}",
            help="Upload documents to this chat"
        )
        
        if uploaded_file and st.button("📤 Upload", key=f"upload_btn_{chat_id}"):
            with st.spinner("📤 Uploading..."):
                try:
                    uploaded_file.seek(0)
                    files = {
                        "file": (uploaded_file.name, uploaded_file, uploaded_file.type)
                    }
                    
                    response = requests.post(
                        f"{API_BASE_URL}/chats/{chat_id}/documents/upload",
                        headers=headers,
                        files=files,
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        st.success(f"✅ {uploaded_file.name} uploaded successfully!")
                        st.rerun()
                    else:
                        st.error(f"❌ Upload failed: {response.json().get('detail', 'Unknown error')}")
                        
                except Exception as e:
                    st.error(f"❌ Upload failed: {str(e)}")
    
    st.markdown("---")
    
    # List documents
    documents = chat_data.get('documents', [])
    
    if not documents:
        st.info("📭 No documents uploaded yet. Upload documents to get started!")
    else:
        st.write(f"**{len(documents)} document(s) attached:**")
        
        for doc in documents:
            with st.container():
                st.markdown(f"""
                <div class="document-card">
                    <strong>📄 {doc['filename']}</strong><br>
                    <small>Uploaded: {datetime.fromisoformat(doc['uploaded_at']).strftime('%Y-%m-%d %H:%M')}</small>
                </div>
                """, unsafe_allow_html=True)
                
                # Delete button
                if st.button("🗑️ Remove", key=f"delete_{doc['id']}", use_container_width=True):
                    response = requests.delete(
                        f"{API_BASE_URL}/chats/{chat_id}/documents/{doc['document_id']}",
                        headers=headers
                    )
                    if response.status_code == 200:
                        st.success("✅ Document removed")
                        st.rerun()
                    else:
                        st.error("❌ Failed to remove document")

# ═══════════════════════════════════════════════════════════
# Right Column: Chat Interface
# ═══════════════════════════════════════════════════════════

with col_chat:
    st.subheader("💬 Conversation")
    
    # Display conversation history
    conversation = chat_data.get('conversation', [])
    
    if conversation:
        for msg in conversation:
            # User message
            st.markdown(f"""
            <div class="message-user">
                <strong>👤 You:</strong><br>
                {msg['question']}
            </div>
            """, unsafe_allow_html=True)
            
            # Assistant message
            st.markdown(f"""
            <div class="message-assistant">
                <strong>🤖 Assistant:</strong><br>
                {msg['answer']}
            </div>
            """, unsafe_allow_html=True)
            
            # Sources
            if msg.get('sources'):
                with st.expander("📚 Sources", expanded=False):
                    for source in msg['sources']:
                        st.write(f"• {source}")
            
            st.markdown("---")
    else:
        st.info("💡 Start asking questions! Your conversation will appear here.")
    
    # Query interface
    st.markdown("### Ask a Question")
    
    with st.form("query_form", clear_on_submit=True):
        question = st.text_area(
            "Enter your question:",
            height=100,
            placeholder="e.g., What is in the uploaded documents?",
            help="Ask questions about the documents in this chat"
        )
        submit_query = st.form_submit_button("🚀 Get Answer", use_container_width=True, type="primary")
        
        if submit_query and question:
            with st.spinner("🤔 Thinking..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/chats/{chat_id}/query",
                        json={"question": question},
                        headers=headers,
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Reload chat to show new conversation
                        st.rerun()
                    else:
                        st.error(f"❌ {response.json().get('detail', 'Unknown error')}")
                        
                except requests.exceptions.Timeout:
                    st.error("❌ Request timed out. Please try again.")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

