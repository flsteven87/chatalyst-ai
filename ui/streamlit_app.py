"""
Streamlit application for interacting with the SQL Agent.
Refactored to follow Streamlit best practices for session state and chat interface.
"""
import sys
import os
import time
import streamlit as st
import pandas as pd
import logging
from dotenv import load_dotenv

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
dotenv_path = os.path.join(project_root, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    logger.info(f"Loaded environment variables from {dotenv_path}")
elif os.path.exists(".env"):
    load_dotenv(".env")
    logger.info("Loaded environment variables from local .env")
else:
    logger.warning("No .env file found at project root or current directory.")

# Import from the app_helpers module
from ui.app_helpers import (
    generate_questions_cached,
    generate_sql_cached,
    run_sql_cached,
    is_sql_valid_cached,
    get_vanna_agent
)

# Vanna AI Avatar URL
AVATAR_URL = "https://vanna.ai/img/vanna.svg"

def check_authentication():
    """
    Check POC access authentication.
    
    Displays login screen and validates access code before allowing
    users to proceed to the main application.
    """
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        # Display login screen
        st.title("🔐 Chatalyst AI - Access Verification")
        st.markdown("**This is a POC test version. Please enter the access code to continue using:**")
        st.markdown("---")
        
        # Center the input form
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            access_code = st.text_input(
                "Access Code", 
                type="password", 
                key="access_code",
                placeholder="Please enter the access code",
                help="If you need an access code, please contact the system administrator"
            )
            
            if st.button("🔓 Verify", type="primary", use_container_width=True):
                if access_code == "ABConvert":
                    st.session_state.authenticated = True
                    st.success("✅ Verification successful! Loading application...")
                    logger.info("User successfully authenticated for POC access")
                    st.rerun()
                else:
                    st.error("❌ Access code incorrect, please try again")
                    logger.warning("Failed authentication attempt")
        
        # Additional info
        st.markdown("---")
        st.caption("🔒 This system is only for authorized personnel testing")
        
        st.stop()  # Prevent further execution

def initialize_session_state():
    """Initialize session state variables for conversation management."""
    if "conversation_history_ui" not in st.session_state:
        st.session_state.conversation_history_ui = []
    if "saved_conversations" not in st.session_state:
        st.session_state.saved_conversations = {}
    if "conversation_counter" not in st.session_state:
        st.session_state.conversation_counter = 0
    if "editing_conversation" not in st.session_state:
        st.session_state.editing_conversation = None
    if "current_loaded_conversation_id" not in st.session_state:
        st.session_state.current_loaded_conversation_id = None

def add_to_ui_history(role: str, content: str, metadata: dict = None):
    """Add message to UI conversation history."""
    entry = {
        "role": role,
        "content": content,
        "timestamp": time.time(),
        "metadata": metadata or {}
    }
    st.session_state.conversation_history_ui.append(entry)

def display_conversation_history():
    """Display all conversation history with user messages as chat and agent responses as expandable sections."""
    if not st.session_state.conversation_history_ui:
        return
    
    # Track current question and responses
    current_question = None
    current_sql = None
    current_results = None
    first_message = True
    
    for entry in st.session_state.conversation_history_ui:
        role = entry["role"]
        content = entry["content"]
        metadata = entry.get("metadata", {})
        
        if role == "user":
            # Add separator before user question (except for the first message)
            if not first_message:
                st.markdown("---")
            
            # Display user question with original chat_message style
            with st.chat_message("user"):
                st.write(content)
            current_question = content
            current_sql = None
            current_results = None
            first_message = False
            
        elif role == "assistant":
            if "sql" in metadata:
                current_sql = metadata["sql"]
            elif metadata.get("df_results_data") is not None:
                current_results = metadata
                
                # Now display agent response with separate expanders
                st.markdown("---")  # Visual separator
                
                # SQL Expander
                if current_sql:
                    with st.expander("🔍 **Generated SQL Query**", expanded=False):
                        st.code(current_sql, language="sql", line_numbers=True)
                
                # Results Expander
                df_data = current_results.get("df_results_data")
                if df_data and len(df_data) > 0:
                    df = pd.DataFrame(df_data)
                    rows_text = "row" if len(df) == 1 else "rows"
                    with st.expander(f"📊 **Query Results** ({len(df)} {rows_text})", expanded=True):
                        st.caption(f"Showing first {min(len(df), 250)} rows")
                        st.dataframe(df.head(min(len(df), 250)), use_container_width=True)
                else:
                    with st.expander("📊 **Query Results**", expanded=True):
                        st.info("✅ Query executed successfully, no data returned")
                
                # Reset for next Q&A
                current_sql = None
                current_results = None
                
            elif "❌ Error:" in content:
                # Handle error case
                st.markdown("---")  # Visual separator
                st.error(content.replace("❌ Error: ", ""))

def auto_save_current_conversation():
    """Auto-save current conversation if it has content."""
    if st.session_state.conversation_history_ui and len(st.session_state.conversation_history_ui) > 0:
        # Check if this is an existing loaded conversation
        if st.session_state.current_loaded_conversation_id and st.session_state.current_loaded_conversation_id in st.session_state.saved_conversations:
            # Update existing conversation
            conv_id = st.session_state.current_loaded_conversation_id
            st.session_state.saved_conversations[conv_id]["history"] = st.session_state.conversation_history_ui.copy()
            st.session_state.saved_conversations[conv_id]["timestamp"] = time.time()
            logger.info(f"Updated existing conversation: {st.session_state.saved_conversations[conv_id]['name']}")
        else:
            # Create new conversation
            conv_id = f"conv_{int(time.time())}"
            
            # Generate simple conversation name
            st.session_state.conversation_counter += 1
            conversation_name = f"Conversation {st.session_state.conversation_counter}"
            
            # Save new conversation
            st.session_state.saved_conversations[conv_id] = {
                "history": st.session_state.conversation_history_ui.copy(),
                "name": conversation_name,
                "timestamp": time.time()
            }
            # Set this as current loaded conversation
            st.session_state.current_loaded_conversation_id = conv_id
            logger.info(f"Auto-saved new conversation: {conversation_name}")

def load_conversation(conversation_id: str):
    """Load a saved conversation - using callback approach."""
    if conversation_id in st.session_state.saved_conversations:
        st.session_state.conversation_history_ui = st.session_state.saved_conversations[conversation_id]["history"].copy()
        st.session_state.current_loaded_conversation_id = conversation_id
        
        # Also load conversation to agent
        agent = get_vanna_agent()
        if agent:
            agent.clear_conversation()
            # Rebuild agent's conversation history from UI history
            current_question = None
            current_sql = None
            
            for entry in st.session_state.conversation_history_ui:
                if entry["role"] == "user":
                    current_question = entry["content"]
                elif entry["role"] == "assistant" and current_question:
                    metadata = entry.get("metadata", {})
                    if "sql" in metadata:
                        current_sql = metadata["sql"]
                        agent._add_to_conversation_history({
                            "type": "question",
                            "original_question": current_question,
                            "processed_question": current_question,
                            "sql": current_sql,
                            "context_used": False
                        })
                        current_question = None
                        current_sql = None

def start_new_conversation():
    """Start a new conversation - using callback approach."""
    # Auto-save current conversation if it has content
    auto_save_current_conversation()
    
    # Clear current conversation
    st.session_state.conversation_history_ui = []
    st.session_state.current_loaded_conversation_id = None
    
    # Clear agent's conversation history
    agent = get_vanna_agent()
    if agent:
        agent.clear_conversation()
    
    logger.info("Started new conversation")

def delete_conversation(conversation_id: str):
    """Delete a saved conversation - using callback approach."""
    if conversation_id in st.session_state.saved_conversations:
        del st.session_state.saved_conversations[conversation_id]
        logger.info(f"Deleted conversation: {conversation_id}")

def rename_conversation(conversation_id: str, new_name: str):
    """Rename a conversation."""
    if conversation_id in st.session_state.saved_conversations and new_name.strip():
        old_name = st.session_state.saved_conversations[conversation_id]["name"]
        st.session_state.saved_conversations[conversation_id]["name"] = new_name.strip()
        logger.info(f"Renamed conversation {conversation_id} from '{old_name}' to '{new_name.strip()}'")
        return True
    return False

def clear_conversation():
    """Clear conversation history in both UI and agent - using callback approach."""
    st.session_state.conversation_history_ui = []
    st.session_state.current_loaded_conversation_id = None
    # Clear agent's conversation history
    agent = get_vanna_agent()
    if agent:
        agent.clear_conversation()
    logger.info("Conversation cleared by user")

def has_active_conversation():
    """Check if there's an active conversation."""
    return len(st.session_state.conversation_history_ui) > 0

def process_question(question: str):
    """Process a user question and update conversation history."""
    # Add user question to UI history
    add_to_ui_history("user", question)
    
    # Generate SQL with conversation context (always enabled)
    with st.spinner("Generating and executing SQL query..."):
        sql_query_or_error = generate_sql_cached(question=question)

        if not sql_query_or_error or not is_sql_valid_cached(sql=sql_query_or_error):
            error_msg = sql_query_or_error or "Failed to generate a valid SQL query."
            add_to_ui_history("assistant", f"❌ Error: {error_msg}")
            # Auto-save conversation after adding error
            auto_save_current_conversation()
            st.rerun()  # Force UI update to show error
            return
        
        sql_query = sql_query_or_error
        
        # Add SQL to UI history
        add_to_ui_history("assistant", "SQL Query Generated", {"sql": sql_query})
        
        # Execute SQL and display results
        df_results = run_sql_cached(sql=sql_query)
    
    if df_results is None:
        error_msg = "Error executing the SQL query. Please check the query or database connection."
        add_to_ui_history("assistant", f"❌ Error: {error_msg}")
        # Auto-save conversation after adding error
        auto_save_current_conversation()
        st.rerun()  # Force UI update to show error
        return
    
    # Store dataframe in session state
    st.session_state["df_results"] = df_results

    # Add results to UI history with actual DataFrame data
    results_summary = f"Query executed successfully. {len(df_results)} rows returned."
    df_data_for_history = None
    if not df_results.empty:
        # Store only first 1000 rows to avoid memory issues
        df_for_storage = df_results.head(1000)
        df_data_for_history = df_for_storage.to_dict('records')
    
    add_to_ui_history("assistant", results_summary, {
        "rows_count": len(df_results), 
        "df_results_data": df_data_for_history
    })
    
    # Auto-save conversation after successful completion
    auto_save_current_conversation()
    
    # Force UI update to show all the new conversation content
    st.rerun()

def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(
        page_title="Chatalyst AI - Data Query Assistant",
        page_icon="📊",
        layout="wide"
    )

    # POC Authentication Check
    check_authentication()

    # Initialize session state
    initialize_session_state()

    # Initialize Vanna Agent early
    if not get_vanna_agent():
        st.error("AI Agent could not be initialized. Please check the logs and configuration.")

    # Sidebar - Conversation management
    st.sidebar.title("💬 Chat Management")
    
    # New conversation button
    if st.sidebar.button("➕ New Chat", use_container_width=True, type="primary", key="new_conv_btn"):
        start_new_conversation()
        st.rerun()
    
    # Clear current conversation (only show if active)
    if has_active_conversation():
        if st.sidebar.button("🗑️ Clear Current", use_container_width=True, key="clear_conv_btn"):
            clear_conversation()
            st.rerun()
    
    st.sidebar.markdown("---")
    
    # Recent conversations
    if st.session_state.saved_conversations:
        st.sidebar.markdown("**📚 Recent Chats**")
        
        # Sort conversations by timestamp (newest first)
        sorted_conversations = sorted(
            st.session_state.saved_conversations.items(),
            key=lambda x: x[1]["timestamp"],
            reverse=True
        )
        
        for conv_id, conv_data in sorted_conversations:
            # Check if this conversation is being edited
            if st.session_state.editing_conversation == conv_id:
                # Edit mode: show text input and confirm/cancel buttons
                col1, col2, col3 = st.sidebar.columns([3, 1, 1])
                
                with col1:
                    new_name = st.text_input(
                        "",
                        value=conv_data["name"],
                        key=f"edit_input_{conv_id}",
                        placeholder="Enter conversation name"
                    )
                
                with col2:
                    if st.button("✓", key=f"confirm_{conv_id}", help="Save changes"):
                        if rename_conversation(conv_id, new_name):
                            st.session_state.editing_conversation = None
                            st.rerun()
                
                with col3:
                    if st.button("✗", key=f"cancel_{conv_id}", help="Cancel editing"):
                        st.session_state.editing_conversation = None
                        st.rerun()
            else:
                # Normal mode: show conversation name, edit and delete buttons
                col1, col2, col3 = st.sidebar.columns([3, 1, 1])
                
                with col1:
                    if st.button(
                        conv_data["name"], 
                        use_container_width=True, 
                        key=f"load_{conv_id}",
                        help="Click to load this conversation"
                    ):
                        load_conversation(conv_id)
                        st.rerun()
                
                with col2:
                    if st.button("📝", key=f"edit_{conv_id}", help="Rename conversation"):
                        st.session_state.editing_conversation = conv_id
                        st.rerun()
                        
                with col3:
                    if st.button("🗑️", key=f"delete_{conv_id}", help="Delete conversation"):
                        delete_conversation(conv_id)
                        st.rerun()
    
    # Current conversation status
    agent = get_vanna_agent()
    if agent:
        summary = agent.get_conversation_summary()
        if summary["total_questions"] > 0:
            st.sidebar.caption(f"💭 Current chat: {summary['total_questions']} messages")
        else:
            st.sidebar.caption("💭 No active conversation")
    
    # Main content
    st.title("ABConvert Data Query Assistant")
    
    # Display suggested questions only when no active conversation
    if not has_active_conversation():
        # Simplified header with better styling
        st.markdown("""
        <h4 style='margin-bottom: 0.5rem; color: #1f77b4; font-weight: 600;'>
            💡 Get started with these questions
        </h4>
        """, unsafe_allow_html=True)
        
        questions = generate_questions_cached()
        if questions:
            # Add custom CSS for left-aligned buttons that fill container width
            st.markdown("""
            <style>
            .stButton > button {
                text-align: left !important;
                justify-content: flex-start !important;
                padding-left: 1rem !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Create buttons that fill container width but with left-aligned text
            for i, question_text in enumerate(questions):
                button_key = f"suggest_{i}"
                if st.button(
                    question_text, 
                    key=button_key,
                    use_container_width=True
                ):
                    # Use session state to track the suggested question
                    st.session_state["pending_question"] = question_text
                    st.rerun()
        else:
            st.caption("No suggested questions available at the moment.")
        
        st.markdown("---")
    
    # Display conversation history
    display_conversation_history()
    
    # Process any pending suggested question
    if "pending_question" in st.session_state:
        pending_q = st.session_state["pending_question"]
        del st.session_state["pending_question"]  # Remove to avoid reprocessing
        process_question(pending_q)
    
    # Chat input
    user_input = st.chat_input("Ask me anything about your data...")
    
    # Process user input
    if user_input:
        process_question(user_input)

if __name__ == "__main__":
    main() 