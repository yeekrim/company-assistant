"""청킹 방식별 c4 검색 적중률: 질문 시점 필터를 건 Top-K 안에 정답 키워드를 모두 담은 청크가 있는지 본다.

labels.csv의 nDCG 라벨은 청크 원문 해시로 붙어 있어 청킹을 바꾸면 쓸 수 없다.
그래서 answer_eval.py와 같은 ANSWER_KEYS로, 라벨 없이 청킹끼리 비교한다.
- 적중: Top-K 중 한 청크에 키워드 그룹이 모두 들어 있음 (라벨 3에 해당)
- 한계: 키워드가 같은 다른 버전 청크도 적중으로 센다. 버전 구분은 answer_eval.py로 본다.

    ../../backend/venv/bin/python chunk_recall.py
"""
import uuid
from functools import partial

import chromadb
from configs import TOP_K
from companies import dated_docs
from questions import ANSWER_KEYS, QUESTIONS

from app.rag import retriever
from app.rag.chunker import chunk_chars, chunk_text, extract_text
from app.rag.dates import query_as_of

COMPANY = "c4"

CHUNKERS = {
    "chars_500 (이전)": lambda text: chunk_chars(text.strip(), 500, 50),
    "articles_500": partial(chunk_text, chunk_size=500),
    "articles_250": partial(chunk_text, chunk_size=250),
}


def build(chunker) -> chromadb.Collection:
    col = chromadb.EphemeralClient().create_collection(f"recall_{uuid.uuid4().hex[:8]}",
                                                       metadata={"hnsw:space": "cosine"})
    original = retriever.get_collection
    retriever.get_collection = lambda _company_id: col
    try:
        for path, effective_date in dated_docs(COMPANY):
            retriever.add_documents(0, chunker(extract_text(str(path))), path.name, effective_date)
    finally:
        retriever.get_collection = original
    return col


def hit(texts: list[str], keys: list[list[str]]) -> bool:
    return any(all(any(k in t for k in group) for group in keys) for t in texts)


def main():
    print("| 청킹 | 청크 수 | 적중 (전체) | 시점 없는 질문 | 과거 시점 질문 |\n|---|---|---|---|---|")
    for name, chunker in CHUNKERS.items():
        col = build(chunker)
        original = retriever.get_collection
        retriever.get_collection = lambda _company_id: col
        try:
            rows = []
            for qid, question, _hint in QUESTIONS[COMPANY]:
                found = retriever.search_chunks(0, question, TOP_K, as_of=query_as_of(question))
                rows.append((qid, hit([c.text for c in found], ANSWER_KEYS[qid])))
        finally:
            retriever.get_collection = original
        now = sum(h for q, h in rows if int(q[-2:]) <= 6)
        past = sum(h for q, h in rows if int(q[-2:]) > 6)
        missed = ",".join(q[-3:] for q, h in rows if not h)
        print(f"| {name} | {col.count()} | {now + past}/{len(rows)} | {now}/6 | {past}/6 |  놓침: {missed}")


if __name__ == "__main__":
    main()
