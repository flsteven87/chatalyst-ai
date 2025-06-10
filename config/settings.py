import os
from dotenv import load_dotenv
import logging

# 根據環境變數決定要載入的環境配置檔案
ENV = os.getenv("ENV", "development")  # 預設為開發環境

# 根據環境類型決定環境檔案名稱
if ENV == "production":
    env_filename = ".env.prod"
elif ENV == "test":
    env_filename = ".env.test"
else:
    env_filename = ".env"  # 開發環境或其他情況

# Load environment variables from the appropriate .env file
# Assuming env file is in the project root, which is two levels up from config/
dotenv_path = os.path.join(os.path.dirname(__file__), "..", env_filename)
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print(f"✅ Loaded environment variables from {dotenv_path} (ENV={ENV})")
elif os.path.exists(os.path.join(os.getcwd(), env_filename)):
    # Fallback if running from project root directly for some reason
    load_dotenv(os.path.join(os.getcwd(), env_filename))
    print(f"✅ Loaded environment variables from current working directory {env_filename} (ENV={ENV})")
else:
    # 如果指定的環境檔案不存在，嘗試載入預設的 .env
    fallback_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(fallback_path):
        load_dotenv(dotenv_path=fallback_path)
        print(f"⚠️  Specified {env_filename} not found, loaded fallback .env file (ENV={ENV})")
    else:
        print(f"❌ Warning: Neither {env_filename} nor .env file found (ENV={ENV})")

logger = logging.getLogger(__name__)

# Vanna AI Configuration
VANNA_API_KEY = os.getenv("VANNA_API_KEY")
VANNA_MODEL_NAME = os.getenv("VANNA_MODEL", "gpt-4o-mini") # Default model
VANNA_PERSIST_DIR = os.getenv("VANNA_PERSIST_DIR", "data/vanna_embeddings") # Default persist directory

# Training control parameters
VANNA_FORCE_RETRAIN = os.getenv("VANNA_FORCE_RETRAIN", "False").lower() == "true"
VANNA_LOAD_TRAINING_ON_STARTUP = os.getenv("VANNA_LOAD_TRAINING_ON_STARTUP", "True").lower() == "true"
VANNA_TRAINING_BATCH_SIZE = int(os.getenv("VANNA_TRAINING_BATCH_SIZE", "50"))

# Models that don't support temperature parameter
MODELS_WITHOUT_TEMPERATURE = [
    "o1-preview", "o1-mini", "o3-mini", "o3-mini-2025-01-31", 
    "o1", "o1-2024-12-17", "o3-mini-2024-12-17"
]

# Define VANNA_CONFIG immediately after fetching its components
VANNA_CONFIG = {
    "api_key": VANNA_API_KEY,
    "model": VANNA_MODEL_NAME,
    "persist_directory": VANNA_PERSIST_DIR,
    # Training control flags
    "force_retrain": VANNA_FORCE_RETRAIN,
    "load_training_on_startup": VANNA_LOAD_TRAINING_ON_STARTUP,
    "training_batch_size": VANNA_TRAINING_BATCH_SIZE,
    # Add other Vanna specific configurations here if needed
    # e.g., "allow_llm_to_see_data": True (This is often set during Vanna instance creation)
}

# Only add temperature if the model supports it
if VANNA_MODEL_NAME not in MODELS_WITHOUT_TEMPERATURE:
    VANNA_CONFIG["temperature"] = float(os.getenv("VANNA_TEMPERATURE", "0.3"))
else:
    # For models like o1/o3, set temperature to 1 (the only accepted value)
    VANNA_CONFIG["temperature"] = 1

# Now, log a warning if the API key wasn't loaded.
if not VANNA_API_KEY:
    logger.warning(
        'VANNA_API_KEY is not set in the environment variables. ' 
        'Vanna AI functionality will be limited or disabled.'
    )

# Database Configuration (example, adjust as per your needs)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE", "abconvert")
POSTGRES_USER = os.getenv("POSTGRES_USER", "abconvert")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "abconvert123")

DATABASE_CONFIG = {
    "host": POSTGRES_HOST,
    "port": POSTGRES_PORT,
    "database": POSTGRES_DATABASE,
    "user": POSTGRES_USER,
    "password": POSTGRES_PASSWORD,
}

# Application Configuration
DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

if __name__ == '__main__':
    # This block can be used for testing the settings loading
    print(f"Current Environment: {ENV}")
    print(f"Environment File: {env_filename}")
    print(f"Loaded VANNA_CONFIG: {VANNA_CONFIG}")
    print(f"Loaded DATABASE_CONFIG: {DATABASE_CONFIG}")
    print(f"Debug Mode: {DEBUG_MODE}")
    print(f"Log Level: {LOG_LEVEL}") 