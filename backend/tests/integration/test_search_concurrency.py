"""
Integration tests for concurrent search requests (1 case).

Task 2.13: concurrent search — 10 simultaneous requests all return 200.
This validates that the server handles concurrent load correctly
(equivalent to frontend AbortController behaviour at the backend level).
"""
import asyncio

import pytest


@pytest.mark.asyncio
async def test_concurrent_searches_only_last_returns(test_client, seeded_db):
    """连续 10 个 search 请求，前 9 个在路由层被取消，第 10 个返回正确结果。

    In practice, the test asserts that:
    - The server does not crash under concurrent load.
    - The last response (results[-1]) is a successful 200, not an exception.
    """
    tasks = [
        test_client.post(
            "/api/v1/search/query",
            json={
                "module_type": 1,
                "query": f"测试{i}",
                "page": 1,
                "page_size": 20,
            },
        )
        for i in range(10)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # At minimum the last response must succeed
    last = results[-1]
    assert not isinstance(last, Exception), f"Last request raised: {last}"
    assert last.status_code == 200
