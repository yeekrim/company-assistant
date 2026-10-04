"""질문 셋과 정답.

- calc: 표 계산형. 정답은 truth CSV에 SQL을 돌려 계산한다 (모델과 무관한 기준값).
- text: 서술형 대조군. 답변에 키워드가 모두 들어 있으면 정답.
"""
from pathlib import Path

import duckdb

TRUTH = Path(__file__).parent / "data" / "truth"

E = f"read_csv_auto('{TRUTH / 'expenses.csv'}')"
L = f"read_csv_auto('{TRUTH / 'leave.csv'}')"

# (id, 질문, 정답 SQL) — 정답 SQL 결과가 숫자면 수치 비교, 문자열이면 포함 여부로 채점
CALC = [
    ("c01", "2026년 1분기(1~3월)에 승인된 경비의 총액은 얼마야?",
     f"SELECT SUM(금액) FROM {E} WHERE 승인상태='승인' AND 사용일 < DATE '2026-04-01'"),
    ("c02", "개발팀의 승인된 경비 건당 평균 금액은 얼마야?",
     f"SELECT AVG(금액) FROM {E} WHERE 승인상태='승인' AND 부서='개발팀'"),
    ("c03", "승인된 경비 총액이 가장 큰 부서는 어디야?",
     f"SELECT 부서 FROM {E} WHERE 승인상태='승인' GROUP BY 부서 ORDER BY SUM(금액) DESC LIMIT 1"),
    ("c04", "반려된 경비 신청은 모두 몇 건이야?",
     f"SELECT COUNT(*) FROM {E} WHERE 승인상태='반려'"),
    ("c05", "경비 내역 중 단일 건으로 가장 큰 금액은 얼마야?",
     f"SELECT MAX(금액) FROM {E}"),
    ("c06", "식대 중 규정상 1인 1회 상한을 초과한 경비는 몇 건이야?",
     f"SELECT COUNT(*) FROM {E} WHERE 항목='식대' AND 금액 > 15000"),
    ("c07", "3월에 사용한 교통비 총액은 얼마야? (승인 상태 무관)",
     f"SELECT SUM(금액) FROM {E} WHERE 항목='교통비' AND month(사용일)=3"),
    ("c08", "마케팅팀의 승인된 접대비 총액은 얼마야?",
     f"SELECT SUM(금액) FROM {E} WHERE 항목='접대비' AND 부서='마케팅팀' AND 승인상태='승인'"),
    ("c09", "잔여 연차가 3일 이하인 직원은 몇 명이야?",
     f"SELECT COUNT(*) FROM {L} WHERE 잔여연차 <= 3"),
    ("c10", "부서별 평균 사용 연차가 가장 높은 부서는 어디야?",
     f"SELECT 부서 FROM {L} GROUP BY 부서 ORDER BY AVG(사용연차) DESC LIMIT 1"),
    ("c11", "전 직원의 사용 연차 합계는 며칠이야?",
     f"SELECT SUM(사용연차) FROM {L}"),
    ("c12", "2020년 1월 1일 이전에 입사한 직원은 몇 명이야?",
     f"SELECT COUNT(*) FROM {L} WHERE 입사일 < DATE '2020-01-01'"),
    ("c13", "아직 대기 상태인 경비의 총액은 얼마야?",
     f"SELECT SUM(금액) FROM {E} WHERE 승인상태='대기'"),
    ("c14", "사번 E0042 직원이 신청한 경비 총액은 얼마야? (승인 상태 무관)",
     f"SELECT COALESCE(SUM(금액), 0) FROM {E} WHERE 사번='E0042'"),
    ("c15", "숙박비 경비의 건당 평균 금액은 얼마야?",
     f"SELECT AVG(금액) FROM {E} WHERE 항목='숙박비'"),
    ("c16", "영업팀 직원은 몇 명이야?",
     f"SELECT COUNT(*) FROM {L} WHERE 부서='영업팀'"),
]

# (id, 질문, 정답에 반드시 들어가야 할 키워드들)
TEXT = [
    ("t01", "업무상 식대 상한은 얼마야?", ["15,000"]),
    ("t02", "경비는 지출일로부터 며칠 이내에 신청해야 해?", ["30"]),
    ("t03", "미사용 연차는 다음 해로 며칠까지 이월할 수 있어?", ["5"]),
    ("t04", "접대비가 50만 원을 넘으면 누구 승인을 받아야 해?", ["대표이사"]),
]


def load() -> list[dict]:
    con = duckdb.connect()
    qs = []
    for qid, q, sql in CALC:
        v = con.execute(sql).fetchone()[0]
        if isinstance(v, (int, float)) or hasattr(v, "__float__"):
            qs.append({"id": qid, "kind": "calc", "question": q, "expected": float(v)})
        else:
            qs.append({"id": qid, "kind": "calc", "question": q, "expected": str(v)})
    for qid, q, kws in TEXT:
        qs.append({"id": qid, "kind": "text", "question": q, "expected": kws})
    return qs


if __name__ == "__main__":
    for q in load():
        print(q["id"], q["expected"], "|", q["question"])
