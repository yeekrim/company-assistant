"""c4(버전 회사) 답변 정답률: 질문 시점에 맞는 버전의 값으로 답하는지 본다.

- A_current: 시행일 기능 전의 앱. 날짜 없이 검색하고, 프롬프트에 날짜 규칙이 없다.
- D_dated: 지금 앱(pipeline.run과 같은 흐름). 질문 시점으로 검색을 거르고,
  조각 앞에 [문서 · 시행일]을 붙이고, 날짜 규칙을 프롬프트에 넣는다.
채점: questions.ANSWER_KEYS의 키워드가 답변에 모두 들어 있으면 정답.
backend/.env의 NVIDIA_API_KEY로 실제 LLM을 호출한다.

    ../../backend/venv/bin/python answer_eval.py
"""
import asyncio
from datetime import date, datetime
from pathlib import Path

from configs import TOP_K, build
from questions import ANSWER_KEYS, QUESTIONS

from common import Trace

from app.rag.dates import format_date, query_as_of, to_int
from app.rag.generator import date_rules, generate

COMPANY = "c4"
RESULTS = Path(__file__).resolve().parent / "results"


def correct(answer: str, keys: list[list[str]]) -> bool:
    return all(any(k in answer for k in group) for group in keys)


async def answer_current(index, question: str) -> str:
    return await generate(question, index.search(question, TOP_K, Trace()), [])


async def answer_dated(index, question: str) -> str:
    as_of = query_as_of(question)
    chunks = index.search_chunks(question, TOP_K)
    context = [f"[문서: {c.source} · 시행일 {format_date(c.effective_date)}]\n{c.text}" for c in chunks]
    rules = date_rules(format_date(as_of or to_int(date.today())), from_query=as_of is not None)
    return await generate(question, context, [], rules)


async def main():
    runs = {"A_current": answer_current, "D_dated": answer_dated}
    rows, score = [], {}
    for name, fn in runs.items():
        index = build(name, COMPANY)
        ok = 0
        for qid, question, hint in QUESTIONS[COMPANY]:
            ans = await fn(index, question)
            hit = correct(ans, ANSWER_KEYS[qid])
            ok += hit
            rows.append((name, qid, hit, question, hint, ans.replace("\n", " ")))
            print(f"{name} {qid} {'O' if hit else 'X'}")
        score[name] = ok

    n = len(QUESTIONS[COMPANY])
    lines = [f"# c4 답변 정답률 ({datetime.now():%Y-%m-%d %H:%M})", "",
             "| 설정 | 전체 | 시점 없는 질문 (q01~q06) | 과거 시점 질문 (q07~q12) |", "|---|---|---|---|"]
    for name in runs:
        mine = [r for r in rows if r[0] == name]
        now = sum(r[2] for r in mine if int(r[1][-2:]) <= 6)
        past = sum(r[2] for r in mine if int(r[1][-2:]) > 6)
        lines.append(f"| {name} | {score[name]}/{n} | {now}/6 | {past}/6 |")
    lines += ["", "## 질문별", "", "| 설정 | 질문 | 정답 | 기대 (hint) | 답변 |", "|---|---|---|---|---|"]
    for name, qid, hit, question, hint, ans in rows:
        lines.append(f"| {name} | {qid} {question} | {'O' if hit else 'X'} | {hint} | {ans[:300]} |")

    report = "\n".join(lines) + "\n"
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"answers-{datetime.now():%Y%m%d-%H%M%S}.md"
    out.write_text(report, encoding="utf-8")
    print("\n".join(lines[:6]))
    print(f"저장: {out}")


if __name__ == "__main__":
    asyncio.run(main())
