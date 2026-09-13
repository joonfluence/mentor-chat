"""Phase 1-⑤⑥: Streamlit 채팅 UI + 상담 내역 JSONL 기록."""

import json
import os
from datetime import datetime, timezone

import streamlit as st

from graph import ask, build_graph

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
LOG_PATH = os.path.join(LOG_DIR, "conversations.jsonl")


def log_turn(
    question: str, answer: str, sources: list[str], web_sources: list[str], route: str
) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "answer": answer,
        "sources": sources,
        "web_sources": web_sources,
        "route": route,
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


st.set_page_config(page_title="멘토와의 대화")
st.title("멘토와의 대화")
st.caption("내 세컨드 브레인(llm-wiki) + 웹 검색에 근거해서 답합니다.")

if "graph_app" not in st.session_state:
    st.session_state.graph_app = build_graph()
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

    with st.chat_message("assistant"):
        with st.spinner("vault 검색 중..."):
            result = ask(question, st.session_state.graph_app)
        st.markdown(result["answer"])
        route_label = "방향 제안" if result["route"] == "direction" else "정보 답변"
        st.caption(f"[{route_label}] vault 출처: {', '.join(result['sources']) or '없음'}")
        if result["web_sources"]:
            st.caption(f"웹 출처: {', '.join(result['web_sources'])}")

    st.session_state.messages.append({"role": "assistant", "content": result["answer"]})
    log_turn(
        question,
        result["answer"],
        result["sources"],
        result["web_sources"],
        result["route"],
    )
