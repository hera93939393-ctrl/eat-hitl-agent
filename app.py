"""eaT 공급업체 서류심사 HITL 승인 데모 (Streamlit)."""

import sqlite3
from pathlib import Path

import streamlit as st
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from agent import build_graph
from cases import MOCK_CASES

DB_PATH = str(Path(__file__).parent / "eat_hitl.db")

CASES_BY_ID = {c["case_id"]: c for c in MOCK_CASES}


@st.cache_resource
def get_app():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return build_graph().compile(checkpointer=checkpointer)


def case_config(case_id: str) -> dict:
    return {"configurable": {"thread_id": case_id}}


def ensure_intake(app) -> None:
    for case in MOCK_CASES:
        config = case_config(case["case_id"])
        snapshot = app.get_state(config)
        if not snapshot.values:
            app.invoke({"case": case, "retry_count": 0}, config=config)


def render_detail(app, case_id: str) -> None:
    snapshot = app.get_state(case_config(case_id))
    payload = snapshot.interrupts[0].value
    case = CASES_BY_ID[case_id]

    st.subheader(f"[{case_id}] {case['company']} 심사 확인")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**요청 원문**\n\n{payload['요청 원문']}")
        st.markdown(f"**제출서류**: {payload['제출서류']}")
    with col2:
        st.markdown(f"**AI 판정**: {payload['AI 판정']}")
        st.markdown(f"**판정근거**: {payload['판정근거']}")
        st.markdown(f"**멈춘 이유**: {payload['멈춘 이유']}")

    st.warning(f"통과시키면: {payload['통과시키면']}")
    if "재판정 횟수" in payload:
        st.caption(f"재판정 횟수: {payload['재판정 횟수']} (최대 3회, 초과 시 자동 반려)")

    action = st.radio(
        "처리 선택",
        ["승인", "수정 후 승인", "반려", "다시 판정"],
        key=f"action_{case_id}",
        horizontal=True,
    )

    extra = ""
    if action == "수정 후 승인":
        extra = st.text_input("승인 조건 (예: 유효기간 단축 등록)", key=f"cond_{case_id}")
    elif action == "반려":
        extra = st.text_input("반려 사유", key=f"reason_{case_id}")
    elif action == "다시 판정":
        extra = st.text_input("재검토 지시사항", key=f"note_{case_id}")

    if st.button("제출", key=f"submit_{case_id}", type="primary"):
        answer_map = {
            "승인": {"action": "approve"},
            "수정 후 승인": {"action": "modify", "condition": extra},
            "반려": {"action": "reject", "reason": extra},
            "다시 판정": {"action": "retry", "note": extra},
        }
        app.invoke(Command(resume=answer_map[action]), config=case_config(case_id))

        new_snapshot = app.get_state(case_config(case_id))
        if not new_snapshot.next:
            st.session_state.pop("selected", None)
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="eaT 서류심사 승인 데모", layout="wide")
    st.title("공공급식통합플랫폼(eaT) 공급업체 서류심사 — 승인 데모")

    app = get_app()
    ensure_intake(app)

    pending, done = [], []
    for case in MOCK_CASES:
        snapshot = app.get_state(case_config(case["case_id"]))
        if snapshot.next:
            pending.append(case)
        else:
            done.append((case, snapshot.values))

    st.sidebar.header(f"승인 대기 ({len(pending)}건)")
    for case in pending:
        label = f"{case['case_id']} · {case['company']}"
        if st.sidebar.button(label, key=f"select_{case['case_id']}", use_container_width=True):
            st.session_state["selected"] = case["case_id"]

    st.sidebar.header(f"처리 완료 ({len(done)}건)")
    for case, values in done:
        status = values.get("final_status", "-")
        st.sidebar.write(f"{case['case_id']} · {case['company']} → **{status}**")

    selected_id = st.session_state.get("selected")
    pending_ids = {c["case_id"] for c in pending}

    if selected_id and selected_id in pending_ids:
        render_detail(app, selected_id)
    else:
        st.info("왼쪽 '승인 대기' 목록에서 확인할 건을 선택하세요.")


if __name__ == "__main__":
    main()
