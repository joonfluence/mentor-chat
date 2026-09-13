"""Phase 1-⑤⑥ + Phase 4-3: Streamlit 채팅 UI + 아젠다 상담 + DB 상담 내역 기록."""

import streamlit as st

from db import create_agenda, list_agendas, save_conversation
from graph import ask, build_graph

st.set_page_config(page_title="멘토와의 대화")
st.title("멘토와의 대화")
st.caption("내 세컨드 브레인(llm-wiki) + 웹 검색에 근거해서 답합니다.")

if "graph_app" not in st.session_state:
    st.session_state.graph_app = build_graph()
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.subheader("상담 아젠다")
    agendas = list_agendas()
    options = {"없음 (일반 대화)": None}
    for a in agendas:
        options[f"{a['title']} (#{a['id']})"] = a["id"]
    selected_label = st.selectbox("아젠다 선택", list(options.keys()))
    agenda_id = options[selected_label]

    with st.expander("+ 새 아젠다 만들기"):
        new_title = st.text_input("제목", key="new_agenda_title")
        new_desc = st.text_area("설명 (지금 다루고 싶은 주제·목표)", key="new_agenda_desc")
        if st.button("만들기") and new_title.strip():
            create_agenda(new_title.strip(), new_desc.strip())
            st.rerun()

if agenda_id is not None:
    st.info(f"📌 현재 아젠다: {selected_label} — 이 아젠다의 이전 상담과 이어서 피드백을 줍니다.")

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
            result = ask(question, st.session_state.graph_app, agenda_id=agenda_id)
        st.markdown(result["answer"])
        route_label = "방향 제안" if result["route"] == "direction" else "정보 답변"
        st.caption(f"[{route_label}] vault 출처: {', '.join(result['sources']) or '없음'}")
        if result["web_sources"]:
            st.caption(f"웹 출처: {', '.join(result['web_sources'])}")

    st.session_state.messages.append({"role": "assistant", "content": result["answer"]})
    save_conversation(
        question=question,
        answer=result["answer"],
        sources=result["sources"],
        web_sources=result["web_sources"],
        route=result["route"],
        agenda_id=agenda_id,
    )
