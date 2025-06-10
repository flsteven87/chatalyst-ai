"""
Refactored Vanna AI integration module for natural language to SQL conversion.
"""
import pandas as pd
import traceback
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from vanna.openai.openai_chat import OpenAI_Chat
from vanna.chromadb.chromadb_vector import ChromaDB_VectorStore

from config.settings import VANNA_CONFIG
from database.connector import PostgreSQLConnector
from training.training_loader import TrainingDataLoader
from database.schema_manager import SchemaManager
from validation.sql_validator import SQLValidator
from training.prompt_manager import PromptManager

logger = logging.getLogger(__name__)


class MyVanna(ChromaDB_VectorStore, OpenAI_Chat):
    """
    Custom Vanna class combining ChromaDB for vector storage and OpenAI for chat.
    """
    def __init__(self, config=None):
        # Extract ChromaDB specific config
        chroma_config = {}
        if config and config.get("persist_directory"):
            chroma_config["path"] = config["persist_directory"]
        
        ChromaDB_VectorStore.__init__(self, config=chroma_config)
        OpenAI_Chat.__init__(self, config=config)


class VannaAgent:
    """
    Simplified Vanna AI agent for converting natural language to SQL queries.
    
    This version separates concerns into specialized components:
    - SchemaManager: Handles database schema and DDL generation
    - SQLValidator: Validates generated SQL queries
    - PromptManager: Manages system prompts and instructions
    - TrainingDataLoader: Loads training data from files
    
    Features:
    - Conversational context: Uses vanna.ai's generate_rewritten_question for dialog
    - Session management: Maintains conversation history for context
    """
    
    def __init__(self, config=None, db_connector=None, training_data_path=None):
        """
        Initialize the Vanna AI agent.
        
        Args:
            config (dict, optional): Vanna configuration
            db_connector (PostgreSQLConnector, optional): Database connector
            training_data_path (str, optional): Path to training data directory
        """
        self.config = config or VANNA_CONFIG
        self.db_connector = db_connector or PostgreSQLConnector()
        
        # Initialize specialized components
        self.schema_manager = SchemaManager(self.db_connector)
        self.sql_validator = SQLValidator(self.schema_manager)
        self.training_loader = TrainingDataLoader(training_data_path)
        
        # Core Vanna instance
        self.vanna_instance = None
        self.initialized = False
        
        # Conversation management
        self.conversation_history: List[Dict[str, Any]] = []
        self.max_history_length = 20  # Limit history to prevent memory issues
        
        # Validate API key
        if not self.config.get("api_key"):
            logger.warning("No OpenAI API key provided. Please set VANNA_API_KEY in .env file.")

    def clear_conversation(self) -> None:
        """
        Clear the conversation history.
        """
        self.conversation_history.clear()
        logger.info("Conversation history cleared")

    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current conversation.
        
        Returns:
            dict: Summary with total questions and last question timestamp
        """
        if not self.conversation_history:
            return {"total_questions": 0, "last_question_time": None}
        
        questions = [item for item in self.conversation_history if item.get("type") == "question"]
        return {
            "total_questions": len(questions),
            "last_question_time": questions[-1].get("timestamp") if questions else None
        }

    def _get_last_question(self) -> Optional[str]:
        """
        Get the last question from conversation history.
        
        Returns:
            str: The last question or None if no previous questions
        """
        # Search backwards through history for the most recent question
        for item in reversed(self.conversation_history):
            if item.get("type") == "question" and item.get("processed_question"):
                return item["processed_question"]
        return None

    def _add_to_conversation_history(self, entry: Dict[str, Any]) -> None:
        """
        Add an entry to conversation history with automatic cleanup.
        
        Args:
            entry: Dictionary containing conversation entry data
        """
        entry["timestamp"] = datetime.now()
        self.conversation_history.append(entry)
        
        # Cleanup old entries if history gets too long
        if len(self.conversation_history) > self.max_history_length:
            # Keep the most recent entries
            self.conversation_history = self.conversation_history[-self.max_history_length:]
            logger.debug("Conversation history cleaned up")

    def _rewrite_question_with_context(self, question: str) -> str:
        """
        Rewrite question using conversation context via vanna's generate_rewritten_question.
        
        Args:
            question: The new question to potentially rewrite
            
        Returns:
            str: The rewritten question or original if no context/rewriting needed
        """
        last_question = self._get_last_question()
        if not last_question:
            return question
            
        try:
            logger.info(f"Attempting to rewrite question with context. Last: '{last_question}', New: '{question}'")
            
            rewritten_question = self.vanna_instance.generate_rewritten_question(
                last_question=last_question,
                new_question=question
            )
            
            # Only use rewritten question if it's significantly different and meaningful
            if rewritten_question and rewritten_question.strip() != question.strip():
                logger.info(f"Question rewritten: '{question}' -> '{rewritten_question}'")
                return rewritten_question.strip()
            else:
                logger.info("Question rewriting returned same or empty result, using original")
                return question
                
        except Exception as e:
            logger.warning(f"Error rewriting question with context: {e}")
            # Fall back to original question if rewriting fails
            return question
    
    def initialize(self) -> bool:
        """
        Initialize the Vanna AI instance and setup with database schema.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            if not self._validate_config():
                return False
            
            if not self._create_vanna_instance():
                return False
            
            if not self._connect_database():
                return False
            
            self._train_system()
            
            self.initialized = True
            logger.info("Vanna AI agent successfully initialized")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Vanna AI agent: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def ask(self, question: str, use_conversation_context: bool = False) -> dict:
        """
        Process a natural language question and generate SQL.
        
        Args:
            question: Natural language question about the data
            use_conversation_context: Whether to use conversation context for question rewriting
            
        Returns:
            dict: Dictionary with generated SQL or error information
        """
        if not self.initialized:
            if not self.initialize():
                return {"error": "Vanna AI agent not initialized", "question": question}
        
        try:
            if not self._validate_question(question):
                return {"error": "Invalid question", "question": str(question)}
            
            logger.info(f"Processing question: {question}")
            
            # Apply conversation context if requested
            processed_question = question
            if use_conversation_context:
                processed_question = self._rewrite_question_with_context(question)
            
            # Generate SQL using the processed question
            generated_sql = self.vanna_instance.generate_sql(processed_question)
            if not generated_sql:
                return {"error": "Failed to generate SQL", "question": question}
            
            # Validate SQL
            is_valid, validation_error = self.sql_validator.validate_sql(generated_sql, processed_question)
            if not is_valid:
                logger.warning(f"Generated invalid SQL: {validation_error}")
                return {
                    "error": f"生成的SQL無效: {validation_error}. 請重新描述您的問題或檢查欄位名稱。",
                    "question": question,
                    "processed_question": processed_question,
                    "sql": generated_sql
                }
            
            # Add to conversation history
            self._add_to_conversation_history({
                "type": "question",
                "original_question": question,
                "processed_question": processed_question,
                "sql": generated_sql,
                "context_used": use_conversation_context
            })
            
            result = {
                "question": question,
                "sql": generated_sql
            }
            
            # Include processed question in result if it was rewritten
            if processed_question != question:
                result["processed_question"] = processed_question
                result["context_used"] = True
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            logger.debug(traceback.format_exc())
            return {"error": str(e), "question": question}
    
    def execute(self, question: str, use_conversation_context: bool = False) -> dict:
        """
        Process a question, generate SQL, and execute it against the database.
        
        Args:
            question: Natural language question about the data
            use_conversation_context: Whether to use conversation context for question rewriting
            
        Returns:
            dict: Dictionary with question, SQL, and results
        """
        # Generate SQL from question
        result = self.ask(question, use_conversation_context=use_conversation_context)
        
        if "error" in result:
            return result
        
        try:
            sql = result["sql"].strip()
            if not sql:
                return {
                    "error": "Empty SQL generated",
                    "question": question,
                    "sql": sql,
                    "success": False
                }
            
            logger.info(f"Executing SQL: {sql}")
            df = self.db_connector.execute_query(sql)
            
            result["results"] = df.to_dict('records') if df is not None and not df.empty else []
            result["success"] = df is not None
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            logger.debug(traceback.format_exc())
            result["error"] = str(e)
            result["success"] = False
            return result
    
    def train_with_examples(self, examples=None, reload_training_data=False) -> bool:
        """
        Train Vanna with example question-SQL pairs.
        
        Args:
            examples: List of dicts with 'question' and 'sql' keys
            reload_training_data: Whether to reload training data from files
                
        Returns:
            bool: True if training successful, False otherwise
        """
        if not self.initialized:
            if not self.initialize():
                logger.error("Cannot train: Vanna AI agent not initialized")
                return False
        
        try:
            if reload_training_data or examples is None:
                self._load_training_data()
                if examples is None:
                    return True
            
            # Train with provided examples
            for example in examples:
                if 'question' in example and 'sql' in example:
                    self.vanna_instance.train(question=example['question'], sql=example['sql'])
                    logger.debug(f"Trained with example: {example['question'][:50]}...")
            
            logger.info(f"Successfully trained with {len(examples)} examples")
            return True
            
        except Exception as e:
            logger.error(f"Error training with examples: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def _validate_config(self) -> bool:
        """Validate Vanna configuration."""
        if not self.config.get("api_key"):
            logger.error("OpenAI API key not provided in configuration")
            return False
        return True
    
    def _create_vanna_instance(self) -> bool:
        """Create and configure Vanna instance."""
        try:
            self.vanna_instance = MyVanna(config=self.config)
            
            logger.info("Vanna instance created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating Vanna instance: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def _connect_database(self) -> bool:
        """Connect to database and set up Vanna connection."""
        try:
            if not self.db_connector.connect():
                logger.error("Failed to connect to database")
                return False
            
            # Connect Vanna to database
            self.vanna_instance.connect_to_postgres(
                host=self.db_connector.config_kwargs.get('host'),
                dbname=self.db_connector.config_kwargs.get('database') or self.db_connector.config_kwargs.get('dbname'),
                user=self.db_connector.config_kwargs.get('user'),
                password=self.db_connector.config_kwargs.get('password'),
                port=self.db_connector.config_kwargs.get('port')
            )
            
            logger.info("Database connection established")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def _train_system(self):
        """Train the system with essential prompts and schema only."""
        try:
            # Check if we should skip training (embeddings already exist)
            if not self._should_retrain():
                logger.info("Skipping training - embeddings already exist and force_retrain=False")
                return
                
            # Train with essential prompts and schema
            self._train_with_essential_prompts()
            self._train_with_expanded_schema()
            
            # Only load training data if configured to do so
            if self.config.get("load_training_on_startup", True):
                self._load_critical_training_data()
            
            logger.info("Essential system training completed")
            
        except Exception as e:
            logger.error(f"Error during system training: {e}")
            logger.debug(traceback.format_exc())
    
    def _should_retrain(self) -> bool:
        """Check if we should retrain based on configuration and existing embeddings."""
        # Always retrain if explicitly requested
        if self.config.get("force_retrain", False):
            logger.info("Force retrain enabled - will reload all training data")
            return True
        
        # Check if embeddings directory exists and has content
        persist_dir = self.config.get("persist_directory", "data/vanna_embeddings")
        if os.path.exists(persist_dir) and os.listdir(persist_dir):
            logger.info(f"Found existing embeddings in {persist_dir}")
            return False
        
        logger.info(f"No existing embeddings found in {persist_dir} - will train")
        return True
    
    def _train_with_essential_prompts(self):
        """Train with only essential prompts to avoid token overflow."""
        try:
            prompt_manager = PromptManager()
            
            # Train with all essential prompts for better guidance
            essential_prompt = prompt_manager.get_system_prompt()
            schema_enforcement = prompt_manager.get_schema_enforcement_prompt()
            
            # Combine prompts for comprehensive guidance
            combined_prompt = f"{essential_prompt}\n\n{schema_enforcement}"
            
            # 🔇 Comprehensive logging suppression for vanna and all dependencies
            import sys
            from io import StringIO
            
            # Store original stdout and loggers
            original_stdout = sys.stdout
            original_loggers = {}
            
            # List of all possible vanna-related loggers to suppress
            logger_names = ['vanna', 'chromadb', 'openai', 'httpx', 'httpcore', '__main__']
            
            for logger_name in logger_names:
                target_logger = logging.getLogger(logger_name)
                original_loggers[logger_name] = target_logger.level
                target_logger.setLevel(logging.CRITICAL)  # Suppress almost everything
            
            # Redirect stdout to catch print statements
            captured_output = StringIO()
            sys.stdout = captured_output
            
            self.vanna_instance.train(documentation=combined_prompt)
            
            # 🔊 Restore original stdout and log levels
            sys.stdout = original_stdout
            for logger_name, original_level in original_loggers.items():
                logging.getLogger(logger_name).setLevel(original_level)
            
            # 🎨 Beautiful system prompt display without timestamp clutter
            print("\n" + "📋 System Prompt Successfully Loaded:".center(80))
            print("=" * 80)
            for line in essential_prompt.split('\n'):
                if line.strip():
                    print(f"   {line}")
            print("=" * 80)
            logger.info("✅ Essential prompt training completed")
            
        except Exception as e:
            logger.error(f"Error training with essential prompts: {e}")
            logger.debug(traceback.format_exc())
    
    def _train_with_expanded_schema(self):
        """Train with expanded core database schema including event tables."""
        try:
            schema_info = self.schema_manager.get_schema_info()
            
            # Expand core tables to include event tables for conversion calculations
            core_tables = [
                'experiments', 'experiment_groups', 'experiment_daily_metrics',  # 核心實驗表格
                'shops'  # 商店資訊
            ]
            
            # 🔇 Comprehensive logging suppression for vanna and all dependencies
            import sys
            from io import StringIO
            
            # Store original stdout and loggers
            original_stdout = sys.stdout
            original_loggers = {}
            
            # List of all possible vanna-related loggers to suppress
            logger_names = ['vanna', 'chromadb', 'openai', 'httpx', 'httpcore', '__main__']
            
            for logger_name in logger_names:
                target_logger = logging.getLogger(logger_name)
                original_loggers[logger_name] = target_logger.level
                target_logger.setLevel(logging.CRITICAL)  # Suppress almost everything
            
            # Redirect stdout to catch print statements
            captured_output = StringIO()
            sys.stdout = captured_output
            
            loaded_tables = []
            for table_name, columns in schema_info.items():
                if table_name in core_tables:
                    # Generate enhanced DDL with comments (but don't log the full DDL)
                    ddl = self.schema_manager.generate_enhanced_ddl(table_name, columns)
                    self.vanna_instance.train(ddl=ddl)
                    loaded_tables.append(table_name)
            
            # 🔊 Restore original stdout and log levels
            sys.stdout = original_stdout
            for logger_name, original_level in original_loggers.items():
                logging.getLogger(logger_name).setLevel(original_level)
            
            # 📊 Concise DDL logging - only show which tables were loaded
            logger.info("📊 Database Schema Successfully Loaded:")
            logger.info("   Tables embedded:")
            for table in loaded_tables:
                column_count = len(schema_info[table])
                logger.info(f"     ✅ {table} ({column_count} columns)")
            logger.info(f"✅ Schema training completed for {len(loaded_tables)} core tables")
            
        except Exception as e:
            logger.error(f"Error training with expanded schema: {e}")
            logger.debug(traceback.format_exc())
    
    def _load_critical_training_data(self):
        """Load only critical training data to avoid token overflow."""
        try:
            # Load only the most important sample queries
            queries = self.training_loader.load_sample_queries()
            
            # Filter for conversion rate and core functionality examples
            critical_queries = []
            for query in queries:
                question = query.get('question', '').lower()
                # Include queries that demonstrate conversion rate calculations
                if any(keyword in question for keyword in ['轉換率', 'conversion', '價格測試', 'price-test']):
                    critical_queries.append(query)
            
            # 🔇 Comprehensive logging suppression for vanna and all dependencies
            import sys
            from io import StringIO
            
            # Store original stdout and loggers
            original_stdout = sys.stdout
            original_loggers = {}
            
            # List of all possible vanna-related loggers to suppress
            logger_names = ['vanna', 'chromadb', 'openai', 'httpx', 'httpcore', '__main__']
            
            for logger_name in logger_names:
                target_logger = logging.getLogger(logger_name)
                original_loggers[logger_name] = target_logger.level
                target_logger.setLevel(logging.CRITICAL)  # Suppress almost everything
            
            # Redirect stdout to catch print statements
            captured_output = StringIO()
            sys.stdout = captured_output
            
            # Limit to prevent token overflow
            for query in critical_queries[:10]:  # Only top 10 critical queries
                self.vanna_instance.train(question=query['question'], sql=query['sql'])
            
            # 🔊 Restore original stdout and log levels
            sys.stdout = original_stdout
            for logger_name, original_level in original_loggers.items():
                logging.getLogger(logger_name).setLevel(original_level)
            
            # 📚 Organized training data logging
            logger.info("📚 Critical Training Data Successfully Loaded:")
            logger.info(f"   📝 Sample queries loaded: {len(critical_queries)} (filtered from {len(queries)} total)")
            logger.info("   🎯 Focus areas: conversion rate calculations, price testing")
            logger.info("✅ Critical training data loading completed")
            
        except Exception as e:
            logger.error(f"Error loading critical training data: {e}")
            logger.debug(traceback.format_exc())
    
    def _load_training_data(self):
        """Load and train with sample queries and documents."""
        try:
            # Load sample queries
            queries = self.training_loader.load_sample_queries()
            for query in queries:
                self.vanna_instance.train(question=query['question'], sql=query['sql'])
            
            # Load documents
            documents = self.training_loader.load_documents()
            for doc in documents:
                self.vanna_instance.train(documentation=doc)
            
            logger.info(f"Training data loaded: {len(queries)} queries, {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            logger.debug(traceback.format_exc())
    
    def _validate_question(self, question) -> bool:
        """Validate input question."""
        if not question or not isinstance(question, str) or not question.strip():
            return False
        return True 