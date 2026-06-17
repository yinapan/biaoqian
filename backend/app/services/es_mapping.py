FIELD_TYPE_TO_ES = {
    "enum_single": {"type": "keyword"},
    "enum_multi": {"type": "keyword"},
    "number_range": {"type": "float"},
    "boolean": {"type": "boolean"},
    "text": {"type": "keyword"},
}


def generate_tag_properties(definitions: list[dict]) -> dict[str, dict]:
    props = {}
    for d in definitions:
        es_type = FIELD_TYPE_TO_ES.get(d["field_type"], {"type": "keyword"})
        props[f"tags.{d['field_name']}"] = es_type
    return props


def build_index_settings_and_mappings(tag_definitions: list[dict]) -> dict:
    tag_props = generate_tag_properties(tag_definitions)
    return {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "ik_smart_analyzer": {"type": "custom", "tokenizer": "ik_smart"},
                    "ik_max_analyzer": {"type": "custom", "tokenizer": "ik_max_word"},
                }
            },
        },
        "mappings": {
            "properties": {
                "id": {"type": "long"},
                "module_type": {"type": "keyword"},
                "name": {
                    "type": "text",
                    "analyzer": "ik_max_analyzer",
                    "search_analyzer": "ik_smart_analyzer",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "resource_path": {"type": "keyword", "index": False},
                "thumbnail_path": {"type": "keyword"},
                "tags": {"type": "object", "dynamic": True},
                "version": {"type": "keyword"},
                "file_size": {"type": "long"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
                "search_text": {
                    "type": "text",
                    "analyzer": "ik_max_analyzer",
                    "search_analyzer": "ik_smart_analyzer",
                },
                **tag_props,
            },
            "dynamic_templates": [
                {
                    "tags_strings": {
                        "path_match": "tags.*",
                        "match_mapping_type": "string",
                        "mapping": {"type": "keyword"},
                    }
                },
                {
                    "tags_numbers": {
                        "path_match": "tags.*",
                        "match_mapping_type": "long",
                        "mapping": {"type": "float"},
                    }
                },
                {
                    "tags_booleans": {
                        "path_match": "tags.*",
                        "match_mapping_type": "boolean",
                        "mapping": {"type": "boolean"},
                    }
                },
            ],
        },
    }
