from openai import AsyncOpenAI
from app.core.config import settings

NVIDIA_MODEL = "meta/llama-3.1-70b-instruct"

_client = None

def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=settings.NVIDIA_API_KEY,
        )
    return _client


def build_prompt(query: str, context_chunks: list[str]) -> str:
    context = "\n\n---\n\n".join(context_chunks)
    return f"""당신은 사내 문서 기반 AI 어시스턴트입니다.
아래 [문서 내용]을 바탕으로 질문에 친절하고 간결하게 답변하세요.

- 문서에 있는 내용만 답변하고, 없는 내용은 추측하지 마세요.
- 핵심을 전달하되, 자연스러운 문장으로 설명하세요.
- 관련된 세부 내용이 존재하면 그것도 덧붙여 설명하세요.
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
    client = get_client()

    completion = await client.chat.completions.create(
        model=NVIDIA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        top_p=0.7,
        max_tokens=1024,
        stream=False,
    )

    return completion.choices[0].message.content or ""
