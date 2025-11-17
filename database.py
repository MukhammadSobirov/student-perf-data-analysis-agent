"""
Database module for the Student Performance Analytics App.
Handles data loading, querying with safety checks, and operations on pandas DataFrame.
"""
import pandas as pd
from typing import Optional, Dict, List, Any
import re
from utils import setup_logger, log_safety_block
from config import CSV_FILE_PATH, DANGEROUS_SQL_KEYWORDS

logger = setup_logger(__name__)


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
        self.load_data()
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

