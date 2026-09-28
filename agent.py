"""eaT 공급업체 서류심사 HITL 에이전트 (LangGraph interrupt/resume 기반)."""

from typing import Optional, TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

from cases import REQUIRED_DOCS
from llm_judge import REGULATION_REFS, generate_reason

MAX_RETRY = 3


class SupplierCase(TypedDict):
    case_id: str
    company: str
    applicant_note: str
    submitted_docs: list[str]
    has_sanction_history: bool
    address_mismatch: bool
    license_days_left: int


class ReviewState(TypedDict, total=False):
    case: SupplierCase
    verdict: str
    reason: str
    stop_reasons: list[str]
    decision: dict
    retry_count: int
    final_status: str
    final_reason: str
    final_conditions: Optional[str]


def judge(state: ReviewState) -> dict:
    """1차 판정. 자동/사람확인 여부는 규칙으로 확정하고(계산 가능한 기준), 그 근거 문장만
    OpenAI API로 생성한다 — LLM 출력이 등록 여부 자체를 좌우하지 않도록 분리."""
    case = state["case"]
    missing = [d for d in REQUIRED_DOCS if d not in case["submitted_docs"]]
    if missing:
        reason = generate_reason(case, "보완요청", [], [], missing=missing)
        return {"verdict": "보완요청", "reason": reason, "stop_reasons": []}

    stop_reasons = []
    citations = []
    if case["has_sanction_history"]:
        stop_reasons.append("최근 1년 내 제재/신고 이력 있음")
        citations.append(REGULATION_REFS["sanction"])
    if case["address_mismatch"]:
        stop_reasons.append("사업자등록 주소와 실제 시설 소재지 불일치")
        citations.append(REGULATION_REFS["address"])
    if case["license_days_left"] <= 0:
        stop_reasons.append("인허가증 유효기간 만료")
        citations.append(REGULATION_REFS["license"])
    elif case["license_days_left"] <= 30:
        stop_reasons.append(f"인허가증 유효기간 임박(잔여 {case['license_days_left']}일)")
        citations.append(REGULATION_REFS["license"])

    verdict = "사람확인필요" if stop_reasons else "자동승인"
    reason = generate_reason(case, verdict, stop_reasons, citations)
    return {"verdict": verdict, "reason": reason, "stop_reasons": stop_reasons}


def route_after_judge(state: ReviewState) -> str:
    return "review" if state["verdict"] == "사람확인필요" else "finalize"


def review(state: ReviewState) -> dict:
    case = state["case"]
    retry_count = state.get("retry_count", 0)

    screen = {
        "업체명": case["company"],
        "요청 원문": case["applicant_note"],
        "제출서류": ", ".join(case["submitted_docs"]),
        "AI 판정": state["verdict"],
        "판정근거": state["reason"],
        "멈춘 이유": "; ".join(state["stop_reasons"]),
        "통과시키면": f"{case['company']}가 공공급식통합플랫폼 공급업체로 등록됩니다",
    }
    if retry_count:
        screen["재판정 횟수"] = f"{retry_count}회"

    answer = interrupt(screen)
    action = answer.get("action")

    if action == "approve":
        return {
            "decision": answer,
            "final_status": "승인",
            "final_reason": state["reason"],
            "final_conditions": None,
        }

    if action == "modify":
        condition = answer.get("condition", "")
        return {
            "decision": answer,
            "final_status": "조건부승인",
            "final_reason": state["reason"],
            "final_conditions": condition,
        }

    if action == "reject":
        return {
            "decision": answer,
            "final_status": "반려",
            "final_reason": answer.get("reason", ""),
        }

    if action == "retry":
        retry_count += 1
        if retry_count >= MAX_RETRY:
            return {
                "decision": answer,
                "retry_count": retry_count,
                "final_status": "반려",
                "final_reason": f"재판정 {MAX_RETRY}회 초과로 자동 반려",
            }
        return {"decision": answer, "retry_count": retry_count}

    raise ValueError(f"알 수 없는 담당자 응답: {action!r}")


def route_after_review(state: ReviewState) -> str:
    return "finalize" if state.get("final_status") else "review"


def finalize(state: ReviewState) -> dict:
    if state["verdict"] == "자동승인":
        return {"final_status": "자동승인", "final_reason": state["reason"]}
    if state["verdict"] == "보완요청":
        return {"final_status": "보완요청", "final_reason": state["reason"]}
    return {}


def build_graph() -> StateGraph:
    g = StateGraph(ReviewState)
    g.add_node("judge", judge)
    g.add_node("review", review)
    g.add_node("finalize", finalize)

    g.add_edge(START, "judge")
    g.add_conditional_edges("judge", route_after_judge, ["review", "finalize"])
    g.add_conditional_edges("review", route_after_review, ["review", "finalize"])
    g.add_edge("finalize", END)
    return g
