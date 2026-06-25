from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENV_DIRS = [
    "deploy/local",
    "deploy/prod",
]
SCRIPT_NAMES = [
    "start.bat",
    "stop.bat",
    "deploy.bat",
    "import-new-data.bat",
    "reimport-data.bat",
    "restore-from-canonical.bat",
    "backup.bat",
]
ROOT_WRAPPERS = [
    "start.bat",
    "stop.bat",
    "deploy.bat",
    "import.bat",
    "import-new-data.bat",
    "reimport-data.bat",
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
        "import.bat": r"deploy\prod\import-new-data.bat",
        "import-new-data.bat": r"deploy\prod\import-new-data.bat",
        "reimport-data.bat": r"deploy\prod\reimport-data.bat",
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


def test_import_scripts_use_environment_backend_url():
    for env_dir in ENV_DIRS:
        for script in ["import-new-data.bat", "reimport-data.bat"]:
            text = _read_script(f"{env_dir}/{script}")
            assert '--backend-url "%APP_URL%"' in text


def test_import_scripts_cover_four_modules_via_three_sources():
    for env_dir in ENV_DIRS:
        for script in ["import-new-data.bat", "reimport-data.bat"]:
            text = _read_script(f"{env_dir}/{script}")
            assert "Import Excel data" in text
            assert "Import effects data" in text
            assert "Import icons data" in text
            assert "scripts/import_data.py" in text
            assert "--excel" in text
            assert "--effects-json" in text
            assert "--icons-json" in text
            assert "icon_png_results\\icon_png_results.json" in text


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
            assert "merged" not in text


def test_import_scripts_accept_custom_data_source_arguments():
    for env_dir in ENV_DIRS:
        for script in ["import-new-data.bat", "reimport-data.bat"]:
            text = _read_script(f"{env_dir}/{script}")
            assert "EXCEL_PATH" in text
            assert "IMPORT_EXCEL" in text
            assert "EFFECTS_JSON_PATH" in text
            assert "IMPORT_EFFECTS" in text
            assert "ICONS_JSON_PATH" in text
            assert "IMPORT_ICONS" in text
            assert "/excel" in text
            assert "/effects" in text
            assert "/icons" in text
            assert '--excel "%EXCEL_PATH%"' in text
            assert '--effects-json "%EFFECTS_JSON_PATH%"' in text
            assert '--icons-json "%ICONS_JSON_PATH%"' in text


def test_reimport_only_imports_explicit_sources_when_arguments_are_provided():
    for env_dir in ENV_DIRS:
        text = _read_script(f"{env_dir}/reimport-data.bat")
        assert "set \"HAS_EXPLICIT_SOURCE=0\"" in text
        assert "set \"HAS_EXPLICIT_SOURCE=1\"" in text
        assert "if \"%HAS_EXPLICIT_SOURCE%\"==\"0\"" in text
        assert "if \"%IMPORT_EXCEL%\"==\"1\"" in text
        assert "if \"%IMPORT_EFFECTS%\"==\"1\"" in text
        assert "if \"%IMPORT_ICONS%\"==\"1\"" in text
        assert "[SKIP] Excel source not requested." in text


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


def test_import_data_syncs_tag_values_for_three_visible_modules():
    text = (ROOT / "scripts" / "import_data.py").read_text(encoding="utf-8")
    assert "extract_enum_values_from_excel" in text
    assert "sync_effect_tag_values" in text
    assert "sync_icon_tag_values" in text


def test_compose_mounts_runtime_icon_pngs_dir_for_frontend_icons():
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "./runtime_data/ui/pngs:/data/icons:ro" in text
    dev_text = (ROOT / "docker-compose.dev.yml").read_text(encoding="utf-8")
    assert "./runtime_data/ui/pngs:/data/icons:ro" in dev_text


def test_runtime_data_is_gitignored_and_used_for_previews():
    gitignore = _read_script(".gitignore")
    compose = _read_script("docker-compose.yml")
    assert "runtime_data/" in gitignore
    assert "./runtime_data/previews:/data/previews" in compose


def test_runtime_data_uses_ui_and_animator_module_dirs():
    text = (ROOT / "scripts" / "canonical_data.py").read_text(encoding="utf-8")
    docs = _read_script("docs/deployment-guide.md")

    assert '3: "animator"' in text
    assert '4: "ui"' in text
    assert "animator/data.jsonl" in docs
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
