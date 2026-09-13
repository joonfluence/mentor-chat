"""Phase 1-④: 검색+답변 체인.
질문을 받으면 벡터스토어에서 관련 청크를 찾고, 그 근거로만 답하도록 Claude에게 요청한다.
"""

import os

from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_anthropic import ChatAnthropic

load_dotenv()

PERSIST_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION_NAME = "mentor_wiki"

SYSTEM_PROMPT = """너는 사용자의 개인 세컨드 브레인(Obsidian 위키 노트)을 근거로 답하는 상담 도우미다.
아래 [근거 문서]에 있는 내용만 근거로 답하고, 근거에 없는 내용은 추측하지 말고 "이 vault에서는 근거를 못 찾았다"고 솔직히 말해라.
답변 끝에 어떤 노트(제목)를 근거로 썼는지 출처를 밝혀라."""


def get_chain():
    embeddings = HuggingFaceEmbeddings(model_name="jhgan/ko-sroberta-multitask")
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=PERSIST_DIR,
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    llm = ChatAnthropic(model="claude-sonnet-5")
    return retriever, llm


def ask(question: str, retriever, llm) -> dict:
    docs = retriever.invoke(question)
    context = "\n\n---\n\n".join(
        f"[{d.metadata.get('title')}]\n{d.page_content}" for d in docs
    )
    sources = sorted({d.metadata.get("title") for d in docs})

    messages = [
        ("system", SYSTEM_PROMPT),
        ("human", f"[근거 문서]\n{context}\n\n[질문]\n{question}"),
    ]
    response = llm.invoke(messages)
    return {"answer": response.content, "sources": sources}


if __name__ == "__main__":
    retriever, llm = get_chain()
    while True:
        q = input("\n질문 (종료: exit): ")
        if q.strip().lower() == "exit":
            break
        result = ask(q, retriever, llm)
        print(f"\n답변: {result['answer']}")
        print(f"출처: {', '.join(result['sources'])}")
