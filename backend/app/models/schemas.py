from pydantic import BaseModel, Field, model_validator
from typing import Any

from app.config import settings


class Condition(BaseModel):
    field: str
    op: str  # ">", "<", ">=", "<=", "=="
    value: float


class SortOption(BaseModel):
    field: str = "relevance"
    order: str = "desc"


class SearchRequest(BaseModel):
    module_type: int = Field(ge=1, le=4)
    query: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    exclude_filters: dict[str, Any] = Field(default_factory=dict)
    dismissed_fields: list[str] = Field(default_factory=list)
    conditions: list[Condition] = Field(default_factory=list)
    sort: SortOption = Field(default_factory=SortOption)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=settings.page_size_max)

    @model_validator(mode="after")
    def check_offset(self):
        if self.page * self.page_size > settings.page_offset_max:
            raise ValueError(
                f"page * page_size must be <= {settings.page_offset_max}"
            )
        return self


class IgnoredTag(BaseModel):
    field: str
    value: str
    reason: str


class ParseInfo(BaseModel):
    parsed_filters: dict[str, Any] = Field(default_factory=dict)
    parsed_excludes: dict[str, Any] = Field(default_factory=dict)
    effective_filters: dict[str, Any] = Field(default_factory=dict)
    effective_excludes: dict[str, Any] = Field(default_factory=dict)
    ignored_tags: list[IgnoredTag] = Field(default_factory=list)
    keyword: str = ""
    confidence: float = 0.0
    fallback: bool = False
    parse_source: str = ""
    parse_time_ms: int = 0


class AssetItem(BaseModel):
    id: int
    name: str
    resource_path: str
    thumbnail_path: str | None = None
    tags: dict[str, Any] = Field(default_factory=dict)
    relevance_score: float = 0.0
    highlight: dict[str, list[str]] = Field(default_factory=dict)


class FacetValue(BaseModel):
    value: str
    count: int


class SearchResponse(BaseModel):
    total: int
    page: int
    page_size: int
    parse_info: ParseInfo | None = None
    items: list[AssetItem]
    facets: dict[str, list[FacetValue]] = Field(default_factory=dict)
    query_time_ms: int = 0
    facet_time_ms: int = 0


class SuggestionItem(BaseModel):
    text: str
    field: str
    type: str = "tag"


class SuggestionsResponse(BaseModel):
    suggestions: list[SuggestionItem]


class ImportResult(BaseModel):
    batch_id: str
    success: int = 0
    skipped: int = 0
    failed: int = 0
    es_sync_failed: int = 0
    unknown_tags: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)


class TagDefinitionOut(BaseModel):
    id: int
    field_name: str
    display_name: str
    field_type: str
    is_filterable: bool
    is_searchable: bool
    sort_order: int
    config: dict[str, Any]
    values: list[dict[str, Any]] = Field(default_factory=list)
