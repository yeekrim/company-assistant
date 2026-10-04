"""세 방식이 공유하는 것: LLM 클라이언트, 호출 계측, 문서 인덱스."""
import asyncio
import os
import uuid
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).parent
BACKEND = ROOT.parent.parent / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)  # app.core.config가 backend/.env를 읽도록

import chromadb  # noqa: E402
from openai import RateLimitError  # noqa: E402

from app.rag.chunker import chunk_text, extract_text  # noqa: E402  (앱과 동일한 전처리)
from app.rag.embedder import embed  # noqa: E402
from app.rag.generator import get_client  # noqa: E402

PDF_PATH = ROOT / "data" / "사내규정_및_현황.pdf"
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"
MODEL = DEFAULT_MODEL  # run_bench.py가 --model로 덮어씀


@dataclass
class Trace:
    """질문 하나를 처리하며 쌓이는 계측값."""
    llm_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    steps: dict = field(default_factory=dict)  # 단계별 소요 시간(초)
    tool_log: list = field(default_factory=list)
    artifacts: list = field(default_factory=list)
    finish_reasons: list = field(default_factory=list)
    rate_limit_wait: float = 0.0

    def add_time(self, step: str, sec: float):
        self.steps[step] = round(self.steps.get(step, 0) + sec, 3)


async def chat(trace: Trace, messages: list[dict], **kw):
    """LLM 호출 + 토큰/시간 기록. 앱(generator.py)과 같은 샘플링 설정."""
    max_tokens = kw.pop("max_tokens", 2048)
    for attempt in range(6):
        t = time.perf_counter()
        try:
            r = await get_client().with_options(max_retries=0).chat.completions.create(
                model=MODEL, messages=messages,
                temperature=0.2, top_p=0.7, max_tokens=max_tokens,
                timeout=180,
                # nemotron은 기본이 추론(thinking) 모드. 앱이 쓰던 Llama 3.1 70B와 조건을 맞추려고 끔
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
                **kw,
            )
            break
        except RateLimitError:
            if attempt == 5:
                raise
            # 무료 티어 요청 한도(429). 대기 시간은 응답시간에서 빼도록 따로 기록
            wait = 10 * (attempt + 1)
            await asyncio.sleep(wait)
            trace.rate_limit_wait += time.perf_counter() - t
    trace.add_time("llm", time.perf_counter() - t)
    trace.llm_calls += 1
    if r.usage:
        trace.prompt_tokens += r.usage.prompt_tokens or 0
        trace.completion_tokens += r.usage.completion_tokens or 0
    trace.finish_reasons.append(r.choices[0].finish_reason)
    return r.choices[0].message


class DocIndex:
    """인메모리 Chroma 인덱스. 도커 Chroma 서버나 실제 회사 컬렉션을 건드리지 않는다.
    chunks를 안 주면 앱의 업로드 경로(extract_text → chunk_text)를 그대로 따른다."""

    def __init__(self, chunks: list[str] | None = None):
        self.chunks = chunks if chunks is not None else chunk_text(extract_text(str(PDF_PATH)))
        client = chromadb.EphemeralClient()
        self.col = client.create_collection(f"bench_{uuid.uuid4().hex[:8]}", metadata={"hnsw:space": "cosine"})
        self.col.upsert(
            ids=[f"c{i}" for i in range(len(self.chunks))],
            embeddings=embed(self.chunks),
            documents=self.chunks,
        )

    def search(self, query: str, top_k: int, trace: Trace) -> list[str]:
        t = time.perf_counter()
        q = embed([query])[0]
        trace.add_time("embed", time.perf_counter() - t)
        t = time.perf_counter()
        r = self.col.query(query_embeddings=[q], n_results=top_k, include=["documents"])
        trace.add_time("search", time.perf_counter() - t)
        return r["documents"][0] if r["documents"] else []
