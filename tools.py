"""
Function tools for the AI agent.
Defines tools that the agent can use to query and analyze student performance data.
"""
from typing import Dict, List, Any, Optional
from database import DataManager
from utils import setup_logger, log_function_call
from config import MAX_RESULTS_TO_LLM

logger = setup_logger(__name__)


class AgentTools:
    """
    Collection of tools available to the AI agent for student performance data operations.
    """
    
    def __init__(self, data_manager: DataManager):
        """
        Initializes tools with DataManager instance.
        Inputs: data_manager (DataManager)
        Outputs: None
        """
        self.data_manager = data_manager
        logger.info("AgentTools initialized")
    
    def search_students_by_criteria(
        self,
        gender: Optional[str] = None,
        race_ethnicity: Optional[str] = None,
        parental_education: Optional[str] = None,
        lunch: Optional[str] = None,
        test_preparation: Optional[str] = None,
        min_math_score: Optional[int] = None,
        max_math_score: Optional[int] = None,
        min_reading_score: Optional[int] = None,
        max_reading_score: Optional[int] = None,
        min_writing_score: Optional[int] = None,
        max_writing_score: Optional[int] = None,
        limit: int = MAX_RESULTS_TO_LLM
    ) -> Dict[str, Any]:
        """
        Searches for students matching specified criteria.
        Inputs: gender, race_ethnicity, parental_education, lunch, test_preparation, score ranges, limit
        Outputs: dictionary with results and metadata
        """
        parameters = {
            "gender": gender,
            "race_ethnicity": race_ethnicity,
            "parental_education": parental_education,
            "lunch": lunch,
            "test_preparation": test_preparation,
            "min_math_score": min_math_score,
            "max_math_score": max_math_score,
            "min_reading_score": min_reading_score,
            "max_reading_score": max_reading_score,
            "min_writing_score": min_writing_score,
            "max_writing_score": max_writing_score,
            "limit": limit
        }
        log_function_call("search_students_by_criteria", parameters)
        
        # Build filters
        filters = {}
        
        if gender:
            filters["gender"] = gender
        
        if race_ethnicity:
            filters["race/ethnicity"] = race_ethnicity
        
        if parental_education:
            filters["parental level of education"] = parental_education
        
        if lunch:
            filters["lunch"] = lunch
        
        if test_preparation:
            filters["test preparation course"] = test_preparation
        
        if min_math_score is not None or max_math_score is not None:
            math_filter = {}
            if min_math_score is not None:
                math_filter["min"] = min_math_score
            if max_math_score is not None:
                math_filter["max"] = max_math_score
            filters["math score"] = math_filter
        
        if min_reading_score is not None or max_reading_score is not None:
            reading_filter = {}
            if min_reading_score is not None:
                reading_filter["min"] = min_reading_score
            if max_reading_score is not None:
                reading_filter["max"] = max_reading_score
            filters["reading score"] = reading_filter
        
        if min_writing_score is not None or max_writing_score is not None:
            writing_filter = {}
            if min_writing_score is not None:
                writing_filter["min"] = min_writing_score
            if max_writing_score is not None:
                writing_filter["max"] = max_writing_score
            filters["writing score"] = writing_filter
        
        # Get filtered results
        results = self.data_manager.filter_data(filters, limit=limit)
        
        return {
            "success": True,
            "count": len(results),
            "results": results,
            "truncated": len(results) >= limit
        }
    
    def get_aggregated_statistics(
        self,
        group_by: str,
        metric: str = "math score",
        aggregation: str = "mean"
    ) -> Dict[str, Any]:
        """
        Gets aggregated statistics grouped by a specific column.
        Inputs: group_by (e.g., 'gender', 'race/ethnicity', 'parental level of education'), 
                metric (e.g., 'math score', 'reading score', 'writing score'), 
                aggregation ('mean', 'sum', 'count', 'min', 'max')
        Outputs: dictionary with aggregated results
        """
        parameters = {
            "group_by": group_by,
            "metric": metric,
            "aggregation": aggregation
        }
        log_function_call("get_aggregated_statistics", parameters)
        
        results = self.data_manager.aggregate_data(group_by, metric, aggregation)
        
        return {
            "success": True,
            "count": len(results),
            "group_by": group_by,
            "metric": metric,
            "aggregation": aggregation,
            "results": results
        }
    
    def get_score_analysis(
        self,
        subject: Optional[str] = None,
        gender: Optional[str] = None,
        race_ethnicity: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyzes score distribution for specified subject and optional filters.
        Inputs: subject ('math score', 'reading score', 'writing score', or None for all), 
                gender (optional), race_ethnicity (optional)
        Outputs: dictionary with score analysis
        """
        parameters = {
            "subject": subject,
            "gender": gender,
            "race_ethnicity": race_ethnicity
        }
        log_function_call("get_score_analysis", parameters)
        
        df = self.data_manager.get_dataframe()
        
        # Filter by demographics if specified
        if gender:
            df = df[df['gender'] == gender]
        
        if race_ethnicity:
            df = df[df['race/ethnicity'] == race_ethnicity]
        
        if len(df) == 0:
            return {
                "success": False,
                "error": "No data found for specified criteria"
            }
        
        analysis = {
            "success": True,
            "count": len(df)
        }
        
        # Analyze specific subject or all subjects
        subjects_to_analyze = []
        if subject:
            if subject in df.columns:
                subjects_to_analyze = [subject]
            else:
                return {
                    "success": False,
                    "error": f"Subject '{subject}' not found in dataset"
                }
        else:
            # Analyze all score columns
            subjects_to_analyze = ['math score', 'reading score', 'writing score']
        
        for subj in subjects_to_analyze:
            if subj in df.columns:
                subj_key = subj.replace(' ', '_')
                analysis[f"{subj_key}_avg"] = float(df[subj].mean())
                analysis[f"{subj_key}_min"] = float(df[subj].min())
                analysis[f"{subj_key}_max"] = float(df[subj].max())
                analysis[f"{subj_key}_median"] = float(df[subj].median())
                analysis[f"{subj_key}_std"] = float(df[subj].std())
                analysis[f"{subj_key}_percentile_25"] = float(df[subj].quantile(0.25))
                analysis[f"{subj_key}_percentile_75"] = float(df[subj].quantile(0.75))
        
        logger.info(f"Score analysis completed for {len(subjects_to_analyze)} subject(s)")
        
        return analysis
    
    def get_demographic_breakdown(self, field: str) -> Dict[str, Any]:
        """
        Returns unique values and counts for a demographic field.
        Inputs: field (e.g., 'gender', 'race/ethnicity', 'parental level of education', 'lunch', 'test preparation course')
        Outputs: dictionary with breakdown
        """
        log_function_call("get_demographic_breakdown", {"field": field})
        
        df = self.data_manager.get_dataframe()
        
        if field not in df.columns:
            return {
                "success": False,
                "error": f"Field '{field}' not found in dataset"
            }
        
        # Get value counts
        value_counts = df[field].value_counts().to_dict()
        
        return {
            "success": True,
            "field": field,
            "breakdown": value_counts,
            "unique_count": len(value_counts)
        }
    
    def get_dataset_overview(self) -> Dict[str, Any]:
        """
        Returns overview statistics about the student performance dataset.
        Inputs: None
        Outputs: dictionary with dataset overview
        """
        log_function_call("get_dataset_overview", {})
        
        stats = self.data_manager.get_summary_stats()
        
        return {
            "success": True,
            "overview": stats
        }
    
    def get_top_performers(
        self, 
        subject: str = "math score",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Returns the top N students by score in specified subject.
        Inputs: subject ('math score', 'reading score', 'writing score', or 'overall'), limit (int, default 10)
        Outputs: dict with list of top performers and metadata
        """
        log_function_call("get_top_performers", {"subject": subject, "limit": limit})
        
        df = self.data_manager.get_dataframe()
        
        if subject == "overall":
            # Calculate overall average score
            if all(col in df.columns for col in ['math score', 'reading score', 'writing score']):
                df_sorted = df.copy()
                df_sorted['overall_score'] = (df_sorted['math score'] + df_sorted['reading score'] + df_sorted['writing score']) / 3
                df_sorted = df_sorted.sort_values(by='overall_score', ascending=False).head(limit)
                results = df_sorted[['gender', 'race/ethnicity', 'parental level of education', 
                                   'math score', 'reading score', 'writing score', 'overall_score']].to_dict('records')
                
                # Round overall score
                for r in results:
                    r['overall_score'] = round(r['overall_score'], 2)
                
                return {
                    "success": True,
                    "count": len(results),
                    "subject": "overall",
                    "limit": limit,
                    "results": results
                }
            else:
                return {
                    "success": False,
                    "error": "Score columns not found for overall calculation"
                }
        elif subject in df.columns:
            df_sorted = df.sort_values(by=subject, ascending=False).head(limit)
            results = df_sorted[['gender', 'race/ethnicity', 'parental level of education', 
                               'lunch', 'test preparation course', 
                               'math score', 'reading score', 'writing score']].to_dict('records')
            
            return {
                "success": True,
                "count": len(results),
                "subject": subject,
                "limit": limit,
                "results": results
            }
        else:
            return {
                "success": False,
                "error": f"Subject '{subject}' not found in dataset"
            }
    
    def get_test_prep_impact(self) -> Dict[str, Any]:
        """
        Compares performance between students who completed test prep vs those who didn't.
        Inputs: None
        Outputs: dict with comparison statistics
        """
        log_function_call("get_test_prep_impact", {})
        
        df = self.data_manager.get_dataframe()
        
        if 'test preparation course' not in df.columns:
            return {
                "success": False,
                "error": "Test preparation course column not found"
            }
        
        # Split data by test prep completion
        completed = df[df['test preparation course'] == 'completed']
        not_completed = df[df['test preparation course'] == 'none']
        
        if len(completed) == 0 or len(not_completed) == 0:
            return {
                "success": False,
                "error": "Insufficient data for comparison"
            }
        
        # Calculate statistics for each group
        analysis = {
            "success": True,
            "completed_test_prep": {
                "count": len(completed),
                "avg_math_score": float(completed['math score'].mean()) if 'math score' in completed.columns else None,
                "avg_reading_score": float(completed['reading score'].mean()) if 'reading score' in completed.columns else None,
                "avg_writing_score": float(completed['writing score'].mean()) if 'writing score' in completed.columns else None,
            },
            "not_completed_test_prep": {
                "count": len(not_completed),
                "avg_math_score": float(not_completed['math score'].mean()) if 'math score' in not_completed.columns else None,
                "avg_reading_score": float(not_completed['reading score'].mean()) if 'reading score' in not_completed.columns else None,
                "avg_writing_score": float(not_completed['writing score'].mean()) if 'writing score' in not_completed.columns else None,
            },
            "improvement": {}
        }
        
        # Calculate improvement (difference)
        if all(analysis["completed_test_prep"].get(k) and analysis["not_completed_test_prep"].get(k) 
               for k in ["avg_math_score", "avg_reading_score", "avg_writing_score"]):
            analysis["improvement"]["math"] = round(
                analysis["completed_test_prep"]["avg_math_score"] - analysis["not_completed_test_prep"]["avg_math_score"], 2
            )
            analysis["improvement"]["reading"] = round(
                analysis["completed_test_prep"]["avg_reading_score"] - analysis["not_completed_test_prep"]["avg_reading_score"], 2
            )
            analysis["improvement"]["writing"] = round(
                analysis["completed_test_prep"]["avg_writing_score"] - analysis["not_completed_test_prep"]["avg_writing_score"], 2
            )
        
        logger.info("Test prep impact analysis completed")
        
        return analysis

    def get_tool_definitions(self) -> List[Dict]:
        """
        Returns OpenAI function definitions for all available tools.
        Inputs: None
        Outputs: list of tool definitions in OpenAI format
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_students_by_criteria",
                    "description": "Search for students matching specific criteria like gender, race/ethnicity, parental education, lunch type, test preparation, and score ranges. Returns up to 'limit' matching students.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "gender": {
                                "type": "string",
                                "description": "Student gender ('male' or 'female')"
                            },
                            "race_ethnicity": {
                                "type": "string",
                                "description": "Race/ethnicity group (e.g., 'group A', 'group B', 'group C', 'group D', 'group E')"
                            },
                            "parental_education": {
                                "type": "string",
                                "description": "Parental level of education (e.g., 'bachelor\\'s degree', 'some college', 'master\\'s degree', 'associate\\'s degree', 'high school', 'some high school')"
                            },
                            "lunch": {
                                "type": "string",
                                "description": "Lunch type ('standard' or 'free/reduced')"
                            },
                            "test_preparation": {
                                "type": "string",
                                "description": "Test preparation course status ('completed' or 'none')"
                            },
                            "min_math_score": {
                                "type": "integer",
                                "description": "Minimum math score (0-100)"
                            },
                            "max_math_score": {
                                "type": "integer",
                                "description": "Maximum math score (0-100)"
                            },
                            "min_reading_score": {
                                "type": "integer",
                                "description": "Minimum reading score (0-100)"
                            },
                            "max_reading_score": {
                                "type": "integer",
                                "description": "Maximum reading score (0-100)"
                            },
                            "min_writing_score": {
                                "type": "integer",
                                "description": "Minimum writing score (0-100)"
                            },
                            "max_writing_score": {
                                "type": "integer",
                                "description": "Maximum writing score (0-100)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default 20)",
                                "default": 20
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_aggregated_statistics",
                    "description": "Get aggregated statistics by grouping student data. For example, get average math score by gender, count by parental education, etc.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "group_by": {
                                "type": "string",
                                "description": "Column to group by (e.g., 'gender', 'race/ethnicity', 'parental level of education', 'lunch', 'test preparation course')"
                            },
                            "metric": {
                                "type": "string",
                                "description": "Column to calculate metric on (e.g., 'math score', 'reading score', 'writing score')",
                                "default": "math score"
                            },
                            "aggregation": {
                                "type": "string",
                                "enum": ["mean", "sum", "count", "min", "max"],
                                "description": "Type of aggregation to perform",
                                "default": "mean"
                            }
                        },
                        "required": ["group_by"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_score_analysis",
                    "description": "Get detailed score analysis including average, min, max, median, standard deviation, and percentiles for specified subject. Can be filtered by demographics.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "subject": {
                                "type": "string",
                                "description": "Subject to analyze: 'math score', 'reading score', 'writing score', or None for all subjects"
                            },
                            "gender": {
                                "type": "string",
                                "description": "Optional: Filter by gender"
                            },
                            "race_ethnicity": {
                                "type": "string",
                                "description": "Optional: Filter by race/ethnicity group"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_demographic_breakdown",
                    "description": "Get unique values and counts for a demographic field (e.g., how many students in each gender, race group, etc.).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "field": {
                                "type": "string",
                                "description": "Demographic field to analyze: 'gender', 'race/ethnicity', 'parental level of education', 'lunch', or 'test preparation course'"
                            }
                        },
                        "required": ["field"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_dataset_overview",
                    "description": "Get overview statistics about the student performance dataset including total students, average scores, pass rate, and data structure.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_top_performers",
                    "description": "Return the top N students by score in a specified subject (math, reading, writing, or overall average).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "subject": {
                                "type": "string",
                                "description": "Subject to rank by: 'math score', 'reading score', 'writing score', or 'overall' for overall average (default 'math score')",
                                "default": "math score"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of top students to return (default 10)",
                                "default": 10
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_test_prep_impact",
                    "description": "Compare performance between students who completed test preparation course vs those who didn't, showing average scores and improvement for each subject.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]
