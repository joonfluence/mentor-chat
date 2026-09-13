"""Phase 2: 상담 내역(Phase 4-3부터는 DB)에서 기억할 만한 것을 추출해 memory.json에 저장한다.
매번 전체 상담 내역을 다시 훑어 LLM으로 추출하고, 기존 memory.json과 content 기준으로 중복 없이 병합한다.
"""

import json
from datetime import datetime, timezone

from dotenv import load_dotenv

from chat import _extract_text, build_llm
from db import list_conversations
from memory_store import MEMORY_PATH, load_memory, save_memory

load_dotenv()

EXTRACT_PROMPT = """아래는 사용자와 '멘토와의 대화' 챗봇 사이의 상담 기록이다.
이 대화들에서 앞으로 다른 대화에서도 참고할 가치가 있는 것만 뽑아라:
- decision: 사용자가 이미 내린 결정
- preference: 사용자가 밝힌 선호·방향
- recurring_concern: 반복해서 나오는 고민·주제

규칙:
- 대화에 실제로 있는 내용만 뽑아라. 지어내지 마라.
- 뽑을 게 없으면 빈 배열을 반환해라.
- 각 항목은 한두 문장으로 요약해라.
- 반드시 아래 JSON 배열 형식으로만 답하라. 다른 설명은 붙이지 마라.

[{{"content": "...", "type": "decision|preference|recurring_concern", "source_question": "..."}}]

[상담 기록]
{conversations}
"""


def load_conversations() -> list[dict]:
    return list_conversations()


def extract(conversations: list[dict], llm) -> list[dict]:
    if not conversations:
        return []
    formatted = "\n\n".join(
        f"Q: {c['question']}\nA: {c['answer']}" for c in conversations
    )
    response = llm.invoke(EXTRACT_PROMPT.format(conversations=formatted))
    text = _extract_text(response.content).strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("[") :]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print(f"WARNING: 추출 결과 JSON 파싱 실패, 원문:\n{text}")
        return []


def merge(existing: list[dict], new_items: list[dict]) -> tuple[list[dict], int]:
    existing_contents = {item["content"] for item in existing}
    now = datetime.now(timezone.utc).isoformat()
    added = 0
    for item in new_items:
        content = item.get("content", "")
        if not content or content in existing_contents:
            continue
        existing.append(
            {
                "content": content,
                "type": item.get("type", "recurring_concern"),
                "source_question": item.get("source_question", ""),
                "created_at": now,
            }
        )
        existing_contents.add(content)
        added += 1
    return existing, added


def main():
    conversations = load_conversations()
    print(f"상담 기록 {len(conversations)}건 로드")

    llm = build_llm()
    new_items = extract(conversations, llm)
    print(f"추출된 항목 {len(new_items)}개")

    merged, added = merge(load_memory(), new_items)
    save_memory(merged)
    print(f"memory.json에 {added}개 신규 항목 추가 (전체 {len(merged)}개) → {MEMORY_PATH}")


if __name__ == "__main__":
    main()
