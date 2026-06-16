CREATE TABLE assets (
    id              BIGSERIAL PRIMARY KEY,
    module_type     SMALLINT NOT NULL,
    name            VARCHAR(255) NOT NULL,
    resource_path   VARCHAR(500) NOT NULL,
    thumbnail_path  VARCHAR(500),
    tags            JSONB NOT NULL DEFAULT '{}',
    version         VARCHAR(20),
    file_size       BIGINT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX uk_assets_module_path ON assets (module_type, resource_path);
CREATE INDEX idx_assets_module ON assets (module_type);
CREATE INDEX idx_assets_tags ON assets USING GIN (tags jsonb_path_ops);
CREATE INDEX idx_assets_updated ON assets (updated_at DESC);

CREATE TABLE tag_definitions (
    id              SERIAL PRIMARY KEY,
    module_type     SMALLINT NOT NULL,
    field_name      VARCHAR(50) NOT NULL,
    display_name    VARCHAR(50) NOT NULL,
    field_type      VARCHAR(20) NOT NULL,
    is_fixed        BOOLEAN DEFAULT FALSE,
    is_filterable   BOOLEAN DEFAULT TRUE,
    is_searchable   BOOLEAN DEFAULT TRUE,
    sort_order      INTEGER DEFAULT 0,
    config          JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(module_type, field_name)
);

CREATE TABLE tag_values (
    id              SERIAL PRIMARY KEY,
    definition_id   INTEGER NOT NULL REFERENCES tag_definitions(id) ON DELETE CASCADE,
    value           VARCHAR(100) NOT NULL,
    display_name    VARCHAR(100),
    sort_order      INTEGER DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    UNIQUE(definition_id, value)
);

CREATE TABLE tag_synonyms (
    id              SERIAL PRIMARY KEY,
    module_type     SMALLINT NOT NULL,
    field_name      VARCHAR(50) NOT NULL,
    target_value    VARCHAR(100) NOT NULL,
    synonym         VARCHAR(100) NOT NULL,
    priority        INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(module_type, field_name, synonym)
);

CREATE INDEX idx_synonyms_module ON tag_synonyms (module_type);
CREATE INDEX idx_synonyms_lookup ON tag_synonyms (module_type, synonym);

CREATE TABLE search_logs (
    id              BIGSERIAL PRIMARY KEY,
    user_id         INTEGER,
    module_type     SMALLINT NOT NULL,
    raw_query       TEXT,
    parsed_filter   JSONB,
    parsed_keyword  TEXT,
    parse_source    VARCHAR(20),
    result_count    INTEGER,
    parse_time_ms   INTEGER,
    query_time_ms   INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_search_logs_time ON search_logs (created_at DESC);

CREATE TABLE user_favorites (
    user_id         INTEGER NOT NULL,
    asset_id        BIGINT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, asset_id)
);

CREATE TABLE import_errors (
    id              BIGSERIAL PRIMARY KEY,
    batch_id        VARCHAR(64) NOT NULL,
    module_type     SMALLINT,
    sheet_name      VARCHAR(100),
    row_number      INTEGER,
    field_name      VARCHAR(50),
    raw_value       TEXT,
    error_type      VARCHAR(50),
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_import_errors_batch ON import_errors (batch_id);

ALTER TABLE assets ADD CONSTRAINT chk_assets_module CHECK (module_type IN (1,2,3,4));
ALTER TABLE tag_definitions ADD CONSTRAINT chk_tagdef_module CHECK (module_type IN (1,2,3,4));
ALTER TABLE tag_synonyms ADD CONSTRAINT chk_synonym_module CHECK (module_type IN (1,2,3,4));
ALTER TABLE search_logs ADD CONSTRAINT chk_logs_module CHECK (module_type IN (1,2,3,4));
