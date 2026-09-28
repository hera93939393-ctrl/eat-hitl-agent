"""공공급식통합플랫폼(eaT) 공급업체 신규 등록 서류심사 모의 케이스."""

REQUIRED_DOCS = ["사업자등록증", "통장사본", "식품관련인허가증"]

MOCK_CASES = [
    {
        "case_id": "C1",
        "company": "가나식품(주)",
        "applicant_note": "공공급식통합플랫폼 신규 공급업체 등록을 신청합니다. 요청 서류 모두 첨부하였습니다.",
        "submitted_docs": ["사업자등록증", "통장사본", "식품관련인허가증"],
        "has_sanction_history": False,
        "address_mismatch": False,
        "license_days_left": 200,
    },
    {
        "case_id": "C2",
        "company": "다라농산",
        "applicant_note": "신규 등록 신청드립니다. 통장사본은 은행 시스템 점검으로 이번 주 내 추가 제출 예정입니다.",
        "submitted_docs": ["사업자등록증", "식품관련인허가증"],  # 통장사본 누락
        "has_sanction_history": False,
        "address_mismatch": False,
        "license_days_left": 150,
    },
    {
        "case_id": "C3",
        "company": "마바유통",
        "applicant_note": "작년 이물 신고 건은 원인 조치를 완료했습니다. 신규 등록 부탁드립니다.",
        "submitted_docs": ["사업자등록증", "통장사본", "식품관련인허가증"],
        "has_sanction_history": True,  # 최근 1년 내 제재 이력
        "address_mismatch": False,
        "license_days_left": 100,
    },
    {
        "case_id": "C4",
        "company": "사아식자재",
        "applicant_note": "본사 주소지와 실제 물류창고 주소가 달라 서류상 주소가 다르게 보일 수 있습니다.",
        "submitted_docs": ["사업자등록증", "통장사본", "식품관련인허가증"],
        "has_sanction_history": False,
        "address_mismatch": True,  # 사업자등록 주소 ≠ 시설 소재지
        "license_days_left": 300,
    },
    {
        "case_id": "C5",
        "company": "자차급식",
        "applicant_note": "인허가증 갱신 절차는 진행 중이며 곧 새 인허가증이 나올 예정입니다.",
        "submitted_docs": ["사업자등록증", "통장사본", "식품관련인허가증"],
        "has_sanction_history": False,
        "address_mismatch": False,
        "license_days_left": 15,  # 인허가증 유효기간 임박
    },
    {
        "case_id": "C6",
        "company": "카타물산",
        "applicant_note": "인허가증 갱신 신청은 접수했으나 아직 발급 전입니다. 우선 등록 부탁드립니다.",
        "submitted_docs": ["사업자등록증", "통장사본", "식품관련인허가증"],
        "has_sanction_history": False,
        "address_mismatch": False,
        "license_days_left": -5,  # 인허가증 만료
    },
]
