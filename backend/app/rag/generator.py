import httpx

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:4b"


def build_prompt(query: str, context_chunks: list[str]) -> str:
    context = "\n\n---\n\n".join(context_chunks)
    return f"""당신은 사내 문서 기반 AI 어시스턴트입니다.
아래 [문서 내용]을 바탕으로 질문에 친절하고 간결하게 답변하세요.

- 문서에 있는 내용만 답변하고, 없는 내용은 추측하지 마세요.
- 자연스러운 문장으로 설명하세요.
- 고유명사와 URL은 원문 그대로 사용하고, 한국어 외 다른 언어가 섞이지 않도록 하세요.
- 관련 내용이 없으면 "업로드된 문서에서 관련 내용을 찾지 못했습니다"라고만 답하세요.

[문서 내용]
{context}

[질문]
{query}

[답변]"""


async def generate(query: str, context_chunks: list[str]) -> str:
    if not context_chunks:
        return "업로드된 사내 문서에서 관련 내용을 찾지 못했습니다. 관련 문서를 먼저 업로드해 주세요."

    prompt = build_prompt(query, context_chunks)

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        )
        response.raise_for_status()
        return response.json()["response"]
