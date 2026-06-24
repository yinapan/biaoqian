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
    "backup.bat",
]
ROOT_WRAPPERS = [
    "start.bat",
    "stop.bat",
    "deploy.bat",
    "import.bat",
    "import-new-data.bat",
    "reimport-data.bat",
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


def test_root_wrappers_delegate_to_prod_scripts():
    expected = {
        "start.bat": r"deploy\prod\start.bat",
        "stop.bat": r"deploy\prod\stop.bat",
        "deploy.bat": r"deploy\prod\deploy.bat",
        "import.bat": r"deploy\prod\import-new-data.bat",
        "import-new-data.bat": r"deploy\prod\import-new-data.bat",
        "reimport-data.bat": r"deploy\prod\reimport-data.bat",
        "backup.bat": r"deploy\prod\backup.bat",
    }
    for wrapper, target in expected.items():
        text = _read_script(wrapper)
        assert target in text


def test_deploy_environments_have_distinct_urls():
    local_env = _read_script("deploy/local/env.bat")
    prod_env = _read_script("deploy/prod/env.bat")
    assert "APP_URL=http://localhost:8080" in local_env
    assert "APP_URL=https://artsearch.testplus.cn" in prod_env
    assert "docker-compose.dev.yml" in local_env
    assert "docker-compose.dev.yml" not in prod_env


def test_import_scripts_use_environment_backend_url():
    for env_dir in ENV_DIRS:
        for script in ["import-new-data.bat", "reimport-data.bat"]:
            text = _read_script(f"{env_dir}/{script}")
            assert '--backend-url "%APP_URL%"' in text


def test_import_scripts_cover_three_visible_modules():
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

    assert "./特效/gifs:/data/gifs:ro" in compose_text
    assert "./特效/gifs:/data/gifs:ro" in dev_compose_text
    assert "特效/merged/gifs" not in import_text
    assert "特效/gifs" in import_text

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
            assert "EFFECTS_JSON_PATH" in text
            assert "ICONS_JSON_PATH" in text
            assert "/excel" in text
            assert "/effects" in text
            assert "/icons" in text
            assert '--excel "%EXCEL_PATH%"' in text
            assert '--effects-json "%EFFECTS_JSON_PATH%"' in text
            assert '--icons-json "%ICONS_JSON_PATH%"' in text


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


def test_compose_mounts_icon_png_results_for_frontend_icons():
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "./icon_png_results:/data/icons:ro" in text
    dev_text = (ROOT / "docker-compose.dev.yml").read_text(encoding="utf-8")
    assert "./icon_png_results:/data/icons:ro" in dev_text
