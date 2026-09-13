# Phase 1 검증 완료 기록 — RAG + 상담 기록

> 완료일: 2026-09-14. PLAN.md의 Phase 1(순수 질의응답 루프) 전체 동작 검증을 마쳤다.

## 완료 요약

- 데이터 소스: Obsidian vault `llm-wiki/wiki/` 132개 노트
- ingest 실행 → **802 청크**를 로컬 Chroma에 저장
- 검색+답변 체인, Streamlit UI, JSONL 상담 기록 모두 동작 확인
- `logs/conversations.jsonl` 2회 대화 기록 확인

## 검증 내역

| 단계 | 내용 | 결과 |
|---|---|---|
| ③ 체인 | `python chat.py` CLI로 실제 질문 2~3회 → 근거 인용 + 출처 표시 | ✅ |
| ④ UI | `streamlit run app.py` → 브라우저 채팅 + 출처 표시 동작 | ✅ |
| ⑤ 기록 | UI에서 질문 → `logs/conversations.jsonl` 생성·append 확인 | ✅ (2 entry) |
| ⑥ 기준 | 실제 vault 내용 질문에 근거 노트 인용하며 정확히 답함 | ✅ |

## 시스템 구성 (동작 확인된 사실)

- **임베딩**: `jhgan/ko-sroberta-multitask` (로컬, API 불필요)
- **벡터스토어**: Chroma, 컬렉션 `mentor_wiki`, `chroma_db/` 에 저장 (188KB sqlite)
- **검색**: top-k=5, 메타데이터(slug·제목·태그·타입·섹션) 유지
- **LLM**: Claude (`chat.py`의 `ChatAnthropic`, `.env`의 `ANTHROPIC_API_KEY`)
- **답변 규칙**: 근거 문서에 없는 건 "근거를 못 찾았다"고 솔직히 답함 (시스템 프롬프트)

## 실행 명령 레퍼런스

```bash
# 재수집 (청크 구성 바뀌면 컬렉션 리셋 후 재생성)
python ingest.py

# CLI 테스트
python chat.py

# UI
streamlit run app.py
```

## Phase 2 발판

- `logs/conversations.jsonl`이 상담 내역 원재료 (타임스탬프·질문·답변·출처 포함)
- 출처 목록이 "어떤 노트가 트리거됐는지" 추적 가능 → 메모리 추출 입력으로 그대로 사용 가능

## 참고 메모 (2026-09-14 기준)

- `langchain-community`의 `HuggingFaceEmbeddings`가 sunset 예정(경고). 장기적으로 `langchain-huggingface`로 전환 가능 — Phase 2 진행 중 필요해지면 처리.
- vault 노트 수가 PLAN 작성 시점(126개)보다 132개로 늘어남.