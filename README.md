# 멘토와의 대화 (mentor-chat)

개인 세컨드 브레인(Obsidian `llm-wiki/wiki/`)을 데이터로 삼아 상담하듯 대화하고, 대화 내역을 기록·기억해서 점점 더 나은 방향을 제안해주는 개인용 RAG 챗봇. 로컬 실행 전용, 스토어 출시 없음.

LangChain(부품 표준화)과 LangGraph(제어 흐름·조건부 분기)를 직접 손으로 만들어보며 익히는 학습 목적과, vault에 쌓인 결정·피드백·패턴을 근거로 "지금 뭘 해야 하나"를 상담받는 동기부여 목적으로 만들었다.

## 무엇을 하는가

1. **질문하면 vault에서 검색해서 근거를 인용하며 답한다.** (Phase 1)
2. **대화가 쌓일수록 결정·선호·반복되는 고민을 기억한다.** 다음 대화부터 이 기억을 참고한다. (Phase 2)
3. **질문 유형에 따라 답변 스타일이 갈린다.** 단순 정보 질문엔 근거만으로 답하고, 방향 조언이 필요한 맥락이면 근거+기억을 종합해 구체적인 다음 행동까지 제안한다. (Phase 3, LangGraph 조건부 엣지)
4. **아젠다(주제·목표)를 정해두고 상담하면, 지난 상담과 비교한 진행상황 피드백을 준다.** "지난번엔 X였는데 지금은 Y네요" 식의 연속성 있는 코칭. (Phase 4)
5. Claude 대신 다른 LLM으로 바꿀 수 있고, vault 근거 외에 실시간 웹 검색도 더할 수 있다. (Phase 4)

## 아키텍처

```
질문
 │
 ▼
retrieve (vault 벡터 검색, Chroma + ko-sroberta)
 │
 ▼
web_search (Tavily, 키 없으면 스킵)
 │
 ├─ 아젠다 지정됨 ──────────────► agenda_context (이전 상담 이력 로드)
 │                                        │
 └─ 아젠다 없음 ──► classify ──┐          │
                    (info/direction)       │
                                ▼          ▼
                          answer_info   answer_direction
                                │          │
                                └────┬─────┘
                                     ▼
                                   답변 + 출처
```

질문·답변·출처·아젠다는 SQLite(`mentor_chat.db`)에 저장되고, 별도 배치(`extract_memory.py`)로 그 안에서 기억할 만한 것만 뽑아 `memory.json`에 구조화 저장한다.

## 기술 스택

| 구성 요소 | 선택 |
|---|---|
| 오케스트레이션 | LangChain + LangGraph |
| LLM | Anthropic Claude (기본) 또는 opencode Zen 게이트웨이 (`LLM_PROVIDER=opencode`) |
| 임베딩 | `jhgan/ko-sroberta-multitask` (로컬, 한국어 특화) |
| 벡터스토어 | Chroma (로컬 파일) |
| 웹 검색 | Tavily (선택, 키 없으면 자동 스킵) |
| 상담 DB | SQLite (`mentor_chat.db`) |
| UI | Streamlit |

## 시작하기

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env
# .env에 ANTHROPIC_API_KEY, VAULT_WIKI_PATH 채우기
# (선택) LLM_PROVIDER=opencode + OPENCODE_API_KEY로 Claude 대신 opencode Zen 사용
# (선택) TAVILY_API_KEY로 웹 검색 켜기

.venv/bin/python ingest.py      # vault 노트를 청크·임베딩해서 Chroma에 저장 (최초 1회)
.venv/bin/streamlit run app.py  # http://localhost:8501
```

CLI로 바로 테스트하려면 `python chat.py`(단선 파이프라인, 분기 없음) 또는 `python graph.py`(Phase 3~4 분기 포함)를 쓴다.

대화가 쌓이면 `python extract_memory.py`로 기억을 갱신한다 (수동 실행, 자동 트리거 아님).

## 데이터 소스 범위

`llm-wiki/wiki/`(정제된 소스 요약 노트)만 읽는다. 이력서·이직·사업 결정 같은 민감한 개인 맥락이 담긴 Obsidian Vault의 `memory/` 폴더나 다른 노트는 참조하지 않는다 — 처음부터 좁은 범위로 시작하기로 한 결정.

## 진행 상황

Phase 1~4 전 항목 완료. 자세한 설계 배경·의사결정 기록은 [PLAN.md](PLAN.md) 참고.
