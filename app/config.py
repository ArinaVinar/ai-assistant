from pydantic_settings import BaseSettings

#default если в env не найдёт
class Settings(BaseSettings):
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "navigator_db"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    postgres_top_k: int = 5
    neo4j_top_k: int = 5

    max_retries: int = 2
    min_confidence: float = 0.65

    class Config:
        env_file = ".env"


settings = Settings()