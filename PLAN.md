# 멘토와의 대화 (mentor-chat)

개인 세컨드 브레인(Obsidian `llm-wiki/wiki/`)을 데이터로 삼아 상담하듯 대화하고, 대화 내역을 기록·기억해서 점점 더 나은 방향을 제안해주는 개인용 RAG 챗봇. 스토어 출시 없음, 로컬 실행 전용.

## 왜 만드는가
- 학습 목적: LangChain(부품 표준화) + LangGraph(제어 흐름·루프·분기) 개념을 직접 손으로 만들어보며 체화.
- 동기부여 목적: vault에 쌓인 내 결정·피드백·패턴을 근거로 "지금 뭘 해야 하나"를 상담받는 도구.
- 데이터 소스는 처음엔 좁게 시작(`llm-wiki/wiki/` 126개 정제 노트) — 파이프라인이 검증되면 이후 `memory/`·GTD 로그·사업 의사결정 로그 같은 더 개인적인 데이터로 확장 가능.

## 전체 프로세스 — 3단계

### Phase 1 — RAG + 상담 기록 (오늘 목표)
질문하면 vault에서 검색해서 답하고, 그 대화를 로컬에 남긴다. 아직 "기억"하거나 "먼저 제안"하지는 않음 — 순수 질의응답 루프만 동작시키는 게 목표.

1. **프로젝트 세팅** — venv, requirements, `.env`(API 키)
2. **데이터 수집(ingest)** — `llm-wiki/wiki/*.md` 읽기 → frontmatter(title/tags/type) + 본문 분리 → 청크 분할
3. **임베딩 + 벡터스토어** — 청크를 임베딩해서 로컬 Chroma DB에 저장 (한 번만 실행하면 되는 배치 스크립트)
4. **검색+답변 체인** — 질문 → 벡터 검색으로 관련 청크 top-k → Claude에게 "이 근거로만 답해라"는 프롬프트로 답변 생성 → 어느 노트에서 가져왔는지 출처 표시
5. **간단한 UI** — Streamlit 채팅 화면 (질문 입력 → 답변 + 출처 표시)
6. **상담 내역 기록** — 매 질문·답변·타임스탬프를 로컬 JSONL 파일에 append (이게 Phase 2의 원재료가 됨)

**완료 기준**: 실제 vault 내용에 대해 질문했을 때, 근거 노트를 인용하며 정확히 답하는 게 눈으로 확인되면 Phase 1 끝.

### Phase 2 — 메모리 저장 (완료, 2026-09-14)
Phase 1의 상담 로그에서 "기억할 만한 것"(반복되는 고민, 이미 내린 결정, 선호)을 LLM으로 추출해 별도 메모리 파일(JSON)에 구조화 저장. 다음 대화부터는 검색 결과 + 이 메모리를 같이 프롬프트에 넣는다 — 지금 이 Claude 세션의 `memory/` 시스템과 개념적으로 동일한 것을 직접 만들어보는 것.

- `memory_store.py` — `memory.json` 읽기/쓰기 공용 모듈
- `extract_memory.py` — `logs/conversations.jsonl` 전체를 LLM으로 훑어 `{content, type: decision|preference|recurring_concern, source_question, created_at}` 형태로 추출, 기존 memory.json과 content 기준 중복 제거 후 병합. **ingest.py와 같은 수동 배치 스크립트** — 대화 후 필요할 때 `python extract_memory.py`로 직접 실행(자동 트리거 아님, 비용·지연 통제 목적으로 의도적 선택).
- `chat.py`의 `ask()`가 매 질문마다 `memory.json`을 읽어 프롬프트의 [이전 기억] 섹션에 포함 — vault 근거와는 구분해서 참고만 하도록 시스템 프롬프트에 명시.
- `memory.json`은 개인 데이터라 `logs/`와 마찬가지로 git-ignore.

### Phase 3 — 방향 제안 (다음)
LangGraph로 판단 노드를 추가: "이 질문이 답만 원하는 건가, 방향 조언이 필요한 맥락인가"를 분기해서, 후자면 검색 결과+메모리를 종합해 먼저 다음 행동을 제안하는 노드로 보낸다. 어제 영상(양실장 8강)의 "노드/엣지로 루프·분기" 개념이 실제로 쓰이는 지점.

## 기술 스택 (결정 사항)
| 구성 요소 | 선택 | 이유 |
|---|---|---|
| 오케스트레이션 | LangChain | 표준 부품(프롬프트 템플릿·모델 연결) |
| LLM | Anthropic Claude (`langchain-anthropic`) | 이미 익숙한 모델, API 키만 있으면 됨 |
| 임베딩 | `jhgan/ko-sroberta-multitask` (로컬, HuggingFace) | 로컬 무료 동작 + 한국어 특화 — 영어 중심 모델(`all-MiniLM-L6-v2`)은 한국어 코퍼스에서 관련 없는 청크가 더 높은 유사도로 뽑히는 문제 확인되어 교체 |
| 벡터스토어 | Chroma (로컬 파일 기반) | 서버 인프라 불필요, 로컬 디렉터리에 저장 |
| UI | Streamlit | 가장 적은 코드로 채팅 화면 구현 |
| 상담 로그 | JSONL 파일 | Phase 2에서 그대로 읽어 처리하기 쉬움 |

## ⚠️ 시작 전 확인 필요
- **ANTHROPIC_API_KEY**: 환경변수에 없음(확인 완료) — 발급/보유 여부 확인 필요. 이게 없으면 4번(답변 생성) 단계를 실제로 못 돌려봄. 콘솔(console.anthropic.com)에서 발급.
- 데이터 소스 경로: `/Users/yijun/Obsidian Vault/llm-wiki/wiki/` (읽기 전용으로만 접근, vault 자체는 수정하지 않음)

## 디렉터리 구조 (예정)
```
mentor-chat/
├── PLAN.md
├── requirements.txt
├── .env.example
├── .gitignore
├── ingest.py        # Phase 1-②③: vault → 청크 → 임베딩 → Chroma 저장 (1회 실행 배치)
├── chat.py          # Phase 1-④: 검색+답변 체인 로직
├── app.py           # Phase 1-⑤: Streamlit UI
├── logs/            # Phase 1-⑥: 상담 내역 JSONL (git-ignore 대상, 개인 데이터)
└── chroma_db/        # 벡터스토어 저장 위치 (git-ignore 대상)
```
