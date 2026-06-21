from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    GEMINI_API_KEY: str = ""
    NVIDIA_API_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
