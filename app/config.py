from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


JIRA_OAUTH_SCOPES = "read:jira-work read:jira-user manage:jira-webhook read:project:jira read:board-scope:jira-software read:sprint:jira-software read:webhook:jira read:jql:jira read:field:jira write:webhook:jira offline_access"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://pka:pka@localhost:5433/pka"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "project_documents"
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_llm_model: str = "gpt-4o-mini"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    upload_dir: str = "./uploads"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    chunk_size: int = 512
    chunk_overlap: int = 50
    retrieval_top_k: int = 4

    jira_oauth_client_id: str = ""
    jira_oauth_client_secret: str = ""
    jira_oauth_redirect_uri: str = "http://localhost:8000/integrations/jira/oauth/callback"
    jira_oauth_frontend_redirect: str = "http://localhost:5173/settings/jira?status="
    jira_token_encryption_key: str = ""
    jira_story_points_field: str = ""
    jira_acceptance_criteria_field: str = ""
    jira_webhook_base_url: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def jira_oauth_configured(self) -> bool:
        return bool(
            self.jira_oauth_client_id
            and self.jira_oauth_client_secret
            and self.jira_oauth_redirect_uri
            and self.jira_token_encryption_key
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
