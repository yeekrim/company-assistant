"""current: 지금 앱의 파이프라인 그대로. Top-10 청크 → 프롬프트 → LLM 1회."""
from app.rag.generator import build_prompt

from common import DocIndex, Trace, chat

SYSTEM = "당신은 사내 문서 기반 AI 어시스턴트입니다. 문서에 있는 내용만 답변하고, 한국어로만 답하세요."


async def answer(question: str, index: DocIndex, trace: Trace) -> str:
    chunks = index.search(question, top_k=10, trace=trace)
    msg = await chat(trace, [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": build_prompt(question, chunks)},
    ])
    return msg.content or ""
