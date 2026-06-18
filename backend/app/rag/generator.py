import httpx

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"


def build_prompt(query: str, context_chunks: list[str]) -> str:
    context = "\n\n---\n\n".join(context_chunks)
    return f"""당신은 사내 문서를 기반으로 답변하는 AI 어시스턴트입니다.
아래 문서 내용을 참고하여 질문에 정확하고 친절하게 한국어로 답변하세요.
문서에 없는 내용은 모른다고 솔직하게 말하세요.

[참고 문서]
{context}

[질문]
{query}

[답변]"""


async def generate(query: str, context_chunks: list[str]) -> str:
    if not context_chunks:
        return "업로드된 사내 문서에서 관련 내용을 찾지 못했습니다. 관련 문서를 먼저 업로드해 주세요."

    prompt = build_prompt(query, context_chunks)

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        )
        response.raise_for_status()
        return response.json()["response"]
