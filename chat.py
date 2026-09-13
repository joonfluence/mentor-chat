"""Phase 1-④: 검색+답변 체인.
질문을 받으면 벡터스토어에서 관련 청크를 찾고, 그 근거로만 답하도록 Claude에게 요청한다.
"""

import os

from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from memory_store import load_memory

load_dotenv()

PERSIST_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION_NAME = "mentor_wiki"

# LLM_PROVIDER=opencode로 바꾸면 Claude 대신 opencode Zen 게이트웨이의 모델을 쓴다.
# opencode의 진짜 무료 모델("-free")은 opencode CLI 안에서만 호출 가능해서 막혀 있고(API로 부르면
# "OpenCode's free tier can only be used in OpenCode" 에러), 대신 같은 게이트웨이의 저가 모델
# (기본값 deepseek-v4-flash, 1M 토큰당 $0.14/$0.28 수준)을 표준 OpenAI 호환 API로 쓴다.
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic")
OPENCODE_MODEL = os.environ.get("OPENCODE_MODEL", "deepseek-v4-flash")
OPENCODE_BASE_URL = "https://opencode.ai/zen/v1"

SYSTEM_PROMPT = """너는 사용자의 개인 세컨드 브레인(Obsidian 위키 노트)을 근거로 답하는 상담 도우미다.
아래 [근거 문서]에 있는 내용만 근거로 답하고, 근거에 없는 내용은 추측하지 말고 "이 vault에서는 근거를 못 찾았다"고 솔직히 말해라.
[이전 기억]은 과거 상담에서 이미 확인된 사용자의 결정·선호·반복되는 고민이다 — 답변 맥락을 이어가는 데 참고하되, vault 근거인 것처럼 인용하지는 마라.
답변 끝에 어떤 노트(제목)를 근거로 썼는지 출처를 밝혀라."""


def build_llm():
    if LLM_PROVIDER == "opencode":
        return ChatOpenAI(
            model=OPENCODE_MODEL,
            api_key=os.environ["OPENCODE_API_KEY"],
            base_url=OPENCODE_BASE_URL,
        )
    return ChatAnthropic(model="claude-sonnet-5")


def get_chain():
    embeddings = HuggingFaceEmbeddings(model_name="jhgan/ko-sroberta-multitask")
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=PERSIST_DIR,
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    llm = build_llm()
    return retriever, llm


def _extract_text(content) -> str:
    """claude-sonnet-5는 복잡한 질문에서 thinking 블록을 섞어 content를 리스트로 반환하기도 한다.
    UI/로그에는 답변 텍스트만 남기고 thinking 블록은 버린다."""
    if isinstance(content, str):
        return content
    parts = [
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return "\n".join(parts)


def retrieve_context(question: str, retriever) -> tuple[str, list[str]]:
    docs = retriever.invoke(question)
    context = "\n\n---\n\n".join(
        f"[{d.metadata.get('title')}]\n{d.page_content}" for d in docs
    )
    sources = sorted({d.metadata.get("title") for d in docs})
    return context, sources


def memory_text() -> str:
    memory_items = load_memory()
    return (
        "\n".join(f"- ({m['type']}) {m['content']}" for m in memory_items)
        or "(아직 없음)"
    )


def ask(question: str, retriever, llm) -> dict:
    context, sources = retrieve_context(question, retriever)

    messages = [
        ("system", SYSTEM_PROMPT),
        (
            "human",
            f"[이전 기억]\n{memory_text()}\n\n[근거 문서]\n{context}\n\n[질문]\n{question}",
        ),
    ]
    response = llm.invoke(messages)
    return {"answer": _extract_text(response.content), "sources": sources}


if __name__ == "__main__":
    retriever, llm = get_chain()
    while True:
        q = input("\n질문 (종료: exit): ")
        if q.strip().lower() == "exit":
            break
        result = ask(q, retriever, llm)
        print(f"\n답변: {result['answer']}")
        print(f"출처: {', '.join(result['sources'])}")
