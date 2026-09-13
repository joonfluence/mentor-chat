"""Phase 3~4: LangGraph로 질문 유형에 따라 답변 스타일을 분기하고, vault 검색에 웹 검색을 더한다.
- info: 단순 정보 질문 → vault+웹 근거로 답 (Phase 1과 동일한 스타일 확장)
- direction: 방향 조언이 필요한 맥락 → 근거(vault+웹) + 기억(memory.json)을 종합해 다음 행동까지 제안
"""

import os
from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph
from tavily import TavilyClient

from chat import _extract_text, get_chain, memory_text, retrieve_context
from db import get_agenda, list_conversations

CLASSIFY_PROMPT = """사용자의 질문을 다음 중 하나로만 분류해라. 단어 하나만 답하고 다른 설명은 붙이지 마라.

- info: 특정 사실·정보·설명을 확인하려는 질문 (예: "OO가 뭐야?", "OO 정리해줘")
- direction: 지금 뭘 해야 할지, 어느 방향으로 가야 할지 조언이 필요한 맥락 (예: "요즘 뭘 해야 할지 모르겠어", "이거 어떻게 풀어가야 하지")

질문: {question}
분류:"""

INFO_SYSTEM_PROMPT = """너는 사용자의 개인 세컨드 브레인(Obsidian 위키 노트)과 웹 검색 결과를 근거로 답하는 상담 도우미다.
[근거 문서](vault 노트)와 [웹 검색 결과](실시간 외부 정보) 중 어디서 가져온 내용인지 구분해서 답해라.
둘 다에 없는 내용은 추측하지 말고 "근거를 못 찾았다"고 솔직히 말해라.
[이전 기억]은 과거 상담에서 이미 확인된 사용자의 결정·선호·반복되는 고민이다 — 참고만 하고 vault/웹 근거인 것처럼 인용하지는 마라.
답변 끝에 vault 노트 제목과 웹 출처(제목+URL)를 구분해서 밝혀라."""

DIRECTION_SYSTEM_PROMPT = """너는 사용자의 개인 세컨드 브레인(Obsidian 위키 노트), 웹 검색 결과, 지난 상담에서 쌓인 기억을 근거로,
질문에 답하는 데서 그치지 않고 지금 무엇을 해보면 좋을지 먼저 제안하는 멘토다.
[근거 문서](vault 노트)와 [웹 검색 결과](실시간 외부 정보)에 실제로 있는 내용만 근거로 삼고, 없는 내용은 추측하지 말고 솔직히 "근거를 못 찾았다"고 말해라.
[상담 아젠다]가 주어지면, 그 아젠다의 이전 상담 이력과 지금 상황을 비교해서 진행상황이 어떤지(잘 되고 있는지, 정체됐는지, 방향이 바뀌었는지) 솔직한 피드백을 반드시 포함해라.
답변은 (1) 질문에 대한 짧은 답 (2) 근거·기억(·아젠다 진행상황)을 바탕으로 한 구체적인 다음 행동 제안, 두 부분으로 구성해라.
답변 끝에 vault 노트 제목과 웹 출처(제목+URL)를 구분해서 밝혀라."""


class MentorState(TypedDict):
    question: str
    context: str
    sources: list[str]
    web_results: list[dict]
    agenda_id: int | None
    agenda_context: str
    route: Literal["info", "direction"]
    answer: str


def _format_web_results(web_results: list[dict]) -> str:
    if not web_results:
        return "(웹 검색 결과 없음)"
    return "\n\n---\n\n".join(
        f"[{r['title']}]({r['url']})\n{r['content']}" for r in web_results
    )


