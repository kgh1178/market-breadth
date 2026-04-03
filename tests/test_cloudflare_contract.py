from pathlib import Path
import json
import subprocess
import tomllib


REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_static_apps.py"
API_DIR = DOCS_DIR / "breadth" / "api"
API_WORKER_WRANGLER = REPO_ROOT / "cloudflare" / "api-worker" / "wrangler.toml"
API_WORKER_SOURCE = REPO_ROOT / "cloudflare" / "api-worker" / "src" / "index.ts"
PRODUCERS_DIR = REPO_ROOT / "cloudflare" / "producers"


def _build_static_outputs() -> None:
    subprocess.run(
        ["python3", str(BUILD_SCRIPT)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_cloudflare_api_worker_wrangler_maps_domain_and_r2_bucket():
    config = tomllib.loads(API_WORKER_WRANGLER.read_text())

    assert config["name"] == "jstockinsight-api"
    assert config["main"] == "src/index.ts"
    assert config["routes"] == [
        {"pattern": "api.jstockinsight.kr/breadth/api/*", "zone_name": "jstockinsight.kr"},
        {"pattern": "api.jstockinsight.kr/fear-greed/api/*", "zone_name": "jstockinsight.kr"},
        {"pattern": "api.jstockinsight.kr/exchange/api/*", "zone_name": "jstockinsight.kr"},
    ]
    assert config["r2_buckets"] == [
        {"binding": "APP_DATA", "bucket_name": "jstockinsight-app-data"}
    ]


def test_cloudflare_api_worker_source_routes_app_api_paths_to_r2_prefix():
    source = API_WORKER_SOURCE.read_text()

    assert 'new Set(["breadth", "fear-greed", "exchange"])' in source
    assert r"url.pathname.match(/^\/([^/]+)\/api\/(.+)$/)" in source
    assert 'const key = `${app}/${rest}`;' in source
    assert '"cache-control": "public, max-age=300"' in source
    assert '"content-type": "application/json; charset=utf-8"' in source


def test_cloudflare_producer_configs_share_bucket_and_breadth_schedule():
    breadth_config = tomllib.loads((PRODUCERS_DIR / "breadth" / "wrangler.toml").read_text())
    fear_config = tomllib.loads((PRODUCERS_DIR / "fear-greed" / "wrangler.toml").read_text())
    exchange_config = tomllib.loads((PRODUCERS_DIR / "exchange" / "wrangler.toml").read_text())

    assert breadth_config["r2_buckets"] == [
        {"binding": "APP_DATA", "bucket_name": "jstockinsight-app-data"}
    ]
    assert fear_config["r2_buckets"] == [
        {"binding": "APP_DATA", "bucket_name": "jstockinsight-app-data"}
    ]
    assert exchange_config["r2_buckets"] == [
        {"binding": "APP_DATA", "bucket_name": "jstockinsight-app-data"}
    ]
    assert breadth_config["triggers"]["crons"] == [
        "30 6 * * 2-6",
        "0 8 * * 2-6",
    ]


def test_cloudflare_producers_expose_fetch_health_response():
    breadth_source = (PRODUCERS_DIR / "breadth" / "src" / "index.ts").read_text()
    fear_source = (PRODUCERS_DIR / "fear-greed" / "src" / "index.ts").read_text()
    exchange_source = (PRODUCERS_DIR / "exchange" / "src" / "index.ts").read_text()

    for source in [breadth_source, fear_source, exchange_source]:
        assert "async fetch()" in source
        assert 'role: "scheduled-producer"' in source
        assert 'status: "ok"' in source


def test_breadth_cloudflare_api_contract_uses_structured_market_metadata():
    _build_static_outputs()

    latest = json.loads((API_DIR / "latest.json").read_text())
    signals = json.loads((API_DIR / "signals.json").read_text())
    metadata = json.loads((API_DIR / "metadata.json").read_text())

    assert "date" in latest
    assert "pipeline_date" in latest
    assert metadata["price_column"] == "Close"
    assert metadata["yfinance_auto_adjust"] is False
    assert signals["partial_data"] in (True, False)

    required_market_fields = {
        "status",
        "as_of_date",
        "series_valid",
        "metrics_valid",
        "price_basis",
        "error_code",
        "error_message",
    }
    for market_id in ["sp500", "nikkei225", "kospi200"]:
        payload = latest[market_id]
        assert required_market_fields.issubset(payload.keys())

        market_series = API_DIR / f"{market_id}.json"
        if payload["status"] == "ok":
            assert payload["series_valid"] is True
            assert payload["metrics_valid"] is True
            assert payload["as_of_date"]
            assert market_series.exists()
        else:
            assert payload["status"] in {"partial", "error"}
            assert payload["series_valid"] is False
            assert payload["metrics_valid"] is False
            assert not market_series.exists()


def test_cloudflare_redirects_preserve_legacy_widget_and_api_links():
    _build_static_outputs()

    redirects = (DOCS_DIR / "_redirects").read_text().strip().splitlines()
    assert "/widget.html /breadth 301" in redirects
    assert "/api/* /breadth/api/:splat 301" in redirects
