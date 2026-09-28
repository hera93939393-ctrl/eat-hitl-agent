"""터미널에서 서류심사 HITL 에이전트를 실행하는 CLI."""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from agent import build_graph
from cases import MOCK_CASES


def ask_terminal(screen: dict) -> dict:
    print("\n" + "=" * 60)
    print("[심사 확인 요청]")
    for key, value in screen.items():
        print(f"{key}: {value}")
    print("-" * 60)
    print("[1] 승인   [2] 수정 후 승인(조건부)   [3] 반려   [4] 다시 판정")
    choice = input("선택 (1-4): ").strip().lstrip("﻿")

    if choice == "1":
        return {"action": "approve"}
    if choice == "2":
        condition = input("승인 조건을 입력하세요: ").strip()
        return {"action": "modify", "condition": condition}
    if choice == "3":
        reason = input("반려 사유를 입력하세요: ").strip()
        return {"action": "reject", "reason": reason}
    if choice == "4":
        note = input("재검토 지시사항을 입력하세요: ").strip()
        return {"action": "retry", "note": note}

    print("알 수 없는 입력입니다. 다시 판정으로 처리합니다.")
    return {"action": "retry", "note": ""}


def run_case(app, case: dict) -> dict:
    config = {"configurable": {"thread_id": case["case_id"]}}
    result = app.invoke({"case": case, "retry_count": 0}, config=config)

    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        answer = ask_terminal(payload)
        result = app.invoke(Command(resume=answer), config=config)

    return result


def main() -> None:
    app = build_graph().compile(checkpointer=InMemorySaver())

    print(f"총 {len(MOCK_CASES)}건의 서류심사를 진행합니다.")
    summary = []

    for case in MOCK_CASES:
        print(f"\n\n### 케이스 {case['case_id']}: {case['company']} ###")
        result = run_case(app, case)
        status = result.get("final_status")
        reason = result.get("final_reason", "")
        conditions = result.get("final_conditions")
        print(f">>> 최종 결과: {status} / 사유: {reason}" + (f" / 조건: {conditions}" if conditions else ""))
        summary.append((case["case_id"], case["company"], status, reason, conditions))

    print("\n\n=== 전체 처리 결과 요약 ===")
    for case_id, company, status, reason, conditions in summary:
        line = f"{case_id} | {company} | {status} | {reason}"
        if conditions:
            line += f" | 조건: {conditions}"
        print(line)


if __name__ == "__main__":
    main()