def build_graph():
    retriever, llm = get_chain()
    tavily_key = os.environ.get("TAVILY_API_KEY")
    tavily_client = TavilyClient(api_key=tavily_key) if tavily_key else None

    def retrieve_node(state: MentorState) -> dict:
        context, sources = retrieve_context(state["question"], retriever)
        return {"context": context, "sources": sources}

    def web_search_node(state: MentorState) -> dict:
        if tavily_client is None:
            return {"web_results": []}
        response = tavily_client.search(state["question"], max_results=3)
        results = [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
            }
            for r in response.get("results", [])
        ]
        return {"web_results": results}

    def classify_node(state: MentorState) -> dict:
        response = llm.invoke(CLASSIFY_PROMPT.format(question=state["question"]))
        label = _extract_text(response.content).strip().lower()
        route: Literal["info", "direction"] = (
            "direction" if "direction" in label else "info"
        )
        return {"route": route}

    def agenda_context_node(state: MentorState) -> dict:
        agenda = get_agenda(state["agenda_id"])
        history = list_conversations(agenda_id=state["agenda_id"])
        history_text = (
            "\n\n".join(f"Q: {h['question']}\nA: {h['answer']}" for h in history[-5:])
            or "(이 아젠다의 첫 상담)"
        )
        agenda_context = (
            f"제목: {agenda['title']}\n설명: {agenda['description']}\n\n"
            f"[이 아젠다의 최근 상담 이력]\n{history_text}"
        )
        # 아젠다 상담은 항상 방향제안 스타일(진행상황 피드백)로 답한다 — 분류 노드를 거치지 않는다.
        return {"agenda_context": agenda_context, "route": "direction"}

    def _build_human_message(state: MentorState) -> str:
        parts = [f"[이전 기억]\n{memory_text()}"]
        if state.get("agenda_context"):
            parts.append(f"[상담 아젠다]\n{state['agenda_context']}")
        parts.append(f"[근거 문서]\n{state['context']}")
        parts.append(f"[웹 검색 결과]\n{_format_web_results(state['web_results'])}")
        parts.append(f"[질문]\n{state['question']}")
        return "\n\n".join(parts)

    def answer_info_node(state: MentorState) -> dict:
        messages = [
            ("system", INFO_SYSTEM_PROMPT),
            ("human", _build_human_message(state)),
        ]
        response = llm.invoke(messages)
        return {"answer": _extract_text(response.content)}

    def answer_direction_node(state: MentorState) -> dict:
        messages = [
            ("system", DIRECTION_SYSTEM_PROMPT),
            ("human", _build_human_message(state)),
        ]
        response = llm.invoke(messages)
        return {"answer": _extract_text(response.content)}

    graph = StateGraph(MentorState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("web_search", web_search_node)
    graph.add_node("classify", classify_node)
    graph.add_node("agenda_context", agenda_context_node)
    graph.add_node("answer_info", answer_info_node)
    graph.add_node("answer_direction", answer_direction_node)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "web_search")
    # 아젠다가 지정돼 있으면 분류를 건너뛰고 바로 방향제안(진행상황 피드백) 스타일로 간다.
    graph.add_conditional_edges(
        "web_search",
        lambda state: "agenda" if state.get("agenda_id") else "classify",
        {"agenda": "agenda_context", "classify": "classify"},
    )
    graph.add_conditional_edges(
        "classify",
        lambda state: state["route"],
        {"info": "answer_info", "direction": "answer_direction"},
    )
    graph.add_edge("agenda_context", "answer_direction")
    graph.add_edge("answer_info", END)
    graph.add_edge("answer_direction", END)

    return graph.compile()


def ask(question: str, app, agenda_id: int | None = None) -> dict:
    result = app.invoke(
        {
            "question": question,
            "web_results": [],
            "agenda_id": agenda_id,
            "agenda_context": "",
        }
    )
    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "web_sources": [
            f"{r['title']} ({r['url']})" for r in result.get("web_results", [])
        ],
        "route": result["route"],
    }


if __name__ == "__main__":
    app = build_graph()
    while True:
        q = input("\n질문 (종료: exit): ")
        if q.strip().lower() == "exit":
            break
        result = ask(q, app)
        print(f"\n[{result['route']}] 답변: {result['answer']}")
        print(f"vault 출처: {', '.join(result['sources'])}")
        print(f"웹 출처: {', '.join(result['web_sources']) or '(없음)'}")
