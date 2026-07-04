"""
Database module for the Student Performance Analytics App.
Handles data loading, querying with safety checks, and operations on pandas DataFrame.
"""
import pandas as pd
import sqlite3
from typing import Optional, Dict, List, Any
import re
from utils import setup_logger, log_safety_block
from config import CSV_FILE_PATH, DANGEROUS_SQL_KEYWORDS, MAX_RESULTS_TO_LLM

logger = setup_logger(__name__)

# Name of the queryable table exposed to the AI agent.
TABLE_NAME = "students"

# Maps the raw CSV column names (with spaces/slashes) to clean SQL-friendly
# identifiers so the LLM can write natural, unquoted SQL.
COLUMN_MAP = {
    "gender": "gender",
    "race/ethnicity": "race_ethnicity",
    "parental level of education": "parental_level_of_education",
    "lunch": "lunch",
    "test preparation course": "test_preparation_course",
    "math score": "math_score",
    "reading score": "reading_score",
    "writing score": "writing_score",
}


class DataManager:
    """
    Manages data operations with safety features.
    Loads CSV into pandas DataFrame and provides safe query interface.
    """
    
    def __init__(self, csv_path: str = CSV_FILE_PATH):
        """
        Initializes DataManager and loads CSV data.
        Inputs: csv_path (string)
        Outputs: None
        """
        self.csv_path = csv_path
        self.df: Optional[pd.DataFrame] = None
        self.conn: Optional[sqlite3.Connection] = None
        self.load_data()
        self._init_sqlite()
        logger.info(f"DataManager initialized with {len(self.df)} rows")
    
    def load_data(self) -> None:
        """
        Loads CSV file into pandas DataFrame.
        Inputs: None
        Outputs: None
        """
        try:
            self.df = pd.read_csv(self.csv_path)
            logger.info(f"Successfully loaded data from {self.csv_path}")
            logger.info(f"Columns: {list(self.df.columns)}")
            logger.info(f"Shape: {self.df.shape}")
        except FileNotFoundError:
            logger.error(f"CSV file not found: {self.csv_path}")
            raise
        except Exception as e:
            logger.error(f"Error loading CSV: {str(e)}")
            raise
    
    def _init_sqlite(self) -> None:
        """
        Loads the DataFrame into an in-memory SQLite table so the AI agent can
        run generated SELECT queries against it.
        Inputs: None
        Outputs: None
        """
        # check_same_thread=False: Streamlit caches DataManager and reuses the
        # connection across request threads.
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        df_sql = self.df.rename(columns=COLUMN_MAP)
        df_sql.to_sql(TABLE_NAME, self.conn, index=False, if_exists="replace")

        # Defense in depth: reject any write at the engine level, regardless of
        # what the LLM generates or what the keyword filter misses.
        self.conn.execute("PRAGMA query_only = ON")
        logger.info(f"Loaded data into in-memory SQLite table '{TABLE_NAME}'")

    def get_schema_description(self) -> str:
        """
        Returns a human-readable schema of the queryable table, including column
        types and sample values for categorical columns. Used to ground the AI
        agent so it generates valid SQL.
        Inputs: None
        Outputs: schema description (string)
        """
        lines = [
            f"Table: {TABLE_NAME} ({len(self.df)} rows)",
            "Columns:",
        ]
        cur = self.conn.execute(f"PRAGMA table_info({TABLE_NAME})")
        for col in cur.fetchall():
            name, col_type = col["name"], col["type"]
            line = f"  - {name} ({col_type})"
            # Add distinct values for low-cardinality categorical columns.
            if col_type.upper() in ("TEXT", ""):
                distinct = self.conn.execute(
                    f'SELECT DISTINCT "{name}" AS v FROM {TABLE_NAME} '
                    f'ORDER BY v LIMIT 10'
                ).fetchall()
                values = [str(r["v"]) for r in distinct]
                line += " — values: " + ", ".join(repr(v) for v in values)
            lines.append(line)
        return "\n".join(lines)

    def execute_query(self, sql: str, limit: int = MAX_RESULTS_TO_LLM) -> Dict[str, Any]:
        """
        Executes an AI-generated read-only SQL query against the in-memory
        database, with safety checks. Only single SELECT/WITH statements allowed.
        Inputs: sql (string), limit (int)
        Outputs: dictionary with results and metadata
        """
        logger.info(f"Executing AI-generated SQL: {sql}")

        # 1. Keyword-based safety check (blocks INSERT/UPDATE/DELETE/DROP/...).
        if not self.is_safe_operation(sql):
            return {
                "success": False,
                "error": "Query rejected: it contains a disallowed write/DDL operation. Only read-only SELECT queries are permitted.",
            }

        # 2. Structural checks: single statement, must be a SELECT/WITH.
        statement = sql.strip().rstrip(";").strip()
        if ";" in statement:
            return {
                "success": False,
                "error": "Only a single SQL statement is allowed.",
            }

        lowered = statement.lower()
        if not (lowered.startswith("select") or lowered.startswith("with")):
            return {
                "success": False,
                "error": "Only SELECT queries are allowed.",
            }

        # 3. Enforce a result cap so we never flood the LLM context.
        if not re.search(r"\blimit\b", lowered):
            statement = f"{statement} LIMIT {limit}"

        # 4. Execute (PRAGMA query_only guarantees no writes reach the data).
        try:
            cur = self.conn.execute(statement)
            rows = cur.fetchmany(limit)
            results = [dict(row) for row in rows]
            logger.info(f"SQL query returned {len(results)} rows")
            return {
                "success": True,
                "sql": statement,
                "row_count": len(results),
                "results": results,
                "truncated": len(results) >= limit,
            }
        except Exception as e:
            logger.error(f"SQL execution error: {str(e)}")
            return {
                "success": False,
                "sql": statement,
                "error": f"SQL execution error: {str(e)}",
            }

    def is_safe_operation(self, query: str) -> bool:
        """
        Checks if a query contains dangerous SQL keywords.
        Blocks all write operations (INSERT, UPDATE, DELETE, DROP, TRUNCATE, ALTER, etc.)
        Inputs: query (string)
        Outputs: boolean (True if safe, False if dangerous)
        """
        query_upper = query.upper()
        
        for keyword in DANGEROUS_SQL_KEYWORDS:
            # Check for keyword as whole word
            if re.search(rf'\b{keyword}\b', query_upper):
                log_safety_block(query, f"Contains dangerous keyword: {keyword}")
                return False
        
        logger.info("Query passed safety check")
        return True
    
    def get_dataframe(self) -> pd.DataFrame:
        """
        Returns the entire DataFrame (for internal use only, not for LLM).
        Inputs: None
        Outputs: pandas DataFrame
        """
        return self.df.copy()
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Returns summary statistics about the student performance dataset.
        Inputs: None
        Outputs: dictionary with statistics
        """
        # Calculate average scores
        avg_math = float(self.df['math score'].mean()) if 'math score' in self.df.columns else None
        avg_reading = float(self.df['reading score'].mean()) if 'reading score' in self.df.columns else None
        avg_writing = float(self.df['writing score'].mean()) if 'writing score' in self.df.columns else None
        
        # Calculate overall average
        avg_overall = None
        if all(col in self.df.columns for col in ['math score', 'reading score', 'writing score']):
            avg_overall = float((self.df['math score'] + self.df['reading score'] + self.df['writing score']).mean() / 3)
        
        # Calculate min/max scores across all subjects
        all_scores = []
        if 'math score' in self.df.columns:
            all_scores.extend(self.df['math score'].tolist())
        if 'reading score' in self.df.columns:
            all_scores.extend(self.df['reading score'].tolist())
        if 'writing score' in self.df.columns:
            all_scores.extend(self.df['writing score'].tolist())
        
        min_score = min(all_scores) if all_scores else None
        max_score = max(all_scores) if all_scores else None
        
        # Calculate pass rate (students with all scores >= 60)
        pass_rate = None
        if all(col in self.df.columns for col in ['math score', 'reading score', 'writing score']):
            passing_students = len(self.df[
                (self.df['math score'] >= 60) & 
                (self.df['reading score'] >= 60) & 
                (self.df['writing score'] >= 60)
            ])
            pass_rate = float((passing_students / len(self.df)) * 100)
        
        stats = {
            "total_rows": len(self.df),
            "total_columns": len(self.df.columns),
            "columns": list(self.df.columns),
            "numeric_columns": list(self.df.select_dtypes(include=['number']).columns),
            "categorical_columns": list(self.df.select_dtypes(include=['object']).columns),
            "missing_values": self.df.isnull().sum().to_dict(),
            "avg_math_score": avg_math,
            "avg_reading_score": avg_reading,
            "avg_writing_score": avg_writing,
            "avg_overall_score": avg_overall,
            "min_score": min_score,
            "max_score": max_score,
            "pass_rate": pass_rate,
        }
        logger.info("Generated summary statistics for student data")
        return stats
    
    def filter_data(self, filters: Dict[str, Any], limit: int = 20) -> List[Dict]:
        """
        Filters data based on provided criteria.
        Inputs: filters (dict), limit (int)
        Outputs: list of dictionaries (filtered results)
        """
        logger.info(f"Filtering data with criteria: {filters}")
        
        df_filtered = self.df.copy()
        
        # Apply filters
        for column, value in filters.items():
            if column not in df_filtered.columns:
                logger.warning(f"Column '{column}' not found in dataset")
                continue
            
            # Handle different filter types
            if isinstance(value, dict):
                # Range filter (e.g., {"min": 100, "max": 500})
                if "min" in value and "max" in value:
                    df_filtered = df_filtered[
                        (df_filtered[column] >= value["min"]) & 
                        (df_filtered[column] <= value["max"])
                    ]
                elif "min" in value:
                    df_filtered = df_filtered[df_filtered[column] >= value["min"]]
                elif "max" in value:
                    df_filtered = df_filtered[df_filtered[column] <= value["max"]]
            elif isinstance(value, list):
                # Multiple values (e.g., ["Apple", "Samsung"])
                df_filtered = df_filtered[df_filtered[column].isin(value)]
            else:
                # Single value
                df_filtered = df_filtered[df_filtered[column] == value]
        
        # Limit results
        df_filtered = df_filtered.head(limit)
        
        result = df_filtered.to_dict('records')
        logger.info(f"Filter returned {len(result)} results (limit: {limit})")
        
        return result
    
    def aggregate_data(self, group_by: str, metric: str, aggregation: str = "mean") -> List[Dict]:
        """
        Aggregates data by grouping and calculating metrics.
        Inputs: group_by (string), metric (string), aggregation (string)
        Outputs: list of dictionaries (aggregated results)
        """
        logger.info(f"Aggregating data: group_by={group_by}, metric={metric}, agg={aggregation}")
        
        if group_by not in self.df.columns:
            logger.error(f"Group by column '{group_by}' not found")
            return []
        
        if metric not in self.df.columns:
            logger.error(f"Metric column '{metric}' not found")
            return []
        
        try:
            if aggregation == "mean":
                result_df = self.df.groupby(group_by)[metric].mean().reset_index()
                result_df.columns = [group_by, f"avg_{metric}"]
            elif aggregation == "sum":
                result_df = self.df.groupby(group_by)[metric].sum().reset_index()
                result_df.columns = [group_by, f"sum_{metric}"]
            elif aggregation == "count":
                result_df = self.df.groupby(group_by)[metric].count().reset_index()
                result_df.columns = [group_by, f"count_{metric}"]
            elif aggregation == "min":
                result_df = self.df.groupby(group_by)[metric].min().reset_index()
                result_df.columns = [group_by, f"min_{metric}"]
            elif aggregation == "max":
                result_df = self.df.groupby(group_by)[metric].max().reset_index()
                result_df.columns = [group_by, f"max_{metric}"]
            else:
                logger.error(f"Unknown aggregation type: {aggregation}")
                return []
            
            result = result_df.to_dict('records')
            logger.info(f"Aggregation returned {len(result)} results")
            
            return result
        except Exception as e:
            logger.error(f"Error during aggregation: {str(e)}")
            return []
    
    def get_unique_values(self, column: str) -> List[Any]:
        """
        Returns unique values for a specific column.
        Inputs: column (string)
        Outputs: list of unique values
        """
        if column not in self.df.columns:
            logger.error(f"Column '{column}' not found")
            return []
        
        unique_vals = self.df[column].unique().tolist()
        logger.info(f"Found {len(unique_vals)} unique values for column '{column}'")
        
        return unique_vals[:50]  # Limit to 50 unique values

