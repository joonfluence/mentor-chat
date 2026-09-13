"""Phase 2: 상담 기록에서 추출한 기억(memory.json)을 읽고 쓰는 공용 모듈."""

import json
import os

MEMORY_PATH = os.path.join(os.path.dirname(__file__), "memory.json")


def load_memory() -> list[dict]:
    if not os.path.exists(MEMORY_PATH):
        return []
    with open(MEMORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_memory(items: list[dict]) -> None:
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
