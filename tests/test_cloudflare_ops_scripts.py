from pathlib import Path
import os
import subprocess


REPO_ROOT = Path(__file__).resolve().parent.parent
SYNC_SCRIPT = REPO_ROOT / "scripts" / "cloudflare_sync_r2.sh"
DEPLOY_SCRIPT = REPO_ROOT / "scripts" / "cloudflare_deploy_workers.sh"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_static_apps.py"
REFRESH_SCRIPT = REPO_ROOT / "scripts" / "cloudflare_refresh_app.sh"


def _build_static_outputs() -> None:
    subprocess.run(
        ["python3", str(BUILD_SCRIPT)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_cloudflare_sync_r2_dry_run_lists_expected_upload_commands():
    _build_static_outputs()

    result = subprocess.run(
        [str(SYNC_SCRIPT), "--dry-run"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )

    stdout = result.stdout
    assert "app=breadth" in stdout
    assert "jstockinsight-app-data/breadth/latest.json" in stdout
    assert "jstockinsight-app-data/breadth/signals.json" in stdout
    assert "npx wrangler r2 object put" in stdout
    assert "--remote" in stdout


def test_cloudflare_sync_r2_app_override_updates_api_dir():
    _build_static_outputs()

    result = subprocess.run(
        [str(SYNC_SCRIPT), "--dry-run", "--app", "exchange"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )

    stdout = result.stdout
    assert "app=exchange" in stdout
    assert f"api_dir={REPO_ROOT / 'docs' / 'exchange' / 'api'}" in stdout
    assert "jstockinsight-app-data/exchange/latest.json" in stdout


def test_cloudflare_deploy_workers_dry_run_lists_expected_targets():
    env = os.environ.copy()
    env["DRY_RUN"] = "1"

    result = subprocess.run(
        [str(DEPLOY_SCRIPT), "all"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )

    stdout = result.stdout
    assert "api-worker" in stdout
    assert "breadth-producer" in stdout
    assert "fear-greed-producer" in stdout
    assert "exchange-producer" in stdout
    assert "npx wrangler deploy" in stdout


def test_cloudflare_refresh_app_dry_run_lists_exchange_flow():
    env = os.environ.copy()
    env["DRY_RUN"] = "1"
    env["PYTHON_BIN"] = "/usr/local/bin/python3"

    result = subprocess.run(
        ["/bin/zsh", str(REFRESH_SCRIPT), "exchange"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )

    stdout = result.stdout
    assert "generating exchange payloads" in stdout
    assert "using python: /usr/local/bin/python3" in stdout
    assert "/usr/local/bin/python3 scripts/generate_exchange_json.py" in stdout
    assert "/usr/local/bin/python3 scripts/build_static_apps.py" in stdout
    assert "scripts/cloudflare_sync_r2.sh --app exchange" in stdout
