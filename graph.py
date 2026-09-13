"""Phase 3: LangGraph로 질문 유형에 따라 답변 스타일을 분기한다.
- info: 단순 정보 질문 → vault 근거로만 답 (Phase 1과 동일한 스타일)
- direction: 방향 조언이 필요한 맥락 → 근거 + 기억(memory.json)을 종합해 다음 행동까지 제안
"""

from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph

from chat import SYSTEM_PROMPT, _extract_text, get_chain, memory_text, retrieve_context

CLASSIFY_PROMPT = """사용자의 질문을 다음 중 하나로만 분류해라. 단어 하나만 답하고 다른 설명은 붙이지 마라.

- info: 특정 사실·정보·설명을 확인하려는 질문 (예: "OO가 뭐야?", "OO 정리해줘")
- direction: 지금 뭘 해야 할지, 어느 방향으로 가야 할지 조언이 필요한 맥락 (예: "요즘 뭘 해야 할지 모르겠어", "이거 어떻게 풀어가야 하지")

질문: {question}
분류:"""

DIRECTION_SYSTEM_PROMPT = """너는 사용자의 개인 세컨드 브레인(Obsidian 위키 노트)과 지난 상담에서 쌓인 기억을 근거로,
질문에 답하는 데서 그치지 않고 지금 무엇을 해보면 좋을지 먼저 제안하는 멘토다.
아래 [근거 문서]와 [이전 기억]에 실제로 있는 내용만 근거로 삼고, 없는 내용은 추측하지 말고 솔직히 "이 vault에서는 근거를 못 찾았다"고 말해라.
답변은 (1) 질문에 대한 짧은 답 (2) 근거·기억을 바탕으로 한 구체적인 다음 행동 제안, 두 부분으로 구성해라.
답변 끝에 어떤 노트를 근거로 썼는지 출처를 밝혀라."""


class MentorState(TypedDict):
    question: str
    context: str
    sources: list[str]
    route: Literal["info", "direction"]
    answer: str


def build_graph():
    retriever, llm = get_chain()

    def retrieve_node(state: MentorState) -> dict:
        context, sources = retrieve_context(state["question"], retriever)
        return {"context": context, "sources": sources}

    def classify_node(state: MentorState) -> dict:
        response = llm.invoke(CLASSIFY_PROMPT.format(question=state["question"]))
        label = _extract_text(response.content).strip().lower()
        route: Literal["info", "direction"] = (
            "direction" if "direction" in label else "info"
        )
        return {"route": route}

    def answer_info_node(state: MentorState) -> dict:
        messages = [
            ("system", SYSTEM_PROMPT),
            (
                "human",
                f"[이전 기억]\n{memory_text()}\n\n[근거 문서]\n{state['context']}\n\n[질문]\n{state['question']}",
            ),
        ]
        response = llm.invoke(messages)
        return {"answer": _extract_text(response.content)}

    def answer_direction_node(state: MentorState) -> dict:
        messages = [
            ("system", DIRECTION_SYSTEM_PROMPT),
            (
                "human",
                f"[이전 기억]\n{memory_text()}\n\n[근거 문서]\n{state['context']}\n\n[질문]\n{state['question']}",
            ),
        ]
        response = llm.invoke(messages)
        return {"answer": _extract_text(response.content)}

    graph = StateGraph(MentorState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("classify", classify_node)
    graph.add_node("answer_info", answer_info_node)
    graph.add_node("answer_direction", answer_direction_node)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "classify")
    graph.add_conditional_edges(
        "classify",
        lambda state: state["route"],
        {"info": "answer_info", "direction": "answer_direction"},
    )
    graph.add_edge("answer_info", END)
    graph.add_edge("answer_direction", END)

    return graph.compile()


def ask(question: str, app) -> dict:
    result = app.invoke({"question": question})
    return {
        "answer": result["answer"],
        "sources": result["sources"],
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
        print(f"출처: {', '.join(result['sources'])}")
