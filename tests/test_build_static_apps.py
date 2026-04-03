from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_static_apps.py"
DOCS_DIR = REPO_ROOT / "docs"


def test_build_static_apps_generates_multi_app_routes():
    subprocess.run(
        ["python3", str(BUILD_SCRIPT)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert (DOCS_DIR / "index.html").exists()
    assert (DOCS_DIR / "widget.html").exists()
    assert (DOCS_DIR / "_redirects").exists()
    assert (DOCS_DIR / "breadth" / "index.html").exists()
    assert (DOCS_DIR / "breadth" / "dashboard" / "index.html").exists()
    assert (DOCS_DIR / "fear-greed" / "index.html").exists()
    assert (DOCS_DIR / "fear-greed" / "dashboard" / "index.html").exists()
    assert (DOCS_DIR / "exchange" / "index.html").exists()
    assert (DOCS_DIR / "exchange" / "dashboard" / "index.html").exists()
    assert not (DOCS_DIR / "api").exists()
