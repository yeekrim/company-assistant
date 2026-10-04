"""current / kaizen-mae / kaizen-go 벤치마크.

사용법 (company-assistant/backend/venv 기준):
    python run_bench.py                         # 전체 실행
    python run_bench.py --variants kaizen-go    # 일부 방식만
    python run_bench.py --only c01,c06,t01      # 일부 질문만
    python run_bench.py --model openai/gpt-oss-20b
"""
import argparse
import asyncio
import json
import re
import statistics
import time
from dataclasses import asdict
from datetime import datetime

import common
from common import ROOT, DocIndex, Trace
from questions import load
from variants import current, kaizen_go, kaizen_mae

VARIANTS = {"current": current, "kaizen-mae": kaizen_mae, "kaizen-go": kaizen_go}
DEPTS = ["영업팀", "개발팀", "인사팀", "재무팀", "마케팅팀"]


def numbers_in(text: str) -> list[float]:
    nums = []
    for m in re.finditer(r"(\d[\d,]*(?:\.\d+)?)\s*(억|만)?", text):
        v = float(m.group(1).replace(",", ""))
        nums.append(v * {"억": 1e8, "만": 1e4}.get(m.group(2), 1))
    return nums


def grade(q: dict, ans: str) -> bool:
    ans = re.sub(r"(?s)<think>.*?</think>", "", ans)
    exp = q["expected"]
    if q["kind"] == "text":
        return all(k in ans or k.replace(",", "") in ans for k in exp)
    if isinstance(exp, str):  # 부서명 등: 답변에서 처음 언급된 후보가 정답이어야 함
        hits = sorted((ans.find(d), d) for d in DEPTS if d in ans)
        return bool(hits) and hits[0][1] == exp
    tol = max(1.0, abs(exp) * 0.005)  # 평균값 반올림 허용 (0.5%)
    return any(abs(n - exp) <= tol for n in numbers_in(ans))


async def run_one(name: str, q: dict, index: DocIndex) -> dict:
    trace = Trace()
    t = time.perf_counter()
    try:
        ans, err = await VARIANTS[name].answer(q["question"], index, trace), None
    except Exception as e:
        ans, err = "", f"{type(e).__name__}: {str(e)[:300]}"
    total = time.perf_counter() - t - trace.rate_limit_wait
    return {"variant": name, "id": q["id"], "kind": q["kind"], "question": q["question"],
            "expected": q["expected"], "answer": ans, "error": err,
            "correct": (not err) and grade(q, ans), "latency": round(total, 2), **asdict(trace)}


def p95(xs):
    return sorted(xs)[max(0, int(round(len(xs) * 0.95)) - 1)] if xs else 0


def summarize(rows: list[dict], variants: list[str], qs: list[dict]) -> str:
    out = [f"# SQL 하네스 벤치마크 결과\n\n- 모델: `{common.MODEL}`\n- 질문: 계산형 "
           f"{sum(q['kind'] == 'calc' for q in qs)}개 / 서술형 {sum(q['kind'] == 'text' for q in qs)}개\n",
           "| 방식 | 계산형 정답률 | 서술형 정답률 | 응답시간 p50 | p95 | 평균 입력 토큰 | 평균 LLM 호출 | 오류 |",
           "|---|---|---|---|---|---|---|---|"]
    for v in variants:
        rs = [r for r in rows if r["variant"] == v]
        calc = [r for r in rs if r["kind"] == "calc"]
        text = [r for r in rs if r["kind"] == "text"]
        lat = [r["latency"] for r in rs if not r["error"]]
        acc = lambda xs: f"{sum(r['correct'] for r in xs)}/{len(xs)}" if xs else "-"
        out.append(f"| {v} | {acc(calc)} | {acc(text)} | {statistics.median(lat) if lat else 0:.1f}s | "
                   f"{p95(lat):.1f}s | {statistics.mean(r['prompt_tokens'] for r in rs):,.0f} | "
                   f"{statistics.mean(r['llm_calls'] for r in rs):.1f} | {sum(bool(r['error']) for r in rs)} |")
    out += ["\n## 질문별 결과 (O 정답 / X 오답 / E 오류)\n",
            "| id | 질문 | 정답 | " + " | ".join(variants) + " |",
            "|---|---|---|" + "---|" * len(variants)]
    for q in qs:
        cells = []
        for v in variants:
            r = next((r for r in rows if r["variant"] == v and r["id"] == q["id"]), None)
            cells.append("-" if r is None else "E" if r["error"] else "O" if r["correct"] else "X")
        exp = q["expected"]
        exp = f"{exp:,.2f}".rstrip("0").rstrip(".") if isinstance(exp, float) else exp
        out.append(f"| {q['id']} | {q['question']} | {exp} | " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default=",".join(VARIANTS))
    ap.add_argument("--only", default="")
    ap.add_argument("--model", default=common.DEFAULT_MODEL)
    ap.add_argument("--pause", type=float, default=2.0, help="질문 사이 대기(초), 요청 한도 대응")
    args = ap.parse_args()
    common.MODEL = args.model

    variants = args.variants.split(",")
    qs = [q for q in load() if not args.only or q["id"] in args.only.split(",")]
    out_dir = ROOT / "results" / datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True)

    print("문서 인덱싱 중 (앱과 동일한 청킹/임베딩)...")
    index = DocIndex()
    # 준비 비용(표 추출·DB 적재)은 업로드 시점 비용이므로 질문별 응답시간에서 제외
    kaizen_go._ensure_db(Trace())
    kaizen_mae._context(Trace())

    rows = []
    with (out_dir / "raw.jsonl").open("w", encoding="utf-8") as f:
        for v in variants:
            for q in qs:
                r = await run_one(v, q, index)
                rows.append(r)
                f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
                f.flush()
                mark = "E" if r["error"] else "O" if r["correct"] else "X"
                await asyncio.sleep(args.pause)  # 요청 한도 여유
                print(f"[{v:10}] {q['id']} {mark} {r['latency']:6.1f}s  in={r['prompt_tokens']:>6} "
                      f"calls={r['llm_calls']}  {r['error'] or ''}")

    (out_dir / "summary.md").write_text(summarize(rows, variants, qs), encoding="utf-8")
    print(f"\n결과: {out_dir / 'summary.md'}")


if __name__ == "__main__":
    asyncio.run(main())
