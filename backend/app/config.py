from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://biaoqiao:biaoqiao_dev@localhost:5432/biaoqiao"
    es_url: str = "http://localhost:9200"
    es_index_alias: str = "assets"
    db_schema: str = ""  # 空 = 用默认 search_path；非空 = SET search_path TO {schema}, public
    admin_api_key: str = "dev-admin-key-change-in-prod"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = "qwen-turbo"
    llm_timeout: float = 3.0
    llm_enabled: bool = True
    parse_cache_maxsize: int = 5000
    parse_cache_ttl: int = 86400
    tag_cache_ttl: int = 3600
    dict_refresh_interval: int = 600
    page_size_max: int = 100
    page_offset_max: int = 10000

    class Config:
        env_file = ".env"


settings = Settings()
