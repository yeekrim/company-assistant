"""kaizen-mae (改善前): 개선 전 방식. 본문 + 표 전체(JSON)를 프롬프트에 넣고 LLM이 직접 계산."""
import json
import time

from common import PDF_PATH, Trace, chat
from tables import extract

SYSTEM = "당신은 사내 문서 기반 AI 어시스턴트입니다. 문서에 있는 내용만 답변하고, 한국어로만 답하세요."

_cache = None


def _context(trace: Trace) -> str:
    global _cache
    if _cache is None:
        t = time.perf_counter()
        text, tables = extract(str(PDF_PATH))
        parts = [f"[본문]\n{text}"]
        for tb in tables:
            records = [dict(zip(tb.columns, r)) for r in tb.rows]
            parts.append(f"[{tb.title}] (JSON)\n{json.dumps(records, ensure_ascii=False, default=str)}")
        _cache = "\n\n".join(parts)
        trace.add_time("prepare", time.perf_counter() - t)  # 첫 질문에만 기록됨
    return _cache


async def answer(question: str, index, trace: Trace) -> str:
    prompt = f"""아래 [문서]의 본문과 데이터(JSON)를 바탕으로 질문에 답하세요.
- 계산이 필요하면 데이터 전체를 빠짐없이 직접 계산하세요.
- 문서에 없는 내용은 추측하지 마세요.

[문서]
{_context(trace)}

[질문]
{question}

[답변]"""
    msg = await chat(trace, [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": prompt},
    ])
    return msg.content or ""
