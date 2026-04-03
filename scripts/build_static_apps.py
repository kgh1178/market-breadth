#!/usr/bin/env python3
"""Build static multi-app outputs into docs/."""

from pathlib import Path
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

    (DOCS_DIR / "widget.html").write_text(WIDGET_REDIRECT, encoding="utf-8")
    (DOCS_DIR / "_redirects").write_text(REDIRECTS, encoding="utf-8")


if __name__ == "__main__":
    build()
