"""
Utility functions for the Data Insights App.
Includes logging setup and helper functions.
"""
import logging
import sys
from datetime import datetime
from typing import Any, Dict, List

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def setup_logger(name: str) -> logging.Logger:
    """
    Creates and returns a logger with the specified name.
    Inputs: name (string)
    Outputs: Logger instance
    """
    return logging.getLogger(name)


def log_function_call(function_name: str, parameters: Dict[str, Any]) -> None:
    """
    Logs a function call with its parameters.
    Inputs: function_name (string), parameters (dict)
    Outputs: None
    """
    logger.info(f"Function called: {function_name}")
    logger.info(f"Parameters: {parameters}")


def log_query_result(result_summary: str) -> None:
    """
    Logs a summary of query results (not full data).
    Inputs: result_summary (string)
    Outputs: None
    """
    logger.info(f"Query result: {result_summary}")


def log_safety_block(operation: str, reason: str) -> None:
    """
    Logs when a dangerous operation is blocked.
    Inputs: operation (string), reason (string)
    Outputs: None
    """
    logger.warning(f"BLOCKED OPERATION: {operation}")
    logger.warning(f"Reason: {reason}")


def format_price(price: float) -> str:
    """
    Formats price as USD currency.
    Inputs: price (float)
    Outputs: formatted string
    """
    return f"${price:,.2f}"


def format_timestamp() -> str:
    """
    Returns current timestamp as formatted string.
    Inputs: None
    Outputs: timestamp string
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def truncate_results(data: List[Dict], max_items: int = 20) -> List[Dict]:
    """
    Truncates results to prevent sending too much data to LLM.
    Inputs: data (list of dicts), max_items (int)
    Outputs: truncated list
    """
    if len(data) > max_items:
        logger.info(f"Truncating results from {len(data)} to {max_items} items")
        return data[:max_items]
    return data

