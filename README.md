# eaT 공급업체 서류심사 HITL 승인 에이전트

공공급식통합플랫폼(eaT) 신규 공급업체 등록 서류심사에 사람 승인(HITL)을 붙인 자동화입니다.
필수서류 누락/충족은 자동 처리하고, 제재이력·주소불일치·인허가증 임박(또는 만료) 등
위험 신호가 있는 건만 등록 직전에 멈춰 담당자 승인을 기다립니다.

## 파일 구성

| 파일 | 역할 |
|---|---|
| `cases.py` | 모의 신청 케이스 6건 (실제 개인/기업정보 아님) |
| `agent.py` | LangGraph 그래프 (judge → review(interrupt) → finalize) |
| `llm_judge.py` | OpenAI API로 1차 판정근거 문장을 생성하는 헬퍼 |
| `cli.py` | 터미널 CLI 실행기 (InMemorySaver) |
| `app.py` | Streamlit 웹 데모 (SqliteSaver로 대기 상태 영속화) |

## 실행 방법

```bash
pip install -r requirements.txt
```

### OpenAI API 키 설정

`judge` 단계에서 판정근거 문장을 OpenAI API로 생성합니다(등록 여부 자체는 규칙으로 확정되고,
LLM은 그 이유를 설명하는 문장만 생성합니다). 실행 전 환경변수로 키를 설정하세요. **키를 코드나
저장소에 직접 적지 마세요.**

```powershell
# PowerShell
$env:OPENAI_API_KEY = "sk-..."
```

```bash
# bash
export OPENAI_API_KEY="sk-..."
```

또는 이 폴더에 `.env` 파일을 만들어 `OPENAI_API_KEY=sk-...` 한 줄을 넣어도 됩니다
(`.env`는 `.gitignore`에 있어 저장소에 올라가지 않습니다).

키가 없으면 자동으로 규칙 기반 기본 문구로 대체되어 데모 자체는 계속 동작합니다.
필요하면 `OPENAI_MODEL` 환경변수로 모델을 바꿀 수 있습니다(기본값 `gpt-4o-mini`).

### 1. 터미널 CLI로 실행

```bash
python cli.py
```

케이스마다 순서대로 심사 화면이 출력되고, 사람 확인이 필요한 건에서 1(승인)/2(수정 후 승인)/3(반려)/4(다시 판정) 중 골라 입력합니다.

### 2. 웹 데모(Streamlit)로 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속 → 왼쪽 "승인 대기" 목록에서 건을 선택 → 요청 원문/AI 판정/근거/멈춘 이유를 확인하고 처리 방식을 골라 제출합니다.

대기 상태는 같은 폴더의 `eat_hitl.db`(SQLite)에 저장되어, 앱을 껐다 켜도 처리 중이던 건이 그대로 남아 이어서 처리할 수 있습니다.
