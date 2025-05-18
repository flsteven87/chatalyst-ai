import streamlit as st
from app.core.agents import OpenAIChatAgent

st.set_page_config(page_title="ChataLyst AI Chat", page_icon="🤖")

st.title("ChataLyst AI Chat")

if "conversation" not in st.session_state:
    st.session_state.conversation = []

agent = OpenAIChatAgent()

for msg in st.session_state.conversation:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("請輸入訊息..."):
    st.session_state.conversation.append({"role": "user", "content": prompt})
    with st.spinner("Thinking..."):
        reply = agent.chat(st.session_state.conversation)
    st.session_state.conversation.append({"role": "assistant", "content": reply})
    st.chat_message("user").write(prompt)
    st.chat_message("assistant").write(reply)
