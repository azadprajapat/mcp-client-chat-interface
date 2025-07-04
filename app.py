
import streamlit as st
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

st.set_page_config(page_title="MCP Chat client", page_icon="💬")
st.title("MCP  Chat Client (LangGraph MCP Agent)")

if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []
if 'agent' not in st.session_state:
    st.session_state['agent'] = None
if 'tools' not in st.session_state:
    st.session_state['tools'] = None
if 'client' not in st.session_state:
    st.session_state['client'] = None

# MCP server config (update as needed)
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8000/mcp")
MCP_TOKEN = os.environ.get("MCP_TOKEN", "YOUR_TOKEN")

async def setup_agent():
    client = MultiServerMCPClient({
        "calculator": {
            "transport": "streamable_http",
            "url": MCP_SERVER_URL,
            "headers": {
                "Authorization": f"Bearer {MCP_TOKEN}",
                "X-Custom-Header": "custom-value"
            },
        }
    })
    tools = await client.get_tools()
    agent = create_react_agent("openai:gpt-4.1", tools)
    return client, tools, agent

if st.session_state['agent'] is None:
    with st.spinner("Setting up MCP agent..."):
        client, tools, agent = asyncio.run(setup_agent())
        st.session_state['client'] = client
        st.session_state['tools'] = tools
        st.session_state['agent'] = agent
        st.success("MCP agent ready!")

st.markdown("---")
user_input = st.text_input("Type your message and press Enter:", key="user_input")
send_btn = st.button("Send", use_container_width=True)

if send_btn and user_input:
    st.session_state['chat_history'].append(("user", user_input))
    with st.spinner("Agent is thinking..."):
        try:
            response = asyncio.run(st.session_state['agent'].ainvoke({"messages": user_input}))
            # Extract and display only the relevant content and tool usage
            display_msgs = []
            if isinstance(response, dict) and "messages" in response:
                for msg in response["messages"]:
                    # Show tool invocation if present
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            tool_name = tool_call.get('name') or tool_call.get('function', {}).get('name')
                            tool_args = tool_call.get('args') or tool_call.get('function', {}).get('arguments')
                            display_msgs.append(f"<span style='color:#e67e22'><b>Invoking tool:</b> {tool_name} {tool_args}</span>")
                    # Show tool result if present
                    if msg.__class__.__name__ == 'ToolMessage' and hasattr(msg, 'content'):
                        display_msgs.append(f"<span style='color:#8e44ad'><b>Tool result:</b> {msg.content}</span>")
                    # Show final assistant message
                    if hasattr(msg, 'content') and msg.content:
                        if msg.__class__.__name__ == 'AIMessage':
                            display_msgs.append(msg.content)
            else:
                display_msgs.append(str(response))
            st.session_state['chat_history'].append(("assistant", "<br>".join(display_msgs)))
        except Exception as e:
            st.session_state['chat_history'].append(("assistant", f"Error: {e}"))
    st.rerun()

st.markdown("---")
for sender, msg in st.session_state['chat_history']:
    if sender == "user":
        st.markdown(f"<div style='text-align:right; color:#1a73e8;'><b>You:</b> {msg}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='text-align:left; color:#34a853;'><b>Assistant:</b> {msg}</div>", unsafe_allow_html=True)
