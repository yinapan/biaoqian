import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE = __ENV.BASE_URL || 'http://localhost:8081';
const THRESHOLD = parseFloat(__ENV.THRESHOLD || '500');

export const options = {
  scenarios: {
    search_baseline: {
      executor: 'per-vu-iterations',
      vus: 1, iterations: 100,
      thresholds: {
        'http_req_duration{scenario:search_baseline}': [`p(95)<${THRESHOLD}`],
      },
    },
    suggestions_baseline: {
      executor: 'per-vu-iterations',
      vus: 1, iterations: 100,
      thresholds: {
        'http_req_duration{scenario:suggestions_baseline}': [`p(95)<${THRESHOLD}`],
      },
    },
    filter_definitions_baseline: {
      executor: 'per-vu-iterations',
      vus: 1, iterations: 100,
      thresholds: {
        'http_req_duration{scenario:filter_definitions_baseline}': [`p(95)<${THRESHOLD}`],
      },
    },
  },
};

export default function () {
  // 搜索空查询
  http.post(`${BASE}/api/v1/search/query`, JSON.stringify({
    module_type: 1, query: '', page: 1, page_size: 60,
  }), { headers: { 'Content-Type': 'application/json' } });

  // suggestions
  http.get(`${BASE}/api/v1/search/suggestions?q=测&module_type=1`);

  // filter definitions
  http.get(`${BASE}/api/v1/filter/definitions/1`);
}
