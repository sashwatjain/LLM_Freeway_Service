from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openrouter_api_key: str = ""
    groq_api_key: str = ""
    google_api_key: str = ""
    gcp_project_id: str = ""
    cohere_api_key: str = ""
    cloudflare_account_id: str = ""
    cloudflare_api_key: str = ""
    hyperbolic_api_key: str = ""
    samba_api_key: str = ""
    scaleway_api_key: str = ""
    mistral_api_key: str = ""
    cerebras_api_key: str = ""
    kluster_api_key: str = ""
    nvidia_api_key: str = ""
    github_token: str = ""

    memory_char_limit: int = 1500


settings = Settings()
