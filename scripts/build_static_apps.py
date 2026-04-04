#!/usr/bin/env python3
"""Build static multi-app outputs into docs/."""

import hashlib
from pathlib import Path
import re
import shutil


ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
LEGACY_PATHS = [
    DOCS_DIR / "api",
]

STATIC_TARGETS = [
    (ROOT / "apps" / "hub" / "index.html", DOCS_DIR / "index.html"),
    (ROOT / "apps" / "breadth" / "widget.html", DOCS_DIR / "breadth" / "index.html"),
    (ROOT / "apps" / "breadth" / "dashboard.html", DOCS_DIR / "breadth" / "dashboard" / "index.html"),
    (ROOT / "apps" / "fear-greed" / "widget.html", DOCS_DIR / "fear-greed" / "index.html"),
    (ROOT / "apps" / "fear-greed" / "dashboard.html", DOCS_DIR / "fear-greed" / "dashboard" / "index.html"),
    (ROOT / "apps" / "exchange" / "widget.html", DOCS_DIR / "exchange" / "index.html"),
    (ROOT / "apps" / "exchange" / "dashboard.html", DOCS_DIR / "exchange" / "dashboard" / "index.html"),
]

APP_API_TARGETS = [
    (ROOT / "apps" / "fear-greed" / "api", DOCS_DIR / "fear-greed" / "api"),
    (ROOT / "apps" / "exchange" / "api", DOCS_DIR / "exchange" / "api"),
]

APP_ASSET_TARGETS = [
    (ROOT / "apps" / "breadth" / "vendor", DOCS_DIR / "breadth" / "vendor"),
    (ROOT / "apps" / "hub" / "assets", DOCS_DIR / "assets" / "hub"),
]

APP_ASSET_FILES = [
    (ROOT / "apps" / "hub" / "assets" / "index.css", DOCS_DIR / "assets" / "hub" / "index.css"),
    (ROOT / "apps" / "breadth" / "assets" / "widget.js", DOCS_DIR / "breadth" / "widget.js"),
    (ROOT / "apps" / "breadth" / "assets" / "widget.css", DOCS_DIR / "breadth" / "widget.css"),
    (ROOT / "apps" / "breadth" / "assets" / "dashboard.js", DOCS_DIR / "breadth" / "dashboard.js"),
    (ROOT / "apps" / "breadth" / "assets" / "dashboard.css", DOCS_DIR / "breadth" / "dashboard.css"),
    (ROOT / "apps" / "fear-greed" / "assets" / "widget.js", DOCS_DIR / "fear-greed" / "widget.js"),
    (ROOT / "apps" / "fear-greed" / "assets" / "widget.css", DOCS_DIR / "fear-greed" / "widget.css"),
    (ROOT / "apps" / "fear-greed" / "assets" / "dashboard.js", DOCS_DIR / "fear-greed" / "dashboard.js"),
    (ROOT / "apps" / "fear-greed" / "assets" / "dashboard.css", DOCS_DIR / "fear-greed" / "dashboard.css"),
    (ROOT / "apps" / "exchange" / "assets" / "widget.js", DOCS_DIR / "exchange" / "widget.js"),
    (ROOT / "apps" / "exchange" / "assets" / "widget.css", DOCS_DIR / "exchange" / "widget.css"),
    (ROOT / "apps" / "exchange" / "assets" / "dashboard.js", DOCS_DIR / "exchange" / "dashboard.js"),
    (ROOT / "apps" / "exchange" / "assets" / "dashboard.css", DOCS_DIR / "exchange" / "dashboard.css"),
]

WIDGET_REDIRECT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=/breadth">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Redirecting…</title>
</head>
<body>
  <p><a href="/breadth">Redirect to Breadth Widget</a></p>
</body>
</html>
"""

REDIRECTS = """/widget.html /breadth 301
/api/* /breadth/api/:splat 301
"""

BASE_HEADERS = """/*
  Referrer-Policy: strict-origin-when-cross-origin
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Permissions-Policy: camera=(), microphone=(), geolocation=()
*/
"""

DEFAULT_CSP = """default-src 'self'; script-src 'self'; style-src 'self'; style-src-attr 'none'; img-src 'self' data:; connect-src 'self'; font-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'; upgrade-insecure-requests"""

HTML_ROUTE_TARGETS = {
    "index.html": ["/", "/index.html"],
    "breadth/index.html": ["/breadth", "/breadth/index.html"],
    "breadth/dashboard/index.html": ["/breadth/dashboard", "/breadth/dashboard/index.html"],
    "fear-greed/index.html": ["/fear-greed", "/fear-greed/index.html"],
    "fear-greed/dashboard/index.html": ["/fear-greed/dashboard", "/fear-greed/dashboard/index.html"],
    "exchange/index.html": ["/exchange", "/exchange/index.html"],
    "exchange/dashboard/index.html": ["/exchange/dashboard", "/exchange/dashboard/index.html"],
    "widget.html": ["/widget.html"],
}


def _render_headers() -> str:
    blocks = [BASE_HEADERS.strip()]
    for relative_path, routes in HTML_ROUTE_TARGETS.items():
        for route in routes:
            blocks.append(f"{route}\n  Content-Security-Policy: {DEFAULT_CSP}")
    return "\n\n".join(blocks) + "\n"


def _asset_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for dest in DOCS_DIR.rglob("*"):
        if not dest.is_file() or dest.suffix not in {".js", ".css"}:
            continue
        content = dest.read_bytes()
        digest = hashlib.md5(content).hexdigest()[:10]
        web_path = "/" + dest.relative_to(DOCS_DIR).as_posix()
        versions[web_path] = digest
    return versions


def _rewrite_html_asset_urls(versions: dict[str, str]) -> None:
    html_targets = [dest for _, dest in STATIC_TARGETS]
    html_targets.append(DOCS_DIR / "widget.html")
    for html_path in html_targets:
        if not html_path.exists():
            continue
        content = html_path.read_text(encoding="utf-8")
        def replace_attr(match: re.Match[str]) -> str:
            attr = match.group(1)
            web_path = match.group(2)
            digest = versions.get(web_path)
            if not digest:
                return match.group(0)
            return f'{attr}="{web_path}?v={digest}"'

        updated = re.sub(r'(href|src)="(/[^"?]+\.(?:css|js))"', replace_attr, content)
        if updated != content:
            html_path.write_text(updated, encoding="utf-8")


def build() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    for legacy_path in LEGACY_PATHS:
        if legacy_path.exists():
            shutil.rmtree(legacy_path)

    for src, dest in STATIC_TARGETS:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)

    for src, dest in APP_API_TARGETS:
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)

    for src, dest in APP_ASSET_TARGETS:
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)

    for src, dest in APP_ASSET_FILES:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)

    (DOCS_DIR / "widget.html").write_text(WIDGET_REDIRECT, encoding="utf-8")
    _rewrite_html_asset_urls(_asset_versions())
    (DOCS_DIR / "_redirects").write_text(REDIRECTS, encoding="utf-8")
    (DOCS_DIR / "_headers").write_text(_render_headers(), encoding="utf-8")


if __name__ == "__main__":
    build()
