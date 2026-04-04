from pathlib import Path
import json
import subprocess
import tomllib


REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_static_apps.py"
API_DIR = DOCS_DIR / "breadth" / "api"
FEAR_GREED_API_DIR = DOCS_DIR / "fear-greed" / "api"
EXCHANGE_API_DIR = DOCS_DIR / "exchange" / "api"
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
        {"pattern": "api.jstockinsight.kr/lotopick", "zone_name": "jstockinsight.kr"},
        {"pattern": "api.jstockinsight.kr/lotopick/*", "zone_name": "jstockinsight.kr"},
    ]
    assert config["r2_buckets"] == [
        {"binding": "APP_DATA", "bucket_name": "jstockinsight-app-data"}
    ]


def test_cloudflare_api_worker_source_routes_app_api_paths_to_r2_prefix():
    source = API_WORKER_SOURCE.read_text()

    assert 'new Set(["breadth", "fear-greed", "exchange"])' in source
    assert 'const LOTOPICK_PUBLIC_BASE = "/lotopick";' in source
    assert 'const LOTOPICK_NEXT_ASSET_PREFIX = `${LOTOPICK_PUBLIC_BASE}/_next/`;' in source
    assert 'LOTOPICK_ORIGIN?: string;' in source
    assert 'return pathname === LOTOPICK_PUBLIC_BASE || pathname.startsWith(`${LOTOPICK_PUBLIC_BASE}/`);' in source
    assert 'requestUrl.pathname.startsWith(LOTOPICK_NEXT_ASSET_PREFIX)' in source
    assert 'requestUrl.pathname.replace(LOTOPICK_PUBLIC_BASE, "")' in source
    assert 'return serviceUnavailable("LotoPick origin is not configured");' in source
    assert 'forwardedHeaders.set("x-lotopick-public-origin", new URL(request.url).origin);' in source
    assert 'const upstreamRequest = new Request(upstreamUrl.toString(), {' in source
    assert 'const upstreamResponse = await fetch(upstreamRequest);' in source
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


def test_cloudflare_pages_headers_publish_security_baseline():
    _build_static_outputs()

    headers = (DOCS_DIR / "_headers").read_text()
    assert "*/" in headers
    assert "Content-Security-Policy:" in headers
    assert "default-src 'self'" in headers
    assert "connect-src 'self'" in headers
    assert "script-src 'self'" in headers
    assert "script-src 'self' 'unsafe-inline'" not in headers
    assert "style-src 'self'" in headers
    assert "style-src 'self' 'unsafe-inline'" not in headers
    assert "style-src-attr 'none'" in headers
    assert "sha256-" not in headers
    assert "object-src 'none'" in headers
    assert "frame-ancestors 'none'" in headers
    assert "X-Content-Type-Options: nosniff" in headers
    assert "X-Frame-Options: DENY" in headers


def test_fear_greed_contract_matches_multi_market_api_shape():
    _build_static_outputs()

    app_id = "fear-greed"
    latest = json.loads((FEAR_GREED_API_DIR / "latest.json").read_text())
    metadata = json.loads((FEAR_GREED_API_DIR / "metadata.json").read_text())
    schema = json.loads((FEAR_GREED_API_DIR / "schema.json").read_text())

    assert latest["app_id"] == app_id
    assert latest["status"] in {"ok", "partial", "error"}
    assert latest["api_base"] == f"/{app_id}/api"
    assert latest["default_market"] == "us"
    assert set(latest["markets"].keys()) == {"us", "kr", "jp", "crypto"}
    for market_id in ("us", "kr", "jp", "crypto"):
        market = latest["markets"][market_id]
        assert {"status", "as_of_date", "series_valid", "metrics_valid", "market", "market_id", "score", "components", "signals"}.issubset(market.keys())
        assert market["market_id"] == market_id

    assert metadata["app_id"] == app_id
    assert metadata["status_contract"]["status"] in {"ok", "partial", "error"}
    assert metadata["paths"]["widget"] == f"/{app_id}"
    assert metadata["paths"]["dashboard"] == f"/{app_id}/dashboard"
    assert set(metadata["markets"].keys()) == {"us", "kr", "jp", "crypto"}
    assert schema["app_id"] == app_id
    assert schema["version"] == "draft-2026-04-04-market-split"
    assert schema["endpoints"]["latest"] == f"/{app_id}/api/latest.json"
    assert schema["endpoints"]["metadata"] == f"/{app_id}/api/metadata.json"


def test_exchange_contract_matches_live_structured_api_shape():
    _build_static_outputs()

    latest = json.loads((EXCHANGE_API_DIR / "latest.json").read_text())
    metadata = json.loads((EXCHANGE_API_DIR / "metadata.json").read_text())
    schema = json.loads((EXCHANGE_API_DIR / "schema.json").read_text())

    assert latest["app_id"] == "exchange"
    assert latest["status"] in {"ok", "partial", "error", "placeholder"}
    assert latest["api_base"] == "/exchange/api"
    assert latest["widget_path"] == "/exchange"
    assert latest["dashboard_path"] == "/exchange/dashboard"
    assert set(latest["pairs"].keys()) == {"USDKRW", "USDJPY", "EURUSD"}
    assert set(latest["signals"].keys()) == {"krw_risk_alert", "yen_breakout_alert"}

    assert metadata["app_id"] == "exchange"
    assert metadata["paths"]["widget"] == "/exchange"
    assert metadata["paths"]["dashboard"] == "/exchange/dashboard"
    assert metadata["paths"]["api_base"] == "/exchange/api"
    assert set(metadata["pairs"].keys()) == {"USDKRW", "USDJPY", "EURUSD"}

    assert schema["app_id"] == "exchange"
    assert schema["version"] == "draft-2026-04-04"
    assert schema["endpoints"]["latest"] == "/exchange/api/latest.json"
    assert schema["endpoints"]["metadata"] == "/exchange/api/metadata.json"
