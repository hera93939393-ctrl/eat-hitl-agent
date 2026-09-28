"""OpenAI API로 1차 판정근거 문구를 생성하는 헬퍼.

판정 자체(자동승인/보완요청/사람확인필요)는 agent.py의 규칙 기반 로직이 그대로 계산한다.
여기서는 그 판정을 사람이 읽기 좋은 근거 문장으로 설명하는 역할만 OpenAI에 맡긴다.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent / ".env")

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

REGULATION_REFS = {
    "sanction": "공급업체 관리지침 제12조(제재·신고 이력 업체 재심사)",
    "address": "공급업체 관리지침 제9조(사업장 소재지 확인)",
    "license": "공급업체 관리지침 제7조(인허가 유효기간 확인)",
}

_client = None


def _get_client() -> OpenAI | None:
    global _client
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    if _client is None:
        _client = OpenAI(api_key=api_key)
    return _client


def _fallback_reason(verdict: str, missing: list[str], stop_reasons: list[str]) -> str:
    if missing:
        return f"필수서류 누락: {', '.join(missing)}"
    if stop_reasons:
        return "필수서류는 충족했으나 특이사항 확인이 필요함"
    return "필수서류 충족, 특이사항 없음"


def generate_reason(
    case: dict,
    verdict: str,
    stop_reasons: list[str],
    citations: list[str],
    missing: list[str] | None = None,
) -> str:
    """OpenAI를 호출해 판정근거 문장을 생성. 키가 없거나 호출이 실패하면 규칙 기반 문구로 대체."""
    missing = missing or []
    client = _get_client()
    if client is None:
        return _fallback_reason(verdict, missing, stop_reasons)

    prompt = f"""당신은 공공급식통합플랫폼(eaT) 공급업체 등록 서류심사를 보조하는 AI 심사관입니다.
아래는 시스템이 규칙에 따라 이미 내린 판정입니다. 새로운 판정을 내리지 말고, 주어진 판정과
특이사항만 근거로 담당자가 한눈에 이해할 수 있는 판정근거를 한국어 1~2문장으로 작성하세요.
관련 규정이 있으면 문장 안에 자연스럽게 인용하세요.

[업체명] {case['company']}
[제출서류] {', '.join(case['submitted_docs'])}
[신청 시 요청 원문] {case['applicant_note']}
[시스템 판정] {verdict}
[필수서류 누락] {', '.join(missing) if missing else '없음'}
[특이사항] {'; '.join(stop_reasons) if stop_reasons else '없음'}
[관련 규정] {'; '.join(citations) if citations else '해당 없음'}"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text = response.choices[0].message.content
        return text.strip() if text else _fallback_reason(verdict, missing, stop_reasons)
    except Exception as exc:  # noqa: BLE001 - demo-grade fallback, any API failure degrades gracefully
        return f"{_fallback_reason(verdict, missing, stop_reasons)} (LLM 호출 실패: {exc})"
