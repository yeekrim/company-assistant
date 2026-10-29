"""평가용 회사 구성. 회사 1곳 = 앱의 회사별 컬렉션 1개.

문서는 공공기관이 공개한 실제 규정 PDF와 업무추진비 집행내역 CSV다 (data/downloads/MANIFEST.md 참고, git 제외).
- c1: 실제 한 기관(서울시설공단)의 규정 3개 + 서울시 본청 업무추진비 2025년 1월
- c2, c3: 서로 다른 기관의 규정을 종류별로 1개씩 묶은 가상의 회사.
  같은 종류 규정(여비 등)은 회사당 1개만 넣어 질문의 정답이 하나로 정해지게 했다.
대학 규정 3개는 이용조건을 확인하지 못해 쓰지 않는다.
- c4: 같은 규정의 여러 버전(국가공무원 복무규정·공무원 여비 규정, law.go.kr 연혁 본문 텍스트).
  문서마다 시행일이 있어 "질문 시점에 시행 중인 버전"을 찾는지 평가한다 (data/downloads/versions/MANIFEST.md).

경비 CSV는 make_corpus.py가 PDF 표로 바꿔 data/corpus/에 저장한다 (앱은 CSV 업로드를 받지 않음).
"""
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
REG = DATA / "downloads" / "regulations"
EXP = DATA / "downloads" / "expenses"
VER = DATA / "downloads" / "versions"
CORPUS = DATA / "corpus"

# 경비 표: (csv 파일, 인코딩, PDF 제목, 남길 컬럼, 행 필터)
# 담당자 이름·전화번호·문서 URL 같은 컬럼은 검색 평가와 관계없어 뺀다.
EXPENSES = {
    "seoul_2025_01": (EXP / "seoul_hq_business_expense_2025.csv", "cp949",
                      "업무추진비 집행내역 (2025년 1월)",
                      ["전체부서명", "집행일시", "집행장소", "집행목적", "집행대상", "결제방법", "집행금액", "비목"],
                      lambda r: r["해당년도"] == "2025" and r["해당월"] == "1"),
    "mou": (EXP / "mou_unification_head_expense.csv", "cp949",
            "기관장 업무추진비 집행내역 (2020~2022)",
            ["사용자", "사용일자", "사용장소", "사용목적(내역)", "사용금액 (원)"], None),
    "nie": (EXP / "nie_executive_expense.csv", "cp949",
            "임원 업무추진비 집행내역",
            ["사용일자", "집행자", "집행내역(목적)", "사용처(지역)", "집행대상자", "집행구분", "인원", "집행금액"], None),
    "daegu": (EXP / "daegu_waterworks_expense.csv", "utf-8-sig",
              "부서 업무추진비 집행내역 (2024년 1~7월)",
              ["부서명", "일자", "집행내역", "금액", "집행장소", "대상인원", "결제방법"], None),
}

COMPANIES = {
    "c1": {
        "name": "서울시설공단",
        "regulations": ["sisul_employment_rules", "sisul_accounting_reg", "sisul_travel_expense_reg"],
        "expenses": ["seoul_2025_01"],
    },
    "c2": {
        "name": "조합 회사 가",
        "regulations": ["lh_travel_expense_reg", "kipa_employment_rules", "knoc_compensation_reg", "kwdi_accounting_reg"],
        "expenses": ["mou"],
    },
    "c3": {
        "name": "조합 회사 나",
        "regulations": ["ekr_travel_expense_reg", "kpx_employment_rules", "kuksiwon_service_reg", "keco_personnel_reg"],
        "expenses": ["nie", "daegu"],
    },
    "c4": {
        "name": "버전 회사 (복무·여비 규정 연혁)",
        "regulations": [],
        "expenses": [],
        # (파일, 시행일 YYYYMMDD) — 업로드할 때 관리자가 입력하는 값에 해당
        "versions": [
            ("복무규정_2016-02-03.txt", 20160203),
            ("복무규정_2020-01-01.txt", 20200101),
            ("복무규정_2026-10-02.txt", 20261002),
            ("여비규정_2016-01-25.txt", 20160125),
            ("여비규정_2023-03-02.txt", 20230302),
            ("여비규정_2026-10-02.txt", 20261002),
        ],
    },
}


def docs(company: str) -> list[Path]:
    """회사에 올라가는 PDF 목록 (규정 원본 + make_corpus.py가 만든 경비 PDF)."""
    return [p for p, _ in dated_docs(company)]


def dated_docs(company: str) -> list[tuple[Path, int]]:
    """(문서, 시행일). 시행일을 모르는 문서는 0 (앱의 '미상'과 같음)."""
    c = COMPANIES[company]
    return ([(REG / f"{n}.pdf", 0) for n in c["regulations"]] + [(CORPUS / f"{n}.pdf", 0) for n in c["expenses"]]
            + [(VER / n, d) for n, d in c.get("versions", [])])
