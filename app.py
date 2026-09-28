"""eaT 공급업체 서류심사 HITL 승인 데모 (Streamlit)."""

import sqlite3
from pathlib import Path

import streamlit as st
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from agent import build_graph
from cases import MOCK_CASES

DB_PATH = str(Path(__file__).parent / "eat_hitl.db")

STATUS_BADGE = {
    "자동승인": ("badge-blue", "⚡"),
    "보완요청": ("badge-gray", "📎"),
    "승인": ("badge-green", "✅"),
    "조건부승인": ("badge-amber", "⚠️"),
    "반려": ("badge-red", "⛔"),
}

CSS = """
<style>
.block-container { padding-top: 2rem; max-width: 1100px; }
.top-pill {
    display: block; text-align: center; margin: 0 auto 1.6rem auto;
    background: linear-gradient(90deg, #3E8EF7, #63B3FF);
    color: #fff; font-weight: 600; font-size: 0.95rem;
    padding: 10px 0; border-radius: 999px; width: fit-content;
    padding-left: 28px; padding-right: 28px;
    box-shadow: 0 4px 14px rgba(63,142,247,0.28);
}
.page-title {
    background: linear-gradient(90deg, #14284B, #1E3A6B);
    color: #fff; font-weight: 800; font-size: 1.7rem;
    padding: 18px 24px; border-radius: 14px; margin-bottom: 1.4rem;
}
.detail-title {
    background: #FFE066; color: #14284B; font-weight: 800; font-size: 1.55rem;
    padding: 16px 22px; border-radius: 10px; margin: 6px 0 18px 0;
    border-left: 6px solid #E0A800;
}
.field-header { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.field-icon {
    width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0;
    background: #EAF3FF; color: #2F6FED; display: flex;
    align-items: center; justify-content: center; font-size: 16px;
}
.field-label { color: #6B7686; font-size: 1.56rem; font-weight: 700; letter-spacing: .02em; text-transform: uppercase; }
.field-value { color: #16233F; font-size: 0.95rem; margin-top: 2px; line-height: 1.4; }
.badge {
    display: inline-block; padding: 3px 12px; border-radius: 999px;
    font-size: 12px; font-weight: 700;
}
.badge-blue { background: #EAF3FF; color: #2F6FED; }
.badge-gray { background: #F1F2F5; color: #5B6472; }
.badge-green { background: #E7F8ED; color: #1E9E4B; }
.badge-amber { background: #FFF4E0; color: #B8720A; }
.badge-red { background: #FDEBEB; color: #E1483F; }
.pass-banner {
    background: #EAF3FF; border-left: 4px solid #2F6FED; color: #14284B;
    padding: 12px 16px; border-radius: 8px; font-size: 0.92rem; margin: 14px 0;
}
section[data-testid="stSidebar"] { background: #F7FAFF; }
div[data-testid="stSidebarUserContent"] h3 { color: #14284B; }
</style>
"""

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


def status_badge_html(status: str) -> str:
    css_class, icon = STATUS_BADGE.get(status, ("badge-gray", "•"))
    return f'<span class="badge {css_class}">{icon} {status}</span>'


def render_field_card(col, icon: str, label: str, value: str) -> None:
    with col:
        with st.container(border=True):
            st.markdown(
                f'<div class="field-header">'
                f'<span class="field-icon">{icon}</span>'
                f'<span class="field-label">{label}</span>'
                f'</div>'
                f'<div class="field-value">{value}</div>',
                unsafe_allow_html=True,
            )


def render_detail(app, case_id: str) -> None:
    snapshot = app.get_state(case_config(case_id))
    payload = snapshot.interrupts[0].value
    case = CASES_BY_ID[case_id]

    st.markdown(
        f'<div class="detail-title">📋 [{case_id}] {case["company"]} 심사 확인</div>',
        unsafe_allow_html=True,
    )

    row1 = st.columns(2)
    render_field_card(row1[0], "📝", "요청 원문", payload["요청 원문"])
    render_field_card(row1[1], "📎", "제출서류", payload["제출서류"])

    row2 = st.columns(2)
    render_field_card(row2[0], "🤖", "AI 판정", payload["AI 판정"])
    render_field_card(row2[1], "📐", "판정근거", payload["판정근거"])

    row3 = st.columns(2)
    stop_col, retry_col = row3
    render_field_card(stop_col, "🛑", "멈춘 이유", payload["멈춘 이유"])
    with retry_col:
        with st.container(border=True):
            if "재판정 횟수" in payload:
                st.markdown(
                    '<div class="field-header">'
                    '<span class="field-icon">🔁</span>'
                    '<span class="field-label">재판정 횟수</span>'
                    '</div>'
                    f'<div class="field-value">{payload["재판정 횟수"]} (최대 3회, 초과 시 자동 반려)</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="field-header">'
                    '<span class="field-icon">🔁</span>'
                    '<span class="field-label">재판정 횟수</span>'
                    '</div>'
                    '<div class="field-value">아직 없음</div>',
                    unsafe_allow_html=True,
                )

    st.markdown(
        f'<div class="pass-banner">🚀 <b>통과시키면</b> — {payload["통과시키면"]}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("**처리 선택**")
    action = st.segmented_control(
        "처리 선택",
        ["승인", "수정 후 승인", "반려", "다시 판정"],
        default="승인",
        key=f"action_{case_id}",
        label_visibility="collapsed",
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
    st.set_page_config(page_title="eaT 서류심사 승인 데모", layout="wide", page_icon="🍚")
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown('<span class="top-pill">HITL Approval Demo</span>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-title">공공급식통합플랫폼(eaT) 공급업체 서류심사</div>',
        unsafe_allow_html=True,
    )

    app = get_app()
    ensure_intake(app)

    pending, done = [], []
    for case in MOCK_CASES:
        snapshot = app.get_state(case_config(case["case_id"]))
        if snapshot.next:
            pending.append(case)
        else:
            done.append((case, snapshot.values))

    st.sidebar.markdown(f"### 🕐 승인 대기 ({len(pending)}건)")
    for case in pending:
        with st.sidebar.container(border=True):
            st.markdown(f"**{case['case_id']} · {case['company']}**")
            if st.button("확인하기", key=f"select_{case['case_id']}", use_container_width=True):
                st.session_state["selected"] = case["case_id"]

    st.sidebar.markdown(f"### ✅ 처리 완료 ({len(done)}건)")
    for case, values in done:
        status = values.get("final_status", "-")
        with st.sidebar.container(border=True):
            st.markdown(
                f"**{case['case_id']} · {case['company']}**  \n{status_badge_html(status)}",
                unsafe_allow_html=True,
            )

    selected_id = st.session_state.get("selected")
    pending_ids = {c["case_id"] for c in pending}

    if selected_id and selected_id in pending_ids:
        render_detail(app, selected_id)
    else:
        st.info("왼쪽 '승인 대기' 목록에서 확인할 건을 선택하세요.")


if __name__ == "__main__":
    main()
