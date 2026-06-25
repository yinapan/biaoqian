import axios from 'axios'
import type {
  SearchRequest,
  SearchResponse,
  TagDefinition,
  SuggestionItem,
} from '@/types'

const api = axios.create({ baseURL: '/api/v1' })

/** Execute a search query */
export async function searchAssets(
  req: SearchRequest,
  signal?: AbortSignal,
): Promise<SearchResponse> {
  const { data } = await api.post<SearchResponse>('/search/query', req, { signal })
  return data
}

/** Fetch tag definitions for a module type */
export async function getTagDefinitions(
  moduleType: number,
): Promise<TagDefinition[]> {
  const { data } = await api.get<TagDefinition[]>(
    `/filter/definitions/${moduleType}`,
  )
  return data
}

/** Fetch auto-complete suggestions */
export async function getSuggestions(
  moduleType: number,
  q: string,
): Promise<SuggestionItem[]> {
  const { data } = await api.get<{ suggestions: SuggestionItem[] }>(
    '/search/suggestions',
    { params: { module_type: moduleType, q } },
  )
  return data.suggestions
}
