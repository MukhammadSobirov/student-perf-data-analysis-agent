"""
Support ticket module for creating Trello cards.
Handles integration with Trello API for user support requests.
"""
from typing import Dict, Any, Optional
from trello import TrelloClient
from utils import setup_logger, format_timestamp
from config import TRELLO_API_KEY, TRELLO_TOKEN, TRELLO_BOARD_ID, TRELLO_LIST_ID

logger = setup_logger(__name__)


class SupportTicketManager:
    """
    Manages creation of support tickets as Trello cards.
    """
    
    def __init__(
        self,
        api_key: str = TRELLO_API_KEY,
        token: str = TRELLO_TOKEN,
        board_id: str = TRELLO_BOARD_ID,
        list_id: str = TRELLO_LIST_ID
    ):
        """
        Initializes Trello client with credentials.
        Inputs: api_key, token, board_id, list_id (all strings)
        Outputs: None
        """
        self.api_key = api_key
        self.token = token
        self.board_id = board_id
        self.list_id = list_id
        self.trello_client: Optional[TrelloClient] = None
        
        logger.info("SupportTicketManager initialized")
    
    def _connect(self) -> bool:
        """
        Establishes connection to Trello.
        Inputs: None
        Outputs: boolean (success status)
        """
        if not all([self.api_key, self.token]):
            logger.error("Trello credentials not configured")
            return False
        
        try:
            self.trello_client = TrelloClient(
                api_key=self.api_key,
                token=self.token
            )
            logger.info("Successfully connected to Trello")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Trello: {str(e)}")
            return False
    
    def create_card(
        self,
        name: str,
        description: str,
        labels: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Creates a support card in Trello.
        Inputs: name (string), description (string), labels (optional list)
        Outputs: dictionary with card information
        """
        logger.info(f"Creating support card: {name}")
        
        # Connect to Trello if not already connected
        if not self.trello_client:
            if not self._connect():
                return {
                    "success": False,
                    "error": "Failed to connect to Trello. Please check configuration."
                }
        
        try:
            # Get the list where we want to add the card
            if not self.list_id:
                return {
                    "success": False,
                    "error": "Trello list ID not configured"
                }
            
            # Get the list object
            trello_list = self.trello_client.get_list(self.list_id)
            
            # Create the card
            card = trello_list.add_card(name=name, desc=description)
            
            # Add labels if provided
            if labels:
                for label_name in labels:
                    try:
                        # Get board to access labels
                        board = self.trello_client.get_board(self.board_id)
                        for label in board.get_labels():
                            if label.name.lower() == label_name.lower():
                                card.add_label(label)
                                break
                    except Exception as e:
                        logger.warning(f"Could not add label {label_name}: {str(e)}")
            
            card_url = card.url
            card_id = card.id
            
            logger.info(f"Successfully created card: {card_id}")
            
            return {
                "success": True,
                "card_id": card_id,
                "card_url": card_url,
                "message": f"Support card created successfully"
            }
            
        except Exception as e:
            error_msg = f"Failed to create card: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def create_ticket_from_conversation(
        self,
        user_query: str,
        conversation_context: str,
        user_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a support card with conversation context.
        Inputs: user_query (string), conversation_context (string), user_email (optional string)
        Outputs: dictionary with card information
        """
        timestamp = format_timestamp()
        
        # Build card name (Trello card title)
        card_name = f"Support Request: {user_query[:60]}"
        
        # Build detailed description
        description_parts = [
            f"**Support Request - {timestamp}**",
            "",
            "### User Query:",
            user_query,
            "",
            "### Conversation Context:",
            "```",
            conversation_context,
            "```",
            ""
        ]
        
        if user_email:
            description_parts.extend([
                "### Contact:",
                f"Email: {user_email}",
                ""
            ])
        
        description_parts.append("---")
        description_parts.append("_This card was automatically created by the Student Performance Analytics App._")
        
        description = "\n".join(description_parts)
        
        # Create card with "support" label
        return self.create_card(
            name=card_name,
            description=description,
            labels=["support"]
        )
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Tests connection to Trello.
        Inputs: None
        Outputs: dictionary with connection status
        """
        logger.info("Testing Trello connection...")
        
        if self._connect():
            try:
                # Try to get board info
                board = self.trello_client.get_board(self.board_id)
                return {
                    "success": True,
                    "message": f"Connected to Trello successfully",
                    "board_name": board.name
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Connected but failed to access board: {str(e)}"
                }
        else:
            return {
                "success": False,
                "error": "Failed to connect to Trello"
            }
