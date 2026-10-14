"""문서 시행일과 질문 속 시점 처리.

시행일은 Chroma 메타데이터에 YYYYMMDD 정수로 저장한다 (숫자 범위 필터 $lte를 쓰기 위해).
시행일을 모르는 문서는 0으로 저장해, 어떤 시점으로 걸러도 검색에서 빠지지 않게 한다.
"""
import calendar
import re
from datetime import date

UNKNOWN = 0

_FULL = re.compile(r"(19\d{2}|20\d{2})\s*(?:년|[.\-/])\s*(\d{1,2})\s*(?:월|[.\-/])\s*(\d{1,2})\s*일?")
_MONTH = re.compile(r"(19\d{2}|20\d{2})\s*년\s*(\d{1,2})\s*월")
_YEAR = re.compile(r"(19\d{2}|20\d{2})\s*년")


def parse_effective_date(value: str | None) -> int:
    """관리자가 입력한 'YYYY-MM-DD' → YYYYMMDD. 빈 값은 UNKNOWN."""
    if value is None or not value.strip():
        return UNKNOWN
    try:
        d = date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError(f"시행일 형식이 올바르지 않습니다 (YYYY-MM-DD): {value}")
    return to_int(d)


def to_int(d: date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


def format_date(value: int) -> str:
    """YYYYMMDD → 'YYYY-MM-DD', UNKNOWN → '미상'."""
    if not value:
        return "미상"
    return f"{value // 10000:04d}-{value // 100 % 100:02d}-{value % 100:02d}"


def query_as_of(query: str) -> int | None:
    """질문에 적힌 시점(그 시점에 시행 중이던 문서를 찾기 위한 기준일). 없으면 None.

    '2016년 3월 2일' → 그날, '2016년 3월' → 그 달 말일, '2016년' → 그해 말일.
    기간을 말하면 그 기간의 끝을 기준으로 삼는다 (그 기간 중 개정됐다면 개정 후 규정).
    '작년'처럼 상대적인 표현은 다루지 않는다.
    """
    for pattern, kind in ((_FULL, "day"), (_MONTH, "month"), (_YEAR, "year")):
        m = pattern.search(query)
        if not m:
            continue
        y = int(m.group(1))
        try:
            if kind == "day":
                return to_int(date(y, int(m.group(2)), int(m.group(3))))
            if kind == "month":
                mo = int(m.group(2))
                return to_int(date(y, mo, calendar.monthrange(y, mo)[1]))
            return to_int(date(y, 12, 31))
        except ValueError:  # 13월 같은 잘못된 날짜는 시점으로 보지 않는다
            continue
    return None
