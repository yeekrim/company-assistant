"""라벨링할 질문-청크 쌍 만들기 (pooling).

회사마다, 설정마다 질문별 Top-K를 뽑고, 그 합집합을 labels/labels.csv에 쓴다.
같은 텍스트의 청크는 설정이 달라도 한 행으로 합친다 (chunk_id = 텍스트 해시).

이미 labels.csv가 있으면 채워 둔 label·note를 그대로 유지하고, 새로 나온 쌍만 빈 칸으로 추가한다.
설정을 추가한 뒤 다시 실행하면 그 설정에서만 나온 청크만 새로 라벨링하면 된다.

    ../../backend/venv/bin/python pool.py
    ../../backend/venv/bin/python pool.py --configs A_current,B_table_split
"""
import argparse
import csv
import hashlib
from pathlib import Path

from companies import COMPANIES
from configs import CONFIGS, TOP_K, build
from questions import QUESTIONS

from common import Trace

LABELS = Path(__file__).resolve().parent / "labels" / "labels.csv"
BASE_FIELDS = ["company", "qid", "question", "hint", "chunk_id", "label", "note"]


def chunk_id(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:10]


def read_rows() -> list[dict]:
    if not LABELS.exists():
        return []
    with LABELS.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", default=",".join(CONFIGS), help="쉼표로 구분한 설정 이름")
    ap.add_argument("--companies", default=",".join(COMPANIES), help="쉼표로 구분한 회사 키")
    args = ap.parse_args()
    names = args.configs.split(",")
    companies = args.companies.split(",")

    rows = {(r["qid"], r["chunk_id"]): r for r in read_rows()}
    rank_cols = list(dict.fromkeys(c for r in rows.values() for c in r if c.startswith("rank:")))

    for name in names:
        col = f"rank:{name}"
        for r in rows.values():  # 이 설정의 순위는 새로 매긴다 (대상 회사만)
            if r["company"] in companies:
                r[col] = ""
        for company in companies:
            index = build(name, company)
            print(f"{company} {name}: 청크 {len(index.chunks)}개")
            for qid, question, hint in QUESTIONS[company]:
                for rank, text in enumerate(index.search(question, TOP_K, Trace()), 1):
                    key = (qid, chunk_id(text))
                    r = rows.setdefault(key, {"company": company, "qid": qid, "question": question,
                                              "hint": hint, "chunk_id": key[1], "label": "", "note": "",
                                              "text": text.replace("\n", " ⏎ ")})
                    r[col] = str(rank)
        if col not in rank_cols:
            rank_cols.append(col)

    all_q = [q for c in COMPANIES for q in QUESTIONS.get(c, [])]
    order = {qid: i for i, (qid, _, _) in enumerate(all_q)}

    def best_rank(r):
        ranks = [int(r[c]) for c in rank_cols if r.get(c)]
        return min(ranks) if ranks else TOP_K + 1

    out = sorted(rows.values(), key=lambda r: (order.get(r["qid"], len(order)), best_rank(r)))
    LABELS.parent.mkdir(exist_ok=True)
    with LABELS.open("w", encoding="utf-8-sig", newline="") as f:  # Excel·Numbers에서 한글이 깨지지 않도록 BOM
        w = csv.DictWriter(f, fieldnames=BASE_FIELDS + rank_cols + ["text"])
        w.writeheader()
        w.writerows({k: r.get(k, "") for k in w.fieldnames} for r in out)

    todo = sum(1 for r in out if not r["label"].strip())
    print(f"{LABELS} — 쌍 {len(out)}개 (라벨 안 된 것 {todo}개), 질문 {len(all_q)}개")


if __name__ == "__main__":
    main()
