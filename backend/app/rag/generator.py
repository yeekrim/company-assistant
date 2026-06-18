def build_prompt(query: str, context_chunks: list[str]) -> str:
    if not context_chunks:
        context = "관련 문서를 찾지 못했습니다."
    else:
        context = "\n\n---\n\n".join(context_chunks)

    return f"""당신은 사내 문서를 기반으로 답변하는 AI 어시스턴트입니다.
아래 문서 내용을 참고하여 질문에 정확하고 친절하게 답변하세요.
문서에 없는 내용은 모른다고 솔직하게 말하세요.

[참고 문서]
{context}

[질문]
{query}

[답변]"""


async def generate(query: str, context_chunks: list[str]) -> str:
    """
    LLM 호출 지점. 현재는 컨텍스트를 그대로 반환하는 더미.
    Claude API 연동 시 이 함수만 교체하면 됩니다.
    """
    prompt = build_prompt(query, context_chunks)

    if not context_chunks:
        return "업로드된 사내 문서에서 관련 내용을 찾지 못했습니다. 관리자에게 문의하거나 관련 문서를 먼저 업로드해 주세요."

    return (
        f"📄 관련 문서 {len(context_chunks)}건을 참고했습니다.\n\n"
        + context_chunks[0][:300]
        + ("\n\n..." if len(context_chunks[0]) > 300 else "")
        + "\n\n*(LLM 연동 전 임시 응답 — Claude API 키 연결 후 정식 답변 제공)*"
    )
