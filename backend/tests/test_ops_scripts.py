from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENV_DIRS = [
    "deploy/local",
    "deploy/prod",
]
SCRIPT_NAMES = [
    "build.bat",
    "start.bat",
    "stop.bat",
    "deploy.bat",
    "import-new-data.bat",
    "reimport-data.bat",
    "reset-and-reimport-data.bat",
    "verify-previews.bat",
    "delete-stale-data.bat",
    "restore-from-canonical.bat",
    "backup.bat",
]
ROOT_WRAPPERS = [
    "build.bat",
    "start.bat",
    "stop.bat",
    "deploy.bat",
    "import.bat",
    "import-new-data.bat",
    "reimport-data.bat",
    "reset-and-reimport-data.bat",
    "verify-previews.bat",
    "delete-stale-data.bat",
    "restore-from-canonical.bat",
    "backup.bat",
]


def _read_script(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_ops_scripts_pin_compose_project_name():
    local_env = _read_script("deploy/local/env.bat")
    prod_env = _read_script("deploy/prod/env.bat")
    assert "PROJECT_NAME=biaoqian_local" in local_env
    assert "PROJECT_NAME=biaoqian" in prod_env


def test_ops_scripts_do_not_delete_docker_volumes():
    forbidden = [
        "down -v",
        "volume prune",
        "system prune --volumes",
    ]
    script_paths = ROOT_WRAPPERS + [
        f"{env_dir}/{script_name}"
        for env_dir in ENV_DIRS
        for script_name in ["env.bat", *SCRIPT_NAMES]
    ]
    for script in script_paths:
        text = _read_script(script).lower()
        for token in forbidden:
            assert token not in text, f"{script} must not contain {token}"


def test_ops_bat_scripts_are_ascii_only():
    script_paths = ROOT_WRAPPERS + [
        f"{env_dir}/{script_name}"
        for env_dir in ENV_DIRS
        for script_name in ["env.bat", *SCRIPT_NAMES]
    ]
    for script in script_paths:
        text = _read_script(script)
        assert text.isascii(), f"{script} must stay ASCII-only for cmd.exe safety"


def test_import_scripts_use_non_destructive_upsert_flow():
    for env_dir in ENV_DIRS:
        for script in ["import-new-data.bat", "reimport-data.bat"]:
            text = _read_script(f"{env_dir}/{script}")
            assert "scripts/import_data.py" in text
            assert "--reindex" in text
            assert "docker-compose.import.yml" in text


def test_import_mode_exposes_postgres_and_elasticsearch_to_host_importer():
    compose_import = _read_script("docker-compose.import.yml")
    assert "postgres:" in compose_import
    assert "elasticsearch:" in compose_import
    assert '"5432:5432"' in compose_import
    assert '"9200:9200"' in compose_import

    for env_dir in ENV_DIRS:
        for script in ["import-new-data.bat", "reimport-data.bat"]:
            text = _read_script(f"{env_dir}/{script}")
            assert "Expose PostgreSQL and Elasticsearch ports" in text
            assert "%COMPOSE_IMPORT% up -d postgres elasticsearch" in text


def test_root_wrappers_delegate_to_prod_scripts():
    expected = {
        "start.bat": r"deploy\prod\start.bat",
        "stop.bat": r"deploy\prod\stop.bat",
        "deploy.bat": r"deploy\prod\deploy.bat",
        "build.bat": r"deploy\prod\build.bat",
        "import.bat": r"deploy\prod\import-new-data.bat",
        "import-new-data.bat": r"deploy\prod\import-new-data.bat",
        "reimport-data.bat": r"deploy\prod\reimport-data.bat",
        "reset-and-reimport-data.bat": r"deploy\prod\reset-and-reimport-data.bat",
        "verify-previews.bat": r"deploy\prod\verify-previews.bat",
        "delete-stale-data.bat": r"deploy\prod\delete-stale-data.bat",
        "restore-from-canonical.bat": r"deploy\prod\restore-from-canonical.bat",
        "backup.bat": r"deploy\prod\backup.bat",
    }
    for wrapper, target in expected.items():
        text = _read_script(wrapper)
        assert target in text


def test_deploy_environments_have_distinct_urls():
    local_env = _read_script("deploy/local/env.bat")
    prod_env = _read_script("deploy/prod/env.bat")
    assert "APP_URL=http://localhost:8081" in local_env
    assert "APP_URL=https://artsearch.testplus.cn" in prod_env
    assert "docker-compose.dev.yml" in local_env
    assert "docker-compose.dev.yml" not in prod_env


def test_build_scripts_compile_frontend_only():
    for env_dir in ENV_DIRS:
        text = _read_script(f"{env_dir}/build.bat")
        assert "npm run build" in text
        assert "npm install" in text
        assert "%COMPOSE% up" not in text
        assert "scripts/import_data.py" not in text


def test_import_scripts_use_environment_backend_url():
    for env_dir in ENV_DIRS:
        for script in ["import-new-data.bat", "reimport-data.bat"]:
            text = _read_script(f"{env_dir}/{script}")
            assert '--backend-url "%APP_URL%"' in text


def test_import_scripts_cover_four_modules_via_four_sources():
    for env_dir in ENV_DIRS:
        for script in ["import-new-data.bat", "reimport-data.bat"]:
            text = _read_script(f"{env_dir}/{script}")
            assert "Import models data" in text
            assert "Import animator data" in text
            assert "Import effects data" in text
            assert "Import icons data" in text
            assert "scripts/import_data.py" in text
            assert "--models-json" in text
            assert "--animator-json" in text
            assert "--effects-json" in text
            assert "--icons-json" in text
            assert 'DATA_ROOT=..\\tag_data_upload' in text
            assert "%DATA_ROOT%\\model\\merged\\model_png_results.json" in text
            assert "%DATA_ROOT%\\animation\\actions_tags_format.json" in text
            assert "%DATA_ROOT%\\effect\\merged\\effect_gif_results.json" in text
            assert "%DATA_ROOT%\\ui\\icon_png_results.json" in text


def test_effect_import_uses_real_effect_data_directory():
    compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    dev_compose_text = (ROOT / "docker-compose.dev.yml").read_text(encoding="utf-8")
    import_text = (ROOT / "scripts" / "import_data.py").read_text(encoding="utf-8")

    assert "./runtime_data/effect/gifs:/data/gifs:ro" in compose_text
    assert "./runtime_data/effect/gifs:/data/gifs:ro" in dev_compose_text
    assert "特效/merged/gifs" not in import_text
    assert "\"runtime_data\" / \"effect\" / \"gifs\"" in import_text
    assert "json_path.parent.parent / \"gifs\"" in import_text

    for env_dir in ENV_DIRS:
        for script in ["import-new-data.bat", "reimport-data.bat"]:
            text = _read_script(f"{env_dir}/{script}")
            assert "effect_gif_results.json" in text
            assert "%DATA_ROOT%\\effect\\merged\\effect_gif_results.json" in text


def test_import_scripts_accept_custom_data_source_arguments():
    for env_dir in ENV_DIRS:
        for script in ["import-new-data.bat", "reimport-data.bat"]:
            text = _read_script(f"{env_dir}/{script}")
            assert "MODELS_JSON_PATH" in text
            assert "IMPORT_MODELS" in text
            assert "EFFECTS_JSON_PATH" in text
            assert "IMPORT_EFFECTS" in text
            assert "ICONS_JSON_PATH" in text
            assert "IMPORT_ICONS" in text
            assert "ANIMATOR_JSON_PATH" in text
            assert "IMPORT_ANIMATOR" in text
            assert "/models" in text
            assert "/effects" in text
            assert "/icons" in text
            assert "/animator" in text
            assert '--models-json "%MODELS_JSON_PATH%"' in text
            assert '--effects-json "%EFFECTS_JSON_PATH%"' in text
            assert '--icons-json "%ICONS_JSON_PATH%"' in text
            assert '--animator-json "%ANIMATOR_JSON_PATH%"' in text


def test_reimport_only_imports_explicit_sources_when_arguments_are_provided():
    for env_dir in ENV_DIRS:
        text = _read_script(f"{env_dir}/reimport-data.bat")
        assert "set \"HAS_EXPLICIT_SOURCE=0\"" in text
        assert "set \"HAS_EXPLICIT_SOURCE=1\"" in text
        assert "if \"%HAS_EXPLICIT_SOURCE%\"==\"0\"" in text
        assert "if \"%IMPORT_MODELS%\"==\"1\"" in text
        assert "if \"%IMPORT_EFFECTS%\"==\"1\"" in text
        assert "if \"%IMPORT_ICONS%\"==\"1\"" in text
        assert "if \"%IMPORT_ANIMATOR%\"==\"1\"" in text
        assert "[SKIP] Models source not requested." in text


def test_import_scripts_stop_after_python_import_failure():
    for env_dir in ENV_DIRS:
        for script in ["import-new-data.bat", "reimport-data.bat"]:
            text = _read_script(f"{env_dir}/{script}")
            assert "goto import_failed" in text
            assert ":import_failed" in text


def test_import_data_prints_source_summary():
    text = (ROOT / "scripts" / "import_data.py").read_text(encoding="utf-8")
    assert "print_import_summary" in text
    assert "total_processed" in text


def test_import_data_supports_explicit_stale_delete_dry_run():
    text = (ROOT / "scripts" / "import_data.py").read_text(encoding="utf-8")
    assert "--delete-stale" in text
    assert "--apply-delete-stale" in text
    assert "delete_stale_assets_for_manifest" in text
    assert "apply=args.apply_delete_stale" in text


def test_import_data_accepts_models_json_as_work_to_do():
    text = (ROOT / "scripts" / "import_data.py").read_text(encoding="utf-8")
    guard_start = text.index("if not any(")
    guard_end = text.index("):", guard_start)
    guard_text = text[guard_start:guard_end]
    assert "args.models_json" in guard_text


def test_import_scripts_do_not_delete_stale_by_default():
    for env_dir in ENV_DIRS:
        for script in ["import-new-data.bat", "reimport-data.bat"]:
            text = _read_script(f"{env_dir}/{script}")
            assert "--delete-stale" not in text
            assert "--apply-delete-stale" not in text


def test_delete_stale_scripts_are_dry_run_until_apply_flag():
    for env_dir in ENV_DIRS:
        text = _read_script(f"{env_dir}/delete-stale-data.bat")
        assert "--delete-stale" in text
        assert "APPLY_DELETE_STALE=0" in text
        assert "APPLY_DELETE_STALE=1" in text
        assert "--apply-delete-stale" in text
        assert "--reindex" in text
        assert "--verify-previews" in text
        assert 'DATA_ROOT=..\\tag_data_upload' in text
        assert "%DATA_ROOT%\\model\\merged\\model_png_results.json" in text
        assert "%DATA_ROOT%\\animation\\actions_tags_format.json" in text
        assert "%DATA_ROOT%\\effect\\merged\\effect_gif_results.json" in text
        assert "%DATA_ROOT%\\ui\\icon_png_results.json" in text


def test_reset_and_reimport_scripts_require_explicit_confirmation():
    for env_dir in ENV_DIRS:
        text = _read_script(f"{env_dir}/reset-and-reimport-data.bat")
        assert "RESET CONFIRM" in text
        assert "--reset-db" in text
        assert "reimport-data.bat" in text
        assert "This clears imported DB rows" in text
        assert "does not remove Docker volumes" in text


def test_verify_preview_scripts_use_environment_backend_url():
    for env_dir in ENV_DIRS:
        text = _read_script(f"{env_dir}/verify-previews.bat")
        assert "--verify-previews" in text
        assert '--backend-url "%APP_URL%"' in text
        assert "--verify-sample-size" in text
        assert "scripts/import_data.py" in text


def test_import_data_syncs_tag_values_for_all_modules():
    text = (ROOT / "scripts" / "import_data.py").read_text(encoding="utf-8")
    assert "sync_model_tag_values" in text
    assert "sync_animator_tag_values" in text
    assert "sync_effect_tag_values" in text
    assert "sync_icon_tag_values" in text


def test_import_scripts_cover_animator_json_source():
    text = (ROOT / "scripts" / "import_data.py").read_text(encoding="utf-8")
    assert "--animator-json" in text
    assert "import_animator_json" in text

    for env_dir in ENV_DIRS:
        for script in ["import-new-data.bat", "reimport-data.bat"]:
            script_text = _read_script(f"{env_dir}/{script}")
            assert "actions_tags_format.json" in script_text
            assert "Import animator data" in script_text


def test_init_sql_contains_animator_json_tag_fields():
    text = _read_script("sql/002_init_tags.sql")
    assert "(3, 'resource_type'" in text
    assert "(3, 'weapon_type'" in text
    assert "(3, 'core_action'" in text
    assert "(3, 'gif_left_path'" in text
    assert "(3, 'action_id',     '动作ID',   'number_range', false, false, false, 4)" in text
    assert "(3, 'size_bytes',    '文件大小', 'number_range', false, false, false, 21)" in text


def test_backend_importers_do_not_depend_on_repo_scripts_path():
    for path in [
        ROOT / "backend/app/importers/animator_importer.py",
        ROOT / "backend/app/importers/effects_importer.py",
        ROOT / "backend/app/importers/icon_importer.py",
    ]:
        text = path.read_text(encoding="utf-8")
        assert "parents[3] / \"scripts\"" not in text
        assert "from app.importers.canonical_data import" in text


def test_compose_mounts_runtime_icon_pngs_dir_for_frontend_icons():
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "./runtime_data/ui/pngs:/data/icons:ro" in text
    dev_text = (ROOT / "docker-compose.dev.yml").read_text(encoding="utf-8")
    assert "./runtime_data/ui/pngs:/data/icons:ro" in dev_text


def test_runtime_data_is_gitignored_and_used_for_previews():
    gitignore = _read_script(".gitignore")
    compose = _read_script("docker-compose.yml")
    assert "runtime_data/" in gitignore
    assert "./runtime_data/model/previews:/data/previews/model" in compose
    assert "./runtime_data/animator/previews:/data/previews/animator" in compose


def test_backend_runs_single_worker_for_in_memory_dictionary_consistency():
    compose = _read_script("docker-compose.yml")
    assert "--workers 4" not in compose
    assert "--workers 1" in compose


def test_backend_startup_migrates_animator_tag_definitions():
    main_text = (ROOT / "backend/app/main.py").read_text(encoding="utf-8")
    assert "ensure_animator_tag_definitions" in main_text
    assert "await ensure_animator_tag_definitions(pool)" in main_text


def test_runtime_data_uses_ui_and_animator_module_dirs():
    text = (ROOT / "backend/app/importers/canonical_data.py").read_text(encoding="utf-8")
    docs = _read_script("docs/deployment-guide.md")

    assert '3: "animator"' in text
    assert '4: "ui"' in text
    assert "animator/data.jsonl" in docs
    assert "model/previews/" in docs
    assert "animator/previews/" in docs
    assert "ui/pngs/" in docs


def test_deploy_and_import_scripts_verify_preview_images():
    for env_dir in ENV_DIRS:
        deploy_text = _read_script(f"{env_dir}/deploy.bat")
        assert "--verify-previews" in deploy_text
        assert '--backend-url "%APP_URL%"' in deploy_text

        for script in ["import-new-data.bat", "reimport-data.bat"]:
            text = _read_script(f"{env_dir}/{script}")
            assert "--verify-previews" in text
            assert '--backend-url "%APP_URL%"' in text


def test_restore_from_canonical_scripts_exist_and_reindex():
    for env_dir in ENV_DIRS:
        text = _read_script(f"{env_dir}/restore-from-canonical.bat")
        assert "--from-canonical" in text
        assert "--reindex" in text
        assert "--verify-previews" in text
        assert "docker-compose.import.yml" in text


def test_local_compose_uses_non_production_port():
    dev_text = (ROOT / "docker-compose.dev.yml").read_text(encoding="utf-8")
    assert '"8081:80"' in dev_text
    assert '"8080:80"' not in dev_text


def test_frontend_search_input_uses_cancellable_quiet_requests():
    api_text = (ROOT / "frontend/src/api/search.ts").read_text(encoding="utf-8")
    store_text = (ROOT / "frontend/src/stores/searchStore.ts").read_text(encoding="utf-8")
    search_bar_text = (ROOT / "frontend/src/components/SearchBar.vue").read_text(encoding="utf-8")
    result_grid_text = (ROOT / "frontend/src/components/ResultGrid.vue").read_text(encoding="utf-8")

    assert "signal?: AbortSignal" in api_text
    assert "{ signal }" in api_text
    assert "currentSearchController?.abort()" in store_text
    assert "cancelPendingSearch" in store_text
    assert "store.cancelPendingSearch()" in search_bar_text
    assert "quiet?: boolean" in store_text
    assert "if (!options?.quiet)" in store_text
    assert "store.doSearch({ quiet: true })" in search_bar_text
    assert "}, 500)" in search_bar_text
    assert "store.loading && !store.items.length" in result_grid_text


def test_frontend_zero_count_filter_options_have_explicit_state():
    text = (ROOT / "frontend/src/components/FilterGroup.vue").read_text(encoding="utf-8")
    assert "'is-zero': getFacetCount(opt.value) === 0" in text
    assert "'zero-count': getFacetCount(opt.value) === 0" in text
    assert ".tag-pill.is-zero" in text
    assert ".zero-count" in text


def test_asset_cards_mount_detail_modal_only_when_opened():
    text = (ROOT / "frontend/src/components/AssetCard.vue").read_text(encoding="utf-8")
    assert '<AssetDetailModal v-if="showDetail"' in text
    assert 'fetchpriority="low"' in text


def test_result_grid_batches_card_mounting_for_all_modules():
    text = (ROOT / "frontend/src/components/ResultGrid.vue").read_text(encoding="utf-8")
    assert "INITIAL_RENDER_LIMIT" in text
    assert "visibleItems" in text
    assert "requestAnimationFrame" in text
    assert "v-for=\"item in visibleItems\"" in text


def test_result_grid_explains_zero_result_search_state():
    text = (ROOT / "frontend/src/components/ResultGrid.vue").read_text(encoding="utf-8")
    assert "emptyChips" in text
    assert "当前条件没有匹配资源" in text
    assert "搜索已执行" in text
    assert "clearSearchContext" in text
    assert "只清空搜索词" in text


def test_detail_preview_adapts_to_screen_size():
    text = (ROOT / "frontend/src/components/AssetDetailModal.vue").read_text(encoding="utf-8")
    preview_frame_img_css = text[text.index(".preview-frame img"):text.index(".preview-label")]
    # Image preserves aspect ratio (width/height auto), capped by viewport height
    assert "width: auto" in preview_frame_img_css
    assert "height: auto" in preview_frame_img_css
    assert "max-width: 100%" in preview_frame_img_css
    assert "max-height: calc(90vh - 150px)" in preview_frame_img_css
    # Single-preview branch keeps its own viewport-aware cap
    single_css = text[text.index(".preview-frame.is-single img"):text.index("/* Paired previews")]
    assert "max-height: calc(90vh - 130px)" in single_css
    # Two-column grid so preview + metadata fit one screen
    assert "grid-template-columns: minmax(0, 1fr) 320px" in text
    # Stacks vertically on narrow viewports
    assert "@media (max-width: 880px)" in text
    assert 'v-if="isIcon"' in text
    assert "icon-preview-pair" in text
    assert "is-icon-original" in text
    assert "is-icon-zoom" in text


def test_detail_gif_previews_stay_side_by_side():
    text = (ROOT / "frontend/src/components/AssetDetailModal.vue").read_text(encoding="utf-8")
    effect_css = text[text.index(".effect-previews,"):text.index(".effect-previews .preview-frame")]
    frame_css = text[text.index(".effect-previews .preview-frame,"):text.index(".preview-frame img")]
    # Dialog widens for paired GIF modules so both fit at natural size when viewport allows
    assert ':width="dialogWidth"' in text
    assert "const dialogWidth = computed" in text
    assert "min(1280px, 96vw)" in text
    # Container tries natural size but caps at 100% — GIFs stay side by side
    assert "width: max-content" in effect_css
    assert "flex-wrap: nowrap" in effect_css
    assert "justify-content: center" in effect_css
    # Frames shrink together (flex-shrink enabled, min-width: 0) when viewport too narrow
    assert "flex: 0 1 auto" in frame_css
    assert "min-width: 0" in frame_css
    assert "max-width: calc((100% - 10px) / 2)" in frame_css
