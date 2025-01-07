import os
import asyncio
import streamlit as st
import time
from github_agent_ai import github_agent, Deps
import httpx
from dotenv import load_dotenv
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart

# Page configuration must be the first Streamlit command
st.set_page_config(
    page_title="GitHub Repository Assistant Agent",
    page_icon="🐙",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables
load_dotenv()

# Custom CSS for ChatGPT-like interface
st.markdown("""
<style>
    /* Main container styling */
    .main {
        max-width: 1200px !important;
    }
    
    /* Chat container */
    .chat-container {
        padding: 1rem;
        max-height: 70vh;
        overflow-y: auto;
        border-radius: 0.5rem;
        background-color: #f7f7f8;
        margin-bottom: 1rem;
    }
    
    /* Message bubbles */
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        max-width: 85%;
    }
    
    .stTextInput {
        padding: 0.5rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
    }
    
    /* Sample prompts styling */
    .sample-prompt {
        padding: 0.8rem 1.2rem;
        margin: 0.4rem;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        cursor: pointer;
        transition: all 0.2s;
        font-size: 0.9rem;
    }
    
    .sample-prompt:hover {
        background-color: #e9ecef;
        transform: translateY(-1px);
    }
    
    /* Sidebar styling */
    .sidebar .stForm {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize enhanced session states
if 'client' not in st.session_state:
    st.session_state.client = httpx.AsyncClient()
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'conversations' not in st.session_state:
    st.session_state.conversations = []
if 'current_conversation' not in st.session_state:
    st.session_state.current_conversation = {
        'timestamp': None,
        'messages': [],
        'repo_url': ''
    }
if 'github_url' not in st.session_state:
    st.session_state.github_url = ""

# Initialize dependencies
deps = Deps(
    client=st.session_state.client,
    github_token=os.getenv('GITHUB_TOKEN'),
)

# Main title
st.title("🐙 GitHub Repository Assistant Agent")
st.markdown("Analyze repositories, explore code, and get insights from your GitHub projects.")

# Enhanced sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    with st.form(key="repo_settings"):
        st.subheader("Repository Settings")
        github_url = st.text_input(
            "GitHub Repository URL",
            value=st.session_state.github_url,
            help="Enter the GitHub repository URL you want to analyze.",
            placeholder="https://github.com/username/repository"
        )
        
        st.subheader("API Configuration")
        openrouter_api_key = st.text_input(
            "OpenRouter API Key",
            type="password",
            help="Enter your OpenRouter API key.",
            value=os.getenv('OPEN_ROUTER_API_KEY', '')
        )
        
        github_token = st.text_input(
            "GitHub Token",
            type="password",
            help="Enter your GitHub token for private repositories.",
            value=os.getenv('GITHUB_TOKEN', '')
        )
        
        llm_model = st.selectbox(
            "Language Model",
            options=["deepseek/deepseek-chat", "openai/gpt-3.5-turbo", "openai/gpt-4"],
            index=0,
            help="Select the Language Model to use for analysis."
        )
        
        submitted = st.form_submit_button("Save Settings")
        if submitted:
            st.session_state.github_url = github_url
            os.environ['OPEN_ROUTER_API_KEY'] = openrouter_api_key
            os.environ['GITHUB_TOKEN'] = github_token
            os.environ['LLM_MODEL'] = llm_model
            
            # Start new conversation
            if st.session_state.current_conversation['messages']:
                st.session_state.conversations.append(st.session_state.current_conversation)
            
            st.session_state.current_conversation = {
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                'messages': [],
                'repo_url': github_url
            }
            st.success("✅ Settings saved successfully!")


# Move this section before the sample prompts (around line 158)
async def process_message(message: str):
    if not st.session_state.github_url:
        st.warning("⚠️ Please enter a GitHub repository URL in the sidebar first.")
        return

    with st.spinner("🤔 Processing your request..."):
        try:
            # Initialize conversation timestamp if not set
            if st.session_state.current_conversation['timestamp'] is None:
                st.session_state.current_conversation['timestamp'] = time.strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.current_conversation['repo_url'] = st.session_state.github_url

            # Run the agent
            result = await github_agent.run(
                message,
                deps=deps,
                message_history=st.session_state.current_conversation['messages']
            )

            # Store messages in current conversation
            user_message = ModelRequest(parts=[UserPromptPart(content=message)])
            st.session_state.current_conversation['messages'].append(user_message)
            
            filtered_messages = [
                msg for msg in result.new_messages()
                if not (
                    hasattr(msg, 'parts') and
                    any(part.part_kind in ['user-prompt', 'text'] for part in msg.parts)
                )
            ]
            st.session_state.current_conversation['messages'].extend(filtered_messages)
            
            agent_response = ModelResponse(parts=[TextPart(content=result.data)])
            st.session_state.current_conversation['messages'].append(agent_response)
            
            st.rerun()

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")


# Sample prompts section (moved above chat history)
st.markdown("## 🚀 Quick Actions")
with st.container():
    sample_prompts = [
        "Show me the structure of this repository",
        "What are the main features of this project?",
        "Show me the contents of the main Python file",
        "List all dependencies in requirements.txt"
    ]
    
    cols = st.columns(2)
    for i, col in enumerate(cols):
        with col:
            for j in range(2):
                prompt_index = i * 2 + j
                if st.button(
                    sample_prompts[prompt_index],
                    key=f"prompt_{prompt_index}",
                    use_container_width=True,
                    type="secondary"
                ):
                    if not st.session_state.github_url:
                        st.warning("⚠️ Please enter a GitHub repository URL first.")
                    else:
                        asyncio.run(process_message(f"{sample_prompts[prompt_index]} in {st.session_state.github_url}"))

st.markdown("---")

# Chat history section
st.markdown("## 💬 Chat History")

# Display previous conversations
if st.session_state.conversations:
    with st.expander("Previous Conversations", expanded=False):
        for conv in reversed(st.session_state.conversations):
            st.markdown(f"**{conv['timestamp']}** - Repository: `{conv['repo_url']}`")
            for msg in conv['messages']:
                if isinstance(msg, ModelRequest):
                    for part in msg.parts:
                        if isinstance(part, UserPromptPart):
                            st.chat_message("user").write(part.content)
                elif isinstance(msg, ModelResponse):
                    for part in msg.parts:
                        if isinstance(part, TextPart):
                            st.chat_message("assistant").write(part.content)
            st.markdown("---")

# Display current conversation
if st.session_state.current_conversation['messages']:
    st.markdown(f"**Current Conversation** - Started at {st.session_state.current_conversation['timestamp']}")
    for msg in st.session_state.current_conversation['messages']:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, UserPromptPart):
                    st.chat_message("user").write(part.content)
        elif isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, TextPart):
                    st.chat_message("assistant").write(part.content)

# Message processing function
async def process_message(message: str):
    if not st.session_state.github_url:
        st.warning("⚠️ Please enter a GitHub repository URL in the sidebar first.")
        return

    with st.spinner("🤔 Processing your request..."):
        try:
            # Initialize conversation timestamp if not set
            if st.session_state.current_conversation['timestamp'] is None:
                st.session_state.current_conversation['timestamp'] = time.strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.current_conversation['repo_url'] = st.session_state.github_url

            # Run the agent
            result = await github_agent.run(
                message,
                deps=deps,
                message_history=st.session_state.current_conversation['messages']
            )

            # Store messages in current conversation
            user_message = ModelRequest(parts=[UserPromptPart(content=message)])
            st.session_state.current_conversation['messages'].append(user_message)
            
            filtered_messages = [
                msg for msg in result.new_messages()
                if not (
                    hasattr(msg, 'parts') and
                    any(part.part_kind in ['user-prompt', 'text'] for part in msg.parts)
                )
            ]
            st.session_state.current_conversation['messages'].extend(filtered_messages)
            
            agent_response = ModelResponse(parts=[TextPart(content=result.data)])
            st.session_state.current_conversation['messages'].append(agent_response)
            
            st.rerun()

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

# Chat input
user_input = st.chat_input("Type your message here...")
if user_input:
    asyncio.run(process_message(user_input))

# Session management (in sidebar)
with st.sidebar:
    st.markdown("---")
    st.subheader("Session Management")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Reset Session", type="secondary"):
            if st.session_state.client:
                asyncio.run(st.session_state.client.aclose())
            st.session_state.client = httpx.AsyncClient()
            st.session_state.messages = []
            st.session_state.current_conversation = {
                'timestamp': None,
                'messages': [],
                'repo_url': st.session_state.github_url
            }
            st.success("Session reset successfully!")
    
    with col2:
        if st.button("Save Conversation", type="primary"):
            if st.session_state.current_conversation['messages']:
                st.session_state.conversations.append(st.session_state.current_conversation)
                st.session_state.current_conversation = {
                    'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                    'messages': [],
                    'repo_url': st.session_state.github_url
                }
                st.success("Conversation saved!")






































# import os
# import asyncio
# import streamlit as st
# from github_agent_ai import github_agent, Deps
# import httpx
# from dotenv import load_dotenv
# from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart

# # Page configuration must be the first Streamlit command
# st.set_page_config(
#     page_title="GitHub Repository Assistant Agent",
#     page_icon="🐙",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # Load environment variables
# load_dotenv()

# # Custom CSS for ChatGPT-like interface
# st.markdown("""
# <style>
#     .stTextInput {
#         padding: 0.5rem;
#         border-radius: 0.5rem;
#         border: 1px solid #dee2e6;
#     }
    
#     .sample-prompt {
#         padding: 0.5rem 1rem;
#         margin: 0.25rem;
#         border-radius: 0.25rem;
#         background-color: #f8f9fa;
#         border: 1px solid #dee2e6;
#         cursor: pointer;
#         transition: all 0.2s;
#     }
    
#     .sample-prompt:hover {
#         background-color: #e9ecef;
#     }
# </style>
# """, unsafe_allow_html=True)

# # Initialize session states
# if 'client' not in st.session_state:
#     st.session_state.client = httpx.AsyncClient()
# if 'messages' not in st.session_state:
#     st.session_state.messages = []
# if 'github_url' not in st.session_state:
#     st.session_state.github_url = ""

# # Initialize dependencies
# deps = Deps(
#     client=st.session_state.client,
#     github_token=os.getenv('GITHUB_TOKEN'),
# )

# # Main title
# st.title("🐙 GitHub Repository Assistant Agent")
# st.markdown("Analyze repositories, explore code, and get insights from your GitHub projects.")

# # Sidebar configuration
# with st.sidebar:
#     st.header("⚙️ Configuration")
#     github_url = st.text_input(
#         "GitHub Repository URL",
#         value=st.session_state.github_url,
#         help="Enter the GitHub repository URL you want to analyze."
#     )
#     openrouter_api_key = st.text_input(
#         "OpenRouter API Key",
#         type="password",
#         help="Enter your OpenRouter API key."
#     )
#     llm_model = st.selectbox(
#         "Language Model",
#         options=["deepseek/deepseek-chat", "openai/gpt-3.5-turbo", "openai/gpt-4"],
#         index=0,
#         help="Select the Language Model to use for analysis."
#     )
    
#     if st.button("Save Settings"):
#         st.session_state.github_url = github_url
#         os.environ['OPEN_ROUTER_API_KEY'] = openrouter_api_key
#         os.environ['LLM_MODEL'] = llm_model
#         st.success("✅ Settings saved successfully!")

# # Display chat messages
# st.markdown("## 💬 Chat History")
# for msg in st.session_state.messages:
#     if isinstance(msg, ModelRequest):
#         for part in msg.parts:
#             if isinstance(part, UserPromptPart):
#                 st.chat_message("user").write(part.content)
#     elif isinstance(msg, ModelResponse):
#         for part in msg.parts:
#             if isinstance(part, TextPart):
#                 st.chat_message("assistant").write(part.content)

# # Sample prompts
# st.markdown("## Sample Prompts")
# col1, col2 = st.columns(2)

# sample_prompts = [
#     "Show me the structure of this repository",
#     "What are the main features of this project?",
#     "Show me the contents of the main Python file",
#     "List all dependencies in requirements.txt"
# ]

# async def process_message(message: str):
#     if not github_url:
#         st.warning("⚠️ Please enter a GitHub repository URL in the sidebar first.")
#         return

#     with st.spinner("🤔 Processing your request..."):
#         try:
#             # Run the agent
#             result = await github_agent.run(
#                 message,
#                 deps=deps,
#                 message_history=st.session_state.messages
#             )

#             # Store messages
#             user_message = ModelRequest(parts=[UserPromptPart(content=message)])
#             st.session_state.messages.append(user_message)
            
#             # Store intermediary messages
#             filtered_messages = [
#                 msg for msg in result.new_messages()
#                 if not (
#                     hasattr(msg, 'parts') and
#                     any(part.part_kind in ['user-prompt', 'text'] for part in msg.parts)
#                 )
#             ]
#             st.session_state.messages.extend(filtered_messages)
            
#             # Store the final response
#             agent_response = ModelResponse(parts=[TextPart(content=result.data)])
#             st.session_state.messages.append(agent_response)
            
#             st.rerun()

#         except Exception as e:
#             st.error(f"An error occurred: {str(e)}")

# def handle_prompt_click(prompt):
#     if not st.session_state.github_url:
#         st.warning("⚠️ Please enter a GitHub repository URL in the sidebar first.")
#         return
#     full_prompt = f"{prompt} in {st.session_state.github_url}"
#     asyncio.run(process_message(full_prompt))

# with col1:
#     st.button(sample_prompts[0], on_click=lambda: handle_prompt_click(sample_prompts[0]))
#     st.button(sample_prompts[1], on_click=lambda: handle_prompt_click(sample_prompts[1]))
# with col2:
#     st.button(sample_prompts[2], on_click=lambda: handle_prompt_click(sample_prompts[2]))
#     st.button(sample_prompts[3], on_click=lambda: handle_prompt_click(sample_prompts[3]))

# # Chat input
# user_input = st.chat_input("Type your message here...")
# if user_input:
#     asyncio.run(process_message(user_input))

# # Client cleanup button (in sidebar)
# with st.sidebar:
#     st.markdown("---")
#     if st.button("Reset Session"):
#         if st.session_state.client:
#             asyncio.run(st.session_state.client.aclose())
#         st.session_state.client = httpx.AsyncClient()
#         st.session_state.messages = []
#         st.success("Session reset successfully!")