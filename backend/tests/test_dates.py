import pytest

from app.rag.dates import UNKNOWN, format_date, parse_effective_date, query_as_of


def test_parse_effective_date():
    assert parse_effective_date("2023-01-01") == 20230101
    assert parse_effective_date("") == UNKNOWN
    assert parse_effective_date(None) == UNKNOWN


def test_parse_effective_date_rejects_bad_format():
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        parse_effective_date("2023/13/01")


def test_format_date():
    assert format_date(20230105) == "2023-01-05"
    assert format_date(UNKNOWN) == "미상"


@pytest.mark.parametrize("query, expected", [
    ("2016년에는 신입 연차가 며칠이야?", 20161231),
    ("2016년 3월 기준 출장 일비는?", 20160331),
    ("2016년 2월 기준", 20160229),  # 윤년 말일
    ("2016년 3월 2일에 시행된 규정", 20160302),
    ("2016.3.2 당시 규정", 20160302),
    ("2016-03-02 기준", 20160302),
    ("신입 연차는 며칠이야?", None),
    ("2016년 13월", 20161231),  # 잘못된 월은 무시하고 연도만 본다
])
def test_query_as_of(query, expected):
    assert query_as_of(query) == expected
