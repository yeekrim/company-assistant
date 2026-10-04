"""가짜 사내 문서 생성: 규정 본문 + 경비 내역 표(500행) + 연차 현황 표(200행).

- data/사내규정_및_현황.pdf : 실험 입력 문서 (세 방식 모두 이 PDF를 기준으로 처리)
- data/truth/*.csv         : 정답 계산용 원본 (모델에게는 절대 주지 않음)
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).parent
DATA = ROOT / "data"
TRUTH = DATA / "truth"
PDF_PATH = DATA / "사내규정_및_현황.pdf"

SEED = 42
DEPTS = ["영업팀", "개발팀", "인사팀", "재무팀", "마케팅팀"]
LAST = list("김이박최정강조윤장임한오서신권황안송류홍")
FIRST = ["민준", "서연", "도윤", "지우", "하준", "서윤", "시우", "하은", "주원", "지유",
         "예준", "수아", "지호", "채원", "준서", "지민", "현우", "다은", "건우", "소율"]
CATEGORIES = {  # 항목: (최소, 최대) 금액
    "교통비": (3_000, 80_000),
    "식대": (6_000, 25_000),
    "숙박비": (60_000, 180_000),
    "도서구입": (12_000, 60_000),
    "장비구매": (50_000, 1_500_000),
    "접대비": (40_000, 600_000),
}
STATUSES = ["승인"] * 7 + ["반려"] * 1 + ["대기"] * 2

POLICY = [
    ("제1장 경비 규정", [
        "제1조(목적) 이 규정은 임직원이 업무 수행 중 지출한 경비의 신청, 승인 및 정산 절차를 정함을 목적으로 한다.",
        "제2조(신청 기한) 경비는 지출일로부터 30일 이내에 사내 경비 시스템을 통해 신청하여야 한다. 기한을 넘긴 신청은 재무팀장의 별도 승인이 없으면 반려된다.",
        "제3조(식대) 업무상 식대는 1인 1회 15,000원을 상한으로 한다. 상한을 초과한 금액은 개인 부담으로 한다.",
        "제4조(숙박비) 출장 숙박비는 1박 120,000원을 상한으로 하며, 해외 출장은 별도 기준을 따른다.",
        "제5조(접대비) 접대비는 사전에 소속 부서장의 승인을 받아야 하며, 1회 500,000원을 초과하는 경우 대표이사의 승인을 받아야 한다.",
        "제6조(장비구매) 1,000,000원 이상의 장비 구매는 자산으로 등록하며, 퇴사 시 반납하여야 한다.",
        "제7조(승인 상태) 경비 신청 건은 '승인', '반려', '대기' 중 하나의 상태를 가진다. '대기'는 부서장 검토 전인 건을 말한다.",
    ]),
    ("제2장 연차 규정", [
        "제8조(연차 부여) 연차는 매년 1월 1일에 근속 연수에 따라 15일에서 최대 25일까지 부여한다.",
        "제9조(연차 이월) 미사용 연차는 다음 해로 최대 5일까지 이월할 수 있으며, 이월된 연차는 3월 31일까지 사용하여야 한다.",
        "제10조(연차 신청) 연차는 사용일 3일 전까지 신청하여야 하며, 반차는 0.5일로 계산한다.",
    ]),
]


def make_people(rng: random.Random, n: int) -> list[dict]:
    people, used = [], set()
    for i in range(1, n + 1):
        while True:
            name = rng.choice(LAST) + rng.choice(FIRST)
            if name not in used:
                used.add(name)
                break
        people.append({"사번": f"E{i:04d}", "이름": name, "부서": rng.choice(DEPTS)})
    return people


def make_expenses(rng: random.Random, people: list[dict], n: int) -> list[dict]:
    start = date(2026, 1, 1)
    rows = []
    for i in range(1, n + 1):
        p = rng.choice(people)
        cat = rng.choice(list(CATEGORIES))
        lo, hi = CATEGORIES[cat]
        rows.append({
            "경비ID": f"X{i:04d}",
            "사번": p["사번"],
            "이름": p["이름"],
            "부서": p["부서"],
            "사용일": (start + timedelta(days=rng.randrange(181))).isoformat(),
            "항목": cat,
            "금액": rng.randrange(lo, hi, 100),
            "승인상태": rng.choice(STATUSES),
        })
    return rows


def make_leave(rng: random.Random, people: list[dict]) -> list[dict]:
    rows = []
    for p in people:
        joined = date(2012, 1, 1) + timedelta(days=rng.randrange(365 * 14))
        years = max(0, 2026 - joined.year)
        granted = min(25, 15 + years // 2)
        used = rng.randrange(0, granted * 2 + 1) / 2  # 반차 단위
        rows.append({
            "사번": p["사번"], "이름": p["이름"], "부서": p["부서"],
            "입사일": joined.isoformat(),
            "부여연차": granted, "사용연차": used, "잔여연차": granted - used,
        })
    return rows


def write_csv(path: Path, rows: list[dict]):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def fmt(v):
    if isinstance(v, int):
        return f"{v:,}"
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def write_pdf(expenses: list[dict], leave: list[dict]):
    pdfmetrics.registerFont(UnicodeCIDFont("HYGothic-Medium"))  # 내장 한글 CID 폰트
    h1 = ParagraphStyle("h1", fontName="HYGothic-Medium", fontSize=15, leading=22, spaceAfter=8)
    body = ParagraphStyle("body", fontName="HYGothic-Medium", fontSize=10, leading=16, spaceAfter=4)
    style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "HYGothic-Medium"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
    ])

    story = [Paragraph("사내 경비·연차 규정 및 2026년 상반기 현황", h1), Spacer(1, 6)]
    for title, articles in POLICY:
        story.append(Paragraph(title, h1))
        story += [Paragraph(a, body) for a in articles]
    for title, rows in [("부록 1. 2026년 상반기 경비 신청 내역", expenses),
                        ("부록 2. 직원별 연차 사용 현황 (2026년 6월 30일 기준)", leave)]:
        story += [PageBreak(), Paragraph(title, h1)]
        data = [list(rows[0])] + [[fmt(v) for v in r.values()] for r in rows]
        story.append(Table(data, repeatRows=1, style=style))  # 페이지마다 헤더 반복

    SimpleDocTemplate(str(PDF_PATH), pagesize=A4).build(story)


def main():
    rng = random.Random(SEED)
    TRUTH.mkdir(parents=True, exist_ok=True)
    people = make_people(rng, 200)
    expenses = make_expenses(rng, people, 500)
    leave = make_leave(rng, people)
    write_csv(TRUTH / "expenses.csv", expenses)
    write_csv(TRUTH / "leave.csv", leave)
    write_pdf(expenses, leave)
    print(f"생성 완료: {PDF_PATH} (경비 {len(expenses)}행, 연차 {len(leave)}행)")


if __name__ == "__main__":
    main()
