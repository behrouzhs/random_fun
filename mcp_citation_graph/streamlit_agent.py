import streamlit as st
import asyncio
from agents import Agent, Runner
from agents.mcp.server import MCPServerSse
from mcp_agent import MCPAgent


def submit():
    if st.session_state['user_input'].strip():
        st.session_state['conversation'].append({"role": "user", "content": st.session_state['user_input']})
        try:
            agent_response = st.session_state['agent'].run(st.session_state['conversation'])
        except Exception as e:
            agent_response = f"Error: {e}"
        st.session_state['conversation'].append({"role": "assistant", "content": str(agent_response)})
        st.session_state['user_input'] = ""


st.title("Paper Citation Network Agent")
if 'user_input' not in st.session_state:
    st.session_state['user_input'] = ""
if 'conversation' not in st.session_state:
    st.session_state['conversation'] = []
if 'agent' not in st.session_state:
    st.session_state['agent'] = MCPAgent(mcp_server_urls=["http://localhost:8888/mcp"])

for msg in st.session_state['conversation'][-8:]:
    if msg['role'] == 'user':
        st.markdown(f"**You:** {msg['content']}")
    else:
        st.markdown(f"<div style='background-color:#f0f2f6;padding:8px;border-radius:8px;'><b>Agent:</b> {msg['content']}</div>", unsafe_allow_html=True)

st.text_input("Your message:", key="user_input")
st.button("Send", on_click=submit)
