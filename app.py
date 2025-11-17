"""
Main Streamlit application for Student Performance Analytics.
Provides UI for data visualization and AI agent chat interface.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import DataManager
from tools import AgentTools
from agent import DataInsightsAgent
from support_ticket import SupportTicketManager
from utils import setup_logger, format_price
from config import OPENAI_API_KEY, TRELLO_API_KEY, TRELLO_TOKEN, TRELLO_BOARD_ID, TRELLO_LIST_ID
import sys

logger = setup_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="Student Performance Analytics",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .stButton>button {
        width: 100%;
    }
    .chat-message {
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .user-message {
        background-color: #e3f2fd;
    }
    .assistant-message {
        background-color: #f5f5f5;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def initialize_app():
    """
    Initializes application components (cached for performance).
    Inputs: None
    Outputs: tuple (data_manager, agent_tools, agent, ticket_manager)
    """
    logger.info("Initializing application components...")
    
    try:
        # Initialize data manager
        data_manager = DataManager()
        
        # Initialize tools
        agent_tools = AgentTools(data_manager)
        
        # Initialize agent (will be re-initialized with user's API key if provided)
        agent = None
        
        # Initialize ticket manager
        ticket_manager = SupportTicketManager()
        
        logger.info("Application components initialized successfully")
        
        return data_manager, agent_tools, ticket_manager
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        st.error(f"Failed to initialize application: {str(e)}")
        sys.exit(1)


def display_business_metrics(data_manager: DataManager):
    """
    Displays student performance metrics dashboard.
    Inputs: data_manager (DataManager)
    Outputs: None
    """
    st.header("📊 Performance Overview")
    
    # Get dataset stats
    stats = data_manager.get_summary_stats()
    df = data_manager.get_dataframe()
    
    # Display key metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Students",
            value=f"{stats['total_rows']:,}",
            help="Total number of students in dataset"
        )
    
    with col2:
        st.metric(
            label="Average Overall Score",
            value=f"{stats['avg_overall_score']:.1f}" if stats['avg_overall_score'] is not None else "N/A",
            help="Average score across all subjects (math, reading, writing)"
        )
    
    with col3:
        st.metric(
            label="Score Range",
            value=f"{stats['min_score']:.0f} - {stats['max_score']:.0f}" if stats['min_score'] is not None and stats['max_score'] is not None else "N/A",
            help="Min and max scores across all subjects"
        )
    
    with col4:
        st.metric(
            label="Pass Rate",
            value=f"{stats['pass_rate']:.1f}%" if stats['pass_rate'] is not None else "N/A",
            help="Percentage of students with all scores >= 60"
        )
    
    # Charts
    st.subheader("Data Visualization")
    
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        # Score distribution histogram
        scores_melted = pd.melt(
            df[['math score', 'reading score', 'writing score']], 
            var_name='Subject', 
            value_name='Score'
        )
        fig_scores = px.histogram(
            scores_melted,
            x='Score',
            color='Subject',
            nbins=30,
            title='Score Distribution by Subject',
            labels={'Score': 'Score (0-100)', 'count': 'Count'},
            barmode='overlay',
            opacity=0.7
        )
        st.plotly_chart(fig_scores, use_container_width=True)
    
    with chart_col2:
        # Performance by gender
        gender_scores = df.groupby('gender')[['math score', 'reading score', 'writing score']].mean().reset_index()
        gender_melted = pd.melt(
            gender_scores, 
            id_vars=['gender'], 
            value_vars=['math score', 'reading score', 'writing score'],
            var_name='Subject',
            value_name='Average Score'
        )
        fig_gender = px.bar(
            gender_melted,
            x='gender',
            y='Average Score',
            color='Subject',
            barmode='group',
            title='Average Scores by Gender',
            labels={'gender': 'Gender', 'Average Score': 'Score'}
        )
        st.plotly_chart(fig_gender, use_container_width=True)
    
    # Additional charts
    chart_col3, chart_col4 = st.columns(2)
    
    with chart_col3:
        # Parental education impact
        education_scores = df.groupby('parental level of education')['math score'].mean().sort_values(ascending=False)
        fig_education = px.bar(
            x=education_scores.values,
            y=education_scores.index,
            orientation='h',
            title='Average Math Score by Parental Education',
            labels={'x': 'Average Math Score', 'y': 'Parental Education Level'},
            color_discrete_sequence=['#9b59b6']
        )
        st.plotly_chart(fig_education, use_container_width=True)
    
    with chart_col4:
        # Test preparation effectiveness
        test_prep_counts = df['test preparation course'].value_counts()
        fig_test_prep = px.pie(
            values=test_prep_counts.values,
            names=test_prep_counts.index,
            title='Test Preparation Course Completion',
            color_discrete_sequence=['#2ecc71', '#e74c3c']
        )
        st.plotly_chart(fig_test_prep, use_container_width=True)
    
    # Additional row for more charts
    chart_col5, chart_col6 = st.columns(2)
    
    with chart_col5:
        # Performance by race/ethnicity
        race_scores = df.groupby('race/ethnicity')[['math score', 'reading score', 'writing score']].mean()
        race_scores['overall'] = race_scores.mean(axis=1)
        race_sorted = race_scores.sort_values('overall', ascending=False)
        fig_race = px.bar(
            x=race_sorted.index,
            y=race_sorted['overall'],
            title='Average Overall Score by Race/Ethnicity',
            labels={'x': 'Race/Ethnicity', 'y': 'Average Overall Score'},
            color_discrete_sequence=['#3498db']
        )
        st.plotly_chart(fig_race, use_container_width=True)
    
    with chart_col6:
        # Lunch type impact
        lunch_scores = df.groupby('lunch')[['math score', 'reading score', 'writing score']].mean().reset_index()
        lunch_melted = pd.melt(
            lunch_scores,
            id_vars=['lunch'],
            value_vars=['math score', 'reading score', 'writing score'],
            var_name='Subject',
            value_name='Average Score'
        )
        fig_lunch = px.bar(
            lunch_melted,
            x='lunch',
            y='Average Score',
            color='Subject',
            barmode='group',
            title='Average Scores by Lunch Type',
            labels={'lunch': 'Lunch Type', 'Average Score': 'Score'}
        )
        st.plotly_chart(fig_lunch, use_container_width=True)


def display_sample_queries():
    """
    Displays sample query buttons.
    Inputs: None
    Outputs: None
    """
    st.subheader("💡 Sample Queries")
    st.markdown("Try these example queries to get started:")
    
    col1, col2, col3 = st.columns(3)
    
    sample_queries = [
        "What are the top 10 students by math score?",
        "Show average scores by gender",
        "Compare students who completed test prep vs those who didn't",
        "Find students with all scores above 90",
        "What's the impact of parental education on performance?",
        "Show me students from group A with math score > 80",
        "Analyze reading score distribution",
        "Which demographic group has the highest average scores?",
        "What's the overall dataset summary?"
    ]
    
    cols = [col1, col2, col3]
    for idx, query in enumerate(sample_queries):
        with cols[idx % 3]:
            if st.button(query, key=f"sample_{idx}"):
                st.session_state.sample_query = query


def display_chat_interface(agent: DataInsightsAgent, ticket_manager: SupportTicketManager):
    """
    Displays chat interface with agent.
    Inputs: agent (DataInsightsAgent), ticket_manager (SupportTicketManager)
    Outputs: None
    """
    st.header("💬 Chat with AI Assistant")
    
    # Initialize session state for chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'sample_query' not in st.session_state:
        st.session_state.sample_query = None
    
    if 'show_ticket_suggestion' not in st.session_state:
        st.session_state.show_ticket_suggestion = False
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            role = message['role']
            content = message['content']
            
            if role == 'user':
                st.markdown(f'<div class="chat-message user-message"><strong>You:</strong> {content}</div>', 
                          unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message assistant-message"><strong>Assistant:</strong> {content}</div>', 
                          unsafe_allow_html=True)
                
                # Show tool calls if available
                if 'tool_calls' in message and message['tool_calls']:
                    with st.expander("View Function Calls"):
                        for tool_call in message['tool_calls']:
                            st.json(tool_call)
    
    # Chat input
    user_input = st.chat_input("Ask me anything about the student performance data...")
    
    # Handle sample query
    if st.session_state.sample_query:
        user_input = st.session_state.sample_query
        st.session_state.sample_query = None
    
    if user_input:
        # Add user message to history
        st.session_state.chat_history.append({
            'role': 'user',
            'content': user_input
        })
        
        # Get agent response
        with st.spinner("Thinking..."):
            try:
                response = agent.chat(user_input)
                
                if response['success']:
                    # Add assistant response to history
                    st.session_state.chat_history.append({
                        'role': 'assistant',
                        'content': response['response'],
                        'tool_calls': response.get('tool_calls_made', [])
                    })
                    
                    # Store support ticket suggestion state
                    if response.get('suggest_support_ticket', False):
                        st.session_state.show_ticket_suggestion = True
                else:
                    st.error(f"Error: {response.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"Error in chat: {str(e)}")
                st.error(f"An error occurred: {str(e)}")
        
        st.rerun()
    
    # Show support ticket suggestion if needed (outside user_input block so it persists)
    if st.session_state.get('show_ticket_suggestion', False):
        st.info("💡 Would you like to create a support ticket for human assistance?")
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("Create Support Ticket", key="create_ticket_btn"):
                st.session_state.create_ticket_request = True
                st.session_state.show_ticket_suggestion = False
                st.rerun()
        with col2:
            if st.button("Dismiss", key="dismiss_ticket_btn"):
                st.session_state.show_ticket_suggestion = False
                st.rerun()
    
    # Support ticket creation
    if st.session_state.get('create_ticket_request', False):
        display_ticket_form(agent, ticket_manager)


def display_ticket_form(agent: DataInsightsAgent, ticket_manager: SupportTicketManager):
    """
    Displays support ticket creation form.
    Inputs: agent (DataInsightsAgent), ticket_manager (SupportTicketManager)
    Outputs: None
    """
    st.subheader("🎫 Create Support Ticket")
    
    with st.form("support_ticket_form"):
        ticket_summary = st.text_input(
            "Brief summary of your issue",
            placeholder="e.g., Unable to find specific data"
        )
        
        ticket_description = st.text_area(
            "Detailed description",
            placeholder="Please describe your issue in detail...",
            height=150
        )
        
        user_email = st.text_input(
            "Your email (optional)",
            placeholder="your.email@example.com"
        )
        
        submit_button = st.form_submit_button("Submit Ticket")
        
        if submit_button:
            if not ticket_summary:
                st.error("Please provide a summary for the ticket")
            else:
                # Get conversation context
                conversation_context = agent.get_conversation_summary()
                
                # Create full description
                full_description = f"{ticket_description}\n\n--- Conversation Context ---\n{conversation_context}"
                
                # Create card
                with st.spinner("Creating support card..."):
                    result = ticket_manager.create_ticket_from_conversation(
                        user_query=ticket_summary,
                        conversation_context=full_description,
                        user_email=user_email if user_email else None
                    )
                
                if result['success']:
                    st.success(f"✅ {result['message']}")
                    st.markdown(f"**Card URL:** [View on Trello]({result['card_url']})")
                    st.session_state.create_ticket_request = False
                else:
                    st.error(f"❌ Failed to create card: {result.get('error', 'Unknown error')}")


def main():
    """
    Main application entry point.
    Inputs: None
    Outputs: None
    """
    logger.info("Starting Student Performance Insights App...")
    
    # Sidebar
    with st.sidebar:
        st.title("⚙️ Configuration")
        
        # API Key input
        api_key_input = st.text_input(
            "OpenAI API Key",
            type="password",
            value=OPENAI_API_KEY,
            help="Enter your OpenAI API key"
        )
        
        st.markdown("---")
        
        # Trello configuration status
        st.subheader("Trello Configuration")
        if TRELLO_API_KEY and TRELLO_TOKEN and TRELLO_BOARD_ID and TRELLO_LIST_ID:
            st.success("✅ Trello configured")
        else:
            st.warning("⚠️ Trello not configured")
            st.info("Set TRELLO_API_KEY, TRELLO_TOKEN, TRELLO_BOARD_ID, and TRELLO_LIST_ID in .env file")
        
        st.markdown("---")
        
        # Actions
        st.subheader("Actions")
        
        if st.button("🔄 Reset Chat"):
            st.session_state.chat_history = []
            if 'agent' in st.session_state and st.session_state.agent:
                st.session_state.agent.reset_conversation()
            st.rerun()
        
        if st.button("📋 View Logs"):
            st.info("Check your console for detailed logs")
        
        st.markdown("---")
        st.caption("Student Performance Analytics v1.0")
    
    # Main content
    st.title("🎓 Student Performance Analytics")
    st.markdown("Get insights from student performance data using AI")
    
    # Initialize components
    data_manager, agent_tools, ticket_manager = initialize_app()
    
    # Initialize agent with API key
    if not api_key_input:
        st.warning("⚠️ Please enter your OpenAI API key in the sidebar to use the chat feature.")
        api_key_valid = False
    else:
        api_key_valid = True
        if 'agent' not in st.session_state or st.session_state.get('api_key') != api_key_input:
            st.session_state.agent = DataInsightsAgent(agent_tools, api_key=api_key_input)
            st.session_state.api_key = api_key_input
            logger.info("Agent initialized with user API key")
    
    # Display sections
    display_business_metrics(data_manager)
    
    st.markdown("---")
    
    display_sample_queries()
    
    st.markdown("---")
    
    if api_key_valid:
        display_chat_interface(st.session_state.agent, ticket_manager)
    else:
        st.info("👆 Enter your OpenAI API key in the sidebar to start chatting with the AI assistant")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>🛡️ <strong>Safety Features Enabled:</strong> All write operations (INSERT, UPDATE, DELETE, DROP) are blocked</p>
        <p>📞 Need help? Use the chat to create a support card on Trello</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

