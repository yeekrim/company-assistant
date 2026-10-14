"""라벨링된 labels.csv로 설정별 검색 품질을 계산한다.

- gain: 3(딱 맞음) / 1(부분 관련) / 0(무관). 복수 라벨 "1|3"은 낮은 쪽(low)과 높은 쪽(high)으로 두 번 계산
- nDCG@K: IDCG는 그 질문의 라벨된 청크 전체(모든 설정의 합집합)로 계산한다.
  설정마다 따로 계산하면 서로 비교할 수 없다.
- P@K strict: 3점만 관련 / lenient: 1점 이상 관련
- 관련 청크(1점 이상)가 하나도 없는 질문은 nDCG를 정의할 수 없어 제외한다.
- 설정의 Top-K에 라벨 없는 청크가 있으면 0점으로 계산하고 개수를 따로 알린다 → pool.py를 다시 돌려 라벨링

    ../../backend/venv/bin/python evaluate.py
"""
import argparse
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from companies import COMPANIES
from configs import CONFIGS, TOP_K, build
from pool import LABELS, chunk_id, read_rows
from questions import QUESTIONS

from common import Trace

RESULTS = Path(__file__).resolve().parent / "results"
VALID = {"0", "1", "3"}


def parse_label(s: str) -> tuple[int, int] | None:
    """'3' → (3, 3), '1|3' → (1, 3), 빈 칸 → None"""
    parts = [p.strip() for p in s.split("|") if p.strip()]
    if not parts:
        return None
    bad = [p for p in parts if p not in VALID]
    if bad:
        raise ValueError(f"라벨은 0·1·3 또는 '1|3' 형식이어야 합니다: {s!r}")
    g = sorted(int(p) for p in parts)
    return g[0], g[-1]


def dcg(gains: list[int]) -> float:
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", default=",".join(CONFIGS))
    ap.add_argument("--companies", default=",".join(COMPANIES))
    args = ap.parse_args()
    names = args.configs.split(",")
    companies = args.companies.split(",")
    qlist = [(c, qid, q) for c in companies for qid, q, _ in QUESTIONS[c]]

    labels: dict[str, dict[str, tuple[int, int]]] = defaultdict(dict)  # qid → chunk_id → (low, high)
    for r in read_rows():
        try:
            g = parse_label(r["label"])
        except ValueError as e:
            raise SystemExit(f"{LABELS} {r['qid']} {r['chunk_id']}: {e}")
        if g is not None:
            labels[r["qid"]][r["chunk_id"]] = g
    if not labels:
        raise SystemExit(f"라벨이 없습니다. {LABELS}의 label 칸을 채운 뒤 다시 실행하세요.")

    # 질문별 각 설정의 Top-K gain 목록
    per_q: dict[str, dict[str, list]] = defaultdict(dict)
    unlabeled: dict[str, int] = defaultdict(int)
    for name in names:
        for company in companies:
            index = build(name, company)
            for c, qid, question in qlist:
                if c != company:
                    continue
                gains = []
                for text in index.search(question, TOP_K, Trace()):
                    g = labels[qid].get(chunk_id(text))
                    if g is None:
                        unlabeled[name] += 1
                        g = (0, 0)
                    gains.append(g)
                per_q[qid][name] = gains

    # score[name][metric][qid]
    score = {name: defaultdict(dict) for name in names}
    skipped = []
    for _, qid, _ in qlist:
        pool = list(labels[qid].values())
        if not any(h > 0 for _, h in pool):
            skipped.append(qid)
            continue
        for side, i in (("low", 0), ("high", 1)):
            idcg = dcg(sorted((g[i] for g in pool), reverse=True)[:TOP_K])
            for name in names:
                score[name][f"ndcg_{side}"][qid] = dcg([g[i] for g in per_q[qid][name]]) / idcg
        for name in names:
            low = [g[0] for g in per_q[qid][name]]
            score[name]["p_strict"][qid] = sum(g == 3 for g in low) / TOP_K
            score[name]["p_lenient"][qid] = sum(g >= 1 for g in low) / TOP_K
    kept = [(c, qid) for c, qid, _ in qlist if qid not in skipped]

    lines = [f"# 검색 평가 결과 ({datetime.now():%Y-%m-%d %H:%M})", "",
             f"- 회사 {len(companies)}곳, 질문 {len(qlist)}개, Top-{TOP_K}, 라벨된 쌍 {sum(len(v) for v in labels.values())}개"]
    if skipped:
        lines.append(f"- 관련 청크가 없어 제외한 질문: {', '.join(skipped)}")
    for name in names:
        if unlabeled[name]:
            lines.append(f"- ⚠ {name}: Top-{TOP_K} 안에 라벨 없는 청크 {unlabeled[name]}개 (0점 처리). pool.py 재실행 후 라벨링 필요")

    metrics = ["ndcg_low", "ndcg_high", "p_strict", "p_lenient"]
    header = (f"| 범위 | 설정 | nDCG@{TOP_K} (low) | nDCG@{TOP_K} (high) | P@{TOP_K} strict | P@{TOP_K} lenient |",
              "|---|---|---|---|---|---|")
    lines += ["", *header]
    for scope in ["전체", *companies]:
        qids = [qid for c, qid in kept if scope == "전체" or c == scope]
        label = scope if scope == "전체" else f"{scope} {COMPANIES[scope]['name']}"
        for name in names:
            vals = [mean([score[name][m][q] for q in qids]) for m in metrics]
            lines.append(f"| {label} ({len(qids)}문항) | {name} | " + " | ".join(f"{v:.3f}" for v in vals) + " |")

    # 질문별 비교 (첫 설정 대비 좋아진/나빠진/같은 질문 수). 평균 차이가 우연인지 가늠하는 용도
    base = names[0]
    for name in names[1:]:
        diff = [score[name]["ndcg_low"][q] - score[base]["ndcg_low"][q] for _, q in kept]
        win, lose = sum(d > 1e-9 for d in diff), sum(d < -1e-9 for d in diff)
        lines.append(f"\n- {name} vs {base} (nDCG low, 질문별): 좋아짐 {win} / 나빠짐 {lose} / 같음 {len(diff) - win - lose}")

    lines += ["", "## 질문별 nDCG (low)", "", "| 질문 | " + " | ".join(names) + " |",
              "|---|" + "---|" * len(names)]
    for _, qid in kept:
        lines.append(f"| {qid} | " + " | ".join(f"{score[n]['ndcg_low'][qid]:.3f}" for n in names) + " |")

    report = "\n".join(lines) + "\n"
    print(report)
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"{datetime.now():%Y%m%d-%H%M%S}.md"
    out.write_text(report, encoding="utf-8")
    print(f"저장: {out}")


if __name__ == "__main__":
    main()
