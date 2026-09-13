"""1회성: Phase 1~2의 logs/conversations.jsonl을 Phase 4-3의 SQLite DB로 이관한다."""

import json
import os

from db import save_conversation

LOG_PATH = os.path.join(os.path.dirname(__file__), "logs", "conversations.jsonl")


def main():
    if not os.path.exists(LOG_PATH):
        print("옮길 로그 없음")
        return
    count = 0
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            save_conversation(
                question=entry["question"],
                answer=entry["answer"],
                sources=entry.get("sources", []),
                web_sources=entry.get("web_sources", []),
                route=entry.get("route", "info"),
                agenda_id=None,
                timestamp=entry.get("timestamp"),
            )
            count += 1
    print(f"{count}건을 DB로 이관 완료 → {os.path.join(os.path.dirname(__file__), 'mentor_chat.db')}")


if __name__ == "__main__":
    main()
