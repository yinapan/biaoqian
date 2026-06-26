import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE = __ENV.BASE_URL || 'http://localhost:8081';

export const options = {
  scenarios: {
    concurrent_50: {
      executor: 'constant-vus',
      vus: 50, duration: '1m',
      thresholds: {
        'http_req_failed{scenario:concurrent_50}': ['rate<0.01'],
      },
    },
    concurrent_200: {
      executor: 'constant-vus',
      vus: 200, duration: '1m',
      thresholds: {
        'http_req_failed{scenario:concurrent_200}': ['rate<0.05'],
      },
    },
    concurrent_50_with_suggestions: {
      executor: 'constant-vus',
      vus: 50, duration: '1m',
      exec: 'search_with_suggestions',
    },
  },
};

export default function () {
  const res = http.post(`${BASE}/api/v1/search/query`, JSON.stringify({
    module_type: 1, query: '', page: 1, page_size: 60,
  }), { headers: { 'Content-Type': 'application/json' } });
  check(res, { 'status 200': r => r.status === 200 });
}

export function search_with_suggestions() {
  http.post(`${BASE}/api/v1/search/query`, JSON.stringify({
    module_type: 1, query: '测', page: 1, page_size: 60,
  }), { headers: { 'Content-Type': 'application/json' } });
  http.get(`${BASE}/api/v1/search/suggestions?q=测&module_type=1`);
}
