from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    default_model: str = "meta-llama/llama-3.1-8b-instruct"
    ions_node_id: str = "genesis_node"
    auth_secret: str = "change-me-in-production"
    env: str = "local"

    # Federation settings
    node_id: str = "genesis_node"
    public_api_base: str = "http://localhost:8000"
    node_description: str = "IONS Genesis reference node"

    class Config:
        env_file = ".env"

settings = Settings()