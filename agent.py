"""
AI Agent module with function calling capabilities.
Handles chat interactions with users for student performance analytics using OpenAI's GPT-5 model.
"""
from typing import List, Dict, Any  # cleaned imports
import json
from openai import OpenAI
from tools import AgentTools
from utils import setup_logger, log_query_result
from config import OPENAI_API_KEY, AGENT_MODEL, AGENT_TEMPERATURE

logger = setup_logger(__name__)


class DataInsightsAgent:
    """
    AI agent that assists users in querying and analyzing student performance data.
    Uses OpenAI's function calling to interact with data tools.
    """
    
    def __init__(self, tools: AgentTools, api_key: str = OPENAI_API_KEY):
        """
        Initializes the agent with tools and OpenAI client.
        Inputs: tools (AgentTools), api_key (string)
        Outputs: None
        """
        self.tools = tools
        self.client = OpenAI(api_key=api_key)
        self.model = AGENT_MODEL
        self.temperature = AGENT_TEMPERATURE
        self.conversation_history: List[Dict] = []
        
        # System prompt
        self.system_prompt = """You are a helpful data insights assistant for a student performance analytics system. 
Your role is to help users query and analyze student performance data using the available tools.

Key guidelines:
- Use the provided tools to query data instead of making assumptions
- Only return limited results to avoid overwhelming the user
- Provide clear, concise analysis of student performance data
- Focus on educational insights: scores, demographics, test preparation impact
- Suggest creating a support ticket when:
  1. You cannot answer the user's question with available tools
  2. The user explicitly asks for human help
  3. The query involves operations beyond data analysis
  4. The user reports bugs or issues with the system
- Be friendly and professional
- Format scores clearly and provide context (e.g., "average score of 75.3 out of 100")
- When showing data, present it in a readable format
- When discussing demographics, be respectful and objective
- NEVER perform write operations (INSERT, UPDATE, DELETE) - the system blocks these for safety

Safety: This system has safety features that prevent any dangerous database operations like deleting or modifying data."""
        
        logger.info(f"DataInsightsAgent initialized with model: {self.model}")
    
    def _should_suggest_support_ticket(self, user_message: str, assistant_response: str = "") -> bool:
        """
        Determines if the agent should suggest creating a support ticket.
        Inputs: user_message (string), assistant_response (string)
        Outputs: boolean
        """
        # Keywords that might indicate need for human support
        support_keywords = [
            "help", "support", "ticket", "human", "agent",
            "bug", "error", "broken", "not working", "issue",
            "complaint", "problem", "can't", "cannot", "unable"
        ]
        
        user_lower = user_message.lower()
        
        # Check for explicit support requests
        for keyword in support_keywords:
            if keyword in user_lower:
                return True
        
        return False
    
    def chat(self, user_message: str) -> Dict[str, Any]:
        """
        Processes user message and returns agent response with function calling.
        Inputs: user_message (string)
        Outputs: dictionary with response and metadata
        """
        logger.info(f"User message: {user_message}")
        
        # Add user message to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Prepare messages for API call
        messages = [  # type: ignore
            {"role": "system", "content": self.system_prompt}
        ] + self.conversation_history  # type: ignore

        # Get available tools
        tools_definitions = self.tools.get_tool_definitions()  # type: ignore

        try:
            # Make initial API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                tools=tools_definitions,  # type: ignore[arg-type]
                temperature=self.temperature
            )
            
            assistant_message = response.choices[0].message
            tool_calls = assistant_message.tool_calls
            
            # If no tool calls, return the response directly
            if not tool_calls:
                assistant_content = assistant_message.content
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_content
                })
                
                logger.info(f"Agent response (no tool calls): {assistant_content[:100]}...")
                
                # Check if support ticket should be suggested
                suggest_ticket = self._should_suggest_support_ticket(user_message, assistant_content)
                
                return {
                    "success": True,
                    "response": assistant_content,
                    "tool_calls_made": [],
                    "suggest_support_ticket": suggest_ticket
                }
            
            # Process tool calls
            logger.info(f"Agent making {len(tool_calls)} tool call(s)")
            
            # Add assistant message with tool calls to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in tool_calls
                ]
            })
            
            tool_calls_info = []
            
            # Execute each tool call
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                logger.info(f"Executing tool: {function_name} with args: {function_args}")
                
                # Execute the function
                function_result = self._execute_tool(function_name, function_args)
                
                tool_calls_info.append({
                    "function": function_name,
                    "arguments": function_args,
                    "result_summary": self._summarize_result(function_result)
                })
                
                # Add tool response to conversation history
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(function_result)
                })
            
            # Get final response from model
            final_response = self.client.chat.completions.create(
                model=self.model,
                messages=[  # type: ignore
                    {"role": "system", "content": self.system_prompt}
                ] + self.conversation_history,  # type: ignore
                temperature=self.temperature
            )
            
            final_content = final_response.choices[0].message.content
            
            # Add final response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": final_content
            })
            
            logger.info(f"Agent final response: {final_content[:100]}...")
            log_query_result(f"Completed {len(tool_calls)} tool calls")
            
            # Check if support ticket should be suggested
            suggest_ticket = self._should_suggest_support_ticket(user_message, final_content)
            
            return {
                "success": True,
                "response": final_content,
                "tool_calls_made": tool_calls_info,
                "suggest_support_ticket": suggest_ticket
            }
            
        except Exception as e:
            error_msg = f"Error during chat: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "response": f"I encountered an error: {str(e)}. Please try again or create a support ticket for assistance.",
                "tool_calls_made": [],
                "suggest_support_ticket": True,
                "error": str(e)
            }
    
    def _execute_tool(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Executes a tool function by name with given arguments.
        Inputs: function_name (string), arguments (dict)
        Outputs: function result
        """
        # Map function names to actual methods
        function_map = {
            "search_students_by_criteria": self.tools.search_students_by_criteria,
            "get_aggregated_statistics": self.tools.get_aggregated_statistics,
            "get_score_analysis": self.tools.get_score_analysis,
            "get_demographic_breakdown": self.tools.get_demographic_breakdown,
            "get_dataset_overview": self.tools.get_dataset_overview,
            "get_top_performers": self.tools.get_top_performers,
            "get_test_prep_impact": self.tools.get_test_prep_impact
        }
        
        if function_name not in function_map:
            logger.error(f"Unknown function: {function_name}")
            return {"success": False, "error": f"Unknown function: {function_name}"}
        
        try:
            function = function_map[function_name]
            result = function(**arguments)
            return result
        except Exception as e:
            logger.error(f"Error executing {function_name}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _summarize_result(self, result: Any) -> str:
        """
        Creates a brief summary of function result for logging.
        Inputs: result (any)
        Outputs: summary string
        """
        if isinstance(result, dict):
            if "count" in result:
                return f"Returned {result['count']} items"
            elif "success" in result:
                return f"Success: {result['success']}"
        return "Result returned"
    
    def reset_conversation(self) -> None:
        """
        Resets conversation history.
        Inputs: None
        Outputs: None
        """
        self.conversation_history = []
        logger.info("Conversation history reset")
    
    def get_conversation_summary(self) -> str:
        """
        Returns a summary of the current conversation for support ticket.
        Inputs: None
        Outputs: summary string
        """
        summary_lines = []
        for msg in self.conversation_history[-6:]:  # Last 6 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if content and isinstance(content, str):
                summary_lines.append(f"{role.upper()}: {content[:200]}")
        
        return "\n".join(summary_lines)
