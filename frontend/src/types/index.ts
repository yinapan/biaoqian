/** Numeric filter condition */
export interface Condition {
  field: string
  op: '>' | '<' | '>=' | '<=' | '=='
  value: number
}

/** Sort option */
export interface SortOption {
  field: string
  order: 'asc' | 'desc'
}

/** POST body for /api/v1/search/query */
export interface SearchRequest {
  module_type: number
  query?: string
  filters?: Record<string, any>
  conditions?: Condition[]
  sort?: SortOption
  page?: number
  page_size?: number
}

/** Tag that was ignored during NL parsing */
export interface IgnoredTag {
  field: string
  value: string
  reason: string
}

/** Metadata about how the query was parsed */
export interface ParseInfo {
  parsed_filters: Record<string, any>
  effective_filters: Record<string, any>
  ignored_tags: IgnoredTag[]
  keyword: string
  confidence: number
  fallback: boolean
  parse_source: string
  parse_time_ms: number
}

/** A single search-result item */
export interface AssetItem {
  id: number
  name: string
  resource_path: string
  thumbnail_path: string | null
  tags: Record<string, any>
  relevance_score: number
  highlight: Record<string, string[]>
}

/** Aggregation bucket */
export interface FacetValue {
  value: string
  count: number
}

/** Response from /api/v1/search/query */
export interface SearchResponse {
  total: number
  page: number
  page_size: number
  parse_info: ParseInfo | null
  items: AssetItem[]
  facets: Record<string, FacetValue[]>
  query_time_ms: number
}

/** Auto-complete suggestion */
export interface SuggestionItem {
  text: string
  field: string
  type: string
}

/** A single allowed value for an enum-type tag */
export interface TagValue {
  value: string
  display_name: string
}

/** Describes one filterable tag dimension */
export interface TagDefinition {
  id: number
  field_name: string
  display_name: string
  field_type: string
  is_filterable: boolean
  is_searchable: boolean
  sort_order: number
  config: Record<string, any>
  values: TagValue[]
}
