import streamlit as st
import asyncio
from agents import Agent, Runner
from agents.mcp.server import MCPServerSse


async def run_agent_async(messages):
    async with MCPServerSse(
        params={
            "transport": "sse",
            "url": "http://localhost:8888/mcp",
            "serverUrl": "http://localhost:8888/mcp"
        },
        cache_tools_list=True,
        client_session_timeout_seconds=60,
    ) as mcp_server:
        agent = Agent(
            name="Paper citation network agent",
            instructions="Use the tools to answer questions about the paper citation network.",
            model="gpt-4o-mini",
            mcp_servers=[mcp_server]
        )
        result = await Runner.run(agent, messages)
        return result

def run_agent(messages):
    result = asyncio.run(run_agent_async(messages))
    return result.final_output

def submit():
    if st.session_state['user_input'].strip():
        st.session_state['conversation'].append({"role": "user", "content": st.session_state['user_input']})
        try:
            agent_response = run_agent(st.session_state['conversation'])
        except Exception as e:
            agent_response = f"Error: {e}"
        st.session_state['conversation'].append({"role": "assistant", "content": str(agent_response)})
        st.session_state['user_input'] = ""


st.title("Paper Citation Network Agent")
if 'user_input' not in st.session_state:
    st.session_state['user_input'] = ""
if 'conversation' not in st.session_state:
    st.session_state['conversation'] = []
for msg in st.session_state['conversation'][-8:]:
    if msg['role'] == 'user':
        st.markdown(f"**You:** {msg['content']}")
    else:
        st.markdown(f"<div style='background-color:#f0f2f6;padding:8px;border-radius:8px;'><b>Agent:</b> {msg['content']}</div>", unsafe_allow_html=True)

st.text_input("Your message:", key="user_input")
st.button("Send", on_click=submit)
