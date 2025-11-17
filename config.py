"""
Configuration module for the Student Performance Analytics App.
Loads environment variables and provides configuration settings.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Trello Configuration
TRELLO_API_KEY = os.getenv("TRELLO_API_KEY", "")
TRELLO_TOKEN = os.getenv("TRELLO_TOKEN", "")
TRELLO_BOARD_ID = os.getenv("TRELLO_BOARD_ID", "")
TRELLO_LIST_ID = os.getenv("TRELLO_LIST_ID", "")

# Application Configuration
CSV_FILE_PATH = os.getenv("CSV_FILE_PATH", "StudentsPerformance.csv")
MAX_RESULTS_TO_LLM = int(os.getenv("MAX_RESULTS_TO_LLM", "20"))

# Agent Configuration
AGENT_MODEL = "gpt-5-nano"
AGENT_TEMPERATURE = 1

# Dangerous SQL keywords to block (all write operations)
DANGEROUS_SQL_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER",
    "CREATE", "REPLACE", "MERGE", "EXEC", "EXECUTE"
]

