import time

from elasticsearch import AsyncElasticsearch

from app.config import settings

_es: AsyncElasticsearch | None = None


async def get_es() -> AsyncElasticsearch:
    global _es
    if _es is None:
        _es = AsyncElasticsearch(settings.es_url)
    return _es


async def close_es():
    global _es
    if _es:
        await _es.close()
        _es = None


def flatten_tag_values(tags: dict) -> list[str]:
    values = []
    for v in tags.values():
        if isinstance(v, list):
            values.extend(str(x) for x in v)
        elif isinstance(v, bool):
            continue
        elif v is not None:
            values.append(str(v))
    return values


def build_es_doc(row: dict) -> dict:
    return {
        "id": row["id"],
        "module_type": str(row["module_type"]),
        "name": row["name"],
        "resource_path": row["resource_path"],
        "thumbnail_path": row.get("thumbnail_path"),
        "tags": row["tags"],
        "version": row.get("version"),
        "file_size": row.get("file_size"),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
        "search_text": f"{row['name']} {' '.join(flatten_tag_values(row['tags']))}",
    }


async def bulk_index(docs: list[dict]) -> dict:
    es = await get_es()
    actions = []
    for doc in docs:
        actions.append({"index": {"_index": settings.es_index_alias, "_id": doc["id"]}})
        actions.append(doc)
    if not actions:
        return {"errors": False, "items": []}
    return await es.bulk(body=actions, refresh="wait_for")


async def reindex_with_alias(pool, index_body: dict) -> dict:
    es = await get_es()
    new_index = f"assets_v{int(time.time())}"
    await es.indices.create(index=new_index, body=index_body)

    batch_size = 500
    offset = 0
    total = 0
    async with pool.acquire() as conn:
        while True:
            rows = await conn.fetch(
                "SELECT * FROM assets ORDER BY id LIMIT $1 OFFSET $2",
                batch_size,
                offset,
            )
            if not rows:
                break
            docs = [build_es_doc(dict(r)) for r in rows]
            actions = []
            for doc in docs:
                actions.append({"index": {"_index": new_index, "_id": doc["id"]}})
                actions.append(doc)
            await es.bulk(body=actions)
            total += len(rows)
            offset += batch_size

    await es.indices.update_aliases(
        body={
            "actions": [
                {"remove": {"index": "*", "alias": settings.es_index_alias}},
                {"add": {"index": new_index, "alias": settings.es_index_alias}},
            ]
        }
    )
    return {"new_index": new_index, "total_indexed": total}


async def check_sync(pool) -> dict:
    es = await get_es()
    async with pool.acquire() as conn:
        pg_count = await conn.fetchval("SELECT COUNT(*) FROM assets")
    es_resp = await es.count(index=settings.es_index_alias)
    es_count = es_resp["count"]
    return {
        "pg_count": pg_count,
        "es_count": es_count,
        "diff": pg_count - es_count,
        "in_sync": pg_count == es_count,
    }
