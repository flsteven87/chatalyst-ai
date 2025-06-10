"""
Application helper functions with caching for the Streamlit interface.
This module acts as an intermediary between the Streamlit UI and the Vanna Agent,
and includes UI-specific data processing and generation logic.
"""
import pandas as pd
import streamlit as st
import traceback
import logging
import hashlib
import json

from agent.vanna_agent import VannaAgent

logger = logging.getLogger(__name__)

# Initialize Vanna Agent
def get_vanna_agent():
    """
    Gets the initialized VannaAgent instance for the current session.
    Each session has its own independent agent to prevent cross-user contamination.
    """
    # Use session state to store agent per user session instead of global caching
    if "vanna_agent" not in st.session_state:
        st.session_state.vanna_agent = None
    
    # Return existing agent if already initialized for this session
    if st.session_state.vanna_agent is not None:
        return st.session_state.vanna_agent
    
    # Initialize new agent for this session
    agent = VannaAgent()
    if not agent.initialized:
        logger.info("VannaAgent not initialized, attempting to initialize...")
        success = agent.initialize()
        if success:
            logger.info("VannaAgent initialized successfully with training data loaded.")
        else:
            logger.error("Failed to initialize VannaAgent.")
            st.error("Core AI agent initialization failed. Please check logs and configuration.")
            return None
    
    # Store in session state for this user
    st.session_state.vanna_agent = agent
    logger.info(f"Created new VannaAgent instance for session: {st.session_state.get('session_id', 'unknown')}")
    return agent

# Generate suggested questions
@st.cache_data(ttl=3600, show_spinner=False)
@st.cache_data(ttl=3600)
def generate_questions_cached():
    """
    Generates a list of suggested questions with progressive difficulty.
    
    Returns:
        list: Five suggested questions from basic to advanced level
    """
    questions = [
        # Level 1: Database exploration
        "What tables are available in this database?",
        
        # Level 2: Data overview
        "Show me the row count for each table in the database",
        
        # Level 3: Data freshness check
        "For each table, show me the most recent record date if there are any date/timestamp columns",
        
        # Level 4: Basic data analysis
        "Show me the top 10 records from the largest table by row count",
        
        # Level 5: Schema exploration
        "What are the column names and data types for all tables in the database?"
    ]
    return questions

# Generate SQL query
def generate_sql_cached(question: str, use_conversation_context: bool = True):
    """
    Generates SQL query from a natural language question.
    
    Args:
        question: Natural language question
        use_conversation_context: Whether to use conversation context for better understanding (default: True)
    
    Returns:
        str: Generated SQL query or error message
    """
    try:
        agent = get_vanna_agent()
        if not agent: # Check if agent initialization failed
            return None

        result = agent.ask(question, use_conversation_context=use_conversation_context)
        if result and "error" in result:
            logger.error(f"SQL generation error: {result['error']}")
            if "Vanna AI agent not initialized" in result['error']:
                return "AI agent is not ready. Please try again later or contact administrator."
            return f"Unable to generate SQL: {result['error']}"
        
        sql_query = result.get("sql")
        if not sql_query:
            logger.warning(f"Generated SQL is empty for question: {question}")
            return "Unable to generate SQL query for this question."
        
        # Log context usage for debugging
        if result.get("context_used"):
            logger.info(f"Question rewritten using context: '{question}' -> '{result.get('processed_question')}'")
            
        return sql_query

    except Exception as e:
        logger.error(f"Error generating SQL: {e}\n{traceback.format_exc()}")
        return f"Unexpected error occurred while generating SQL: {e}"

# Validate SQL
@st.cache_data(ttl=3600)
def is_sql_valid_cached(sql: str) -> bool:
    """Checks if the SQL is valid (basic check)."""
    if not isinstance(sql, str) or not sql.strip():
        return False
    # Check for error messages instead of SQL
    error_indicators = ["the ", "sorry", "error", "unable", "failed", "cannot"]
    if any(sql.lower().startswith(indicator) for indicator in error_indicators):
        return False
    return True

# Run SQL query (no caching due to JSONB columns)
def run_sql_cached(sql: str) -> pd.DataFrame | None:
    """Executes SQL query and returns results as a DataFrame."""
    try:
        agent = get_vanna_agent()
        if not agent or not agent.db_connector:
            logger.error("Vanna agent or DB connector not available for executing SQL.")
            return None
        
        db_connector = agent.db_connector
        
        if not db_connector.connection or db_connector.connection.closed:
            logger.info("DB connection closed, attempting to reconnect.")
            if not db_connector.connect():
                logger.error("Failed to reconnect to the database.")
                return None
            
        logger.info(f"Executing SQL: {sql}")
        df = db_connector.execute_query(sql)
        
        # Convert JSONB/dict columns to strings to avoid caching issues
        if df is not None and not df.empty:
            for col in df.columns:
                if df[col].dtype == 'object':
                    # Check if any values in this column are dicts
                    sample_vals = df[col].dropna().head(3)
                    if not sample_vals.empty and any(isinstance(val, dict) for val in sample_vals):
                        logger.info(f"Converting JSONB column '{col}' to string for caching compatibility")
                        df[col] = df[col].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, dict) else x)
        
        return df
    except Exception as e:
        logger.error(f"Error executing SQL: {e}\n{traceback.format_exc()}")
        return None 