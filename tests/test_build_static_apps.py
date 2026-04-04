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
    assert (DOCS_DIR / "_headers").exists()
    assert (DOCS_DIR / "assets" / "hub" / "index.js").exists()
    assert (DOCS_DIR / "assets" / "hub" / "index.css").exists()
    assert (DOCS_DIR / "breadth" / "index.html").exists()
    assert (DOCS_DIR / "breadth" / "dashboard" / "index.html").exists()
    assert (DOCS_DIR / "breadth" / "widget.js").exists()
    assert (DOCS_DIR / "breadth" / "widget.css").exists()
    assert (DOCS_DIR / "breadth" / "dashboard.js").exists()
    assert (DOCS_DIR / "breadth" / "dashboard.css").exists()
    assert (DOCS_DIR / "fear-greed" / "index.html").exists()
    assert (DOCS_DIR / "fear-greed" / "dashboard" / "index.html").exists()
    assert (DOCS_DIR / "fear-greed" / "widget.js").exists()
    assert (DOCS_DIR / "fear-greed" / "widget.css").exists()
    assert (DOCS_DIR / "fear-greed" / "dashboard.js").exists()
    assert (DOCS_DIR / "fear-greed" / "dashboard.css").exists()
    assert (DOCS_DIR / "fear-greed" / "api" / "latest.json").exists()
    assert (DOCS_DIR / "fear-greed" / "api" / "metadata.json").exists()
    assert (DOCS_DIR / "fear-greed" / "api" / "schema.json").exists()
    assert (DOCS_DIR / "exchange" / "index.html").exists()
    assert (DOCS_DIR / "exchange" / "dashboard" / "index.html").exists()
    assert (DOCS_DIR / "exchange" / "widget.js").exists()
    assert (DOCS_DIR / "exchange" / "widget.css").exists()
    assert (DOCS_DIR / "exchange" / "dashboard.js").exists()
    assert (DOCS_DIR / "exchange" / "dashboard.css").exists()
    assert (DOCS_DIR / "exchange" / "api" / "latest.json").exists()
    assert (DOCS_DIR / "exchange" / "api" / "metadata.json").exists()
    assert (DOCS_DIR / "exchange" / "api" / "schema.json").exists()
    assert not (DOCS_DIR / "api").exists()

    assert "<style>" not in (DOCS_DIR / "index.html").read_text(encoding="utf-8")
    assert 'rel="stylesheet" href="/assets/hub/index.css"' in (DOCS_DIR / "index.html").read_text(encoding="utf-8")
    assert "<style>" not in (DOCS_DIR / "breadth" / "index.html").read_text(encoding="utf-8")
    assert 'rel="stylesheet" href="/breadth/widget.css"' in (DOCS_DIR / "breadth" / "index.html").read_text(encoding="utf-8")
    assert "<style>" not in (DOCS_DIR / "breadth" / "dashboard" / "index.html").read_text(encoding="utf-8")
    assert 'rel="stylesheet" href="/breadth/dashboard.css"' in (DOCS_DIR / "breadth" / "dashboard" / "index.html").read_text(encoding="utf-8")
    fear_widget = (DOCS_DIR / "fear-greed" / "index.html").read_text(encoding="utf-8")
    fear_dashboard = (DOCS_DIR / "fear-greed" / "dashboard" / "index.html").read_text(encoding="utf-8")
    assert 'href="/fear-greed/dashboard"' in fear_widget
    assert 'href="/fear-greed/api/latest.json"' not in fear_widget
    assert 'href="/fear-greed/api/schema.json"' not in fear_widget
    assert 'href="/"' not in fear_widget
    assert 'id="marketGrid"' in fear_widget
    assert 'href="/fear-greed/api/metadata.json"' in fear_dashboard
    assert 'href="/fear-greed/api/schema.json"' in fear_dashboard
    assert 'id="overviewGrid"' in fear_dashboard
    assert 'id="detailGrid"' in fear_dashboard

    headers = (DOCS_DIR / "_headers").read_text(encoding="utf-8")
    assert "*/" in headers
    assert "Content-Security-Policy:" in headers
    assert "script-src 'self'" in headers
    assert "script-src 'self' 'unsafe-inline'" not in headers
    assert "style-src 'self'" in headers
    assert "style-src 'self' 'unsafe-inline'" not in headers
    assert "style-src-attr 'none'" in headers
    assert "sha256-" not in headers
    assert "object-src 'none'" in headers
    assert "frame-ancestors 'none'" in headers
