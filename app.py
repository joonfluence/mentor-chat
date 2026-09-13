"""Phase 1-⑤⑥: Streamlit 채팅 UI + 상담 내역 JSONL 기록."""

import json
import os
from datetime import datetime, timezone

import streamlit as st

from chat import ask, get_chain

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
LOG_PATH = os.path.join(LOG_DIR, "conversations.jsonl")


def log_turn(question: str, answer: str, sources: list[str]) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "answer": answer,
        "sources": sources,
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


st.set_page_config(page_title="멘토와의 대화")
st.title("멘토와의 대화")
st.caption("내 세컨드 브레인(llm-wiki)에 근거해서만 답합니다.")

if "chain" not in st.session_state:
    st.session_state.chain = get_chain()
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

question = st.chat_input("무엇이 궁금하세요?")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    retriever, llm = st.session_state.chain
    with st.chat_message("assistant"):
        with st.spinner("vault 검색 중..."):
            result = ask(question, retriever, llm)
        st.markdown(result["answer"])
        st.caption(f"출처: {', '.join(result['sources']) or '없음'}")

    st.session_state.messages.append({"role": "assistant", "content": result["answer"]})
    log_turn(question, result["answer"], result["sources"])
