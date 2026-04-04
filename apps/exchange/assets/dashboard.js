const I18N = {
  en: {
    eyebrow: "Cross-Market FX",
    title: "Exchange Dashboard",
    copy: "A structured FX monitor for USD-led pairs, regime tags, and alert states. The dashboard renders only what the pipeline declares valid.",
    widget: "Widget",
    api: "API Metadata",
    schema: "API Schema",
    home: "App Hub",
    loading: "Loading…",
    status_ok: "Healthy",
    status_partial: "Partial",
    status_error: "Unavailable",
    status_placeholder: "Placeholder",
    status_copy: "Fetching `/exchange/api/latest.json`.",
    fetch_error: "Could not load exchange API data.",
    status_label: "Status",
    updated: "Pipeline date",
    pairs: "Pairs",
    pair_title: "Major exchange pairs",
    coverage: "{ready}/{total} pairs ready",
    regime: "Regime",
    alerts: "Alerts",
    source: "Data source",
    as_of_prefix: "As of",
    signal_on: "Active",
    signal_off: "Inactive",
    usd_strength: "USD strength",
    asia_fx_pressure: "Asia FX pressure",
    krw_risk_alert: "KRW risk alert",
    yen_breakout_alert: "Yen breakout alert",
    primary_source: "Primary source",
    tickers: "Tickers",
    period: "Lookback",
    daily_change: "Daily change",
    z_score: "20d z-score",
    no_pairs: "No valid pair metrics are available yet."
  },
  ko: {
    eyebrow: "크로스마켓 FX",
    title: "환율 대시보드",
    copy: "달러 중심 통화쌍, 레짐 태그, 경보 상태를 함께 보는 구조화 FX 모니터입니다. 파이프라인이 유효하다고 선언한 값만 렌더링합니다.",
    widget: "위젯",
    api: "API 메타데이터",
    schema: "API 스키마",
    home: "앱 허브",
    loading: "불러오는 중…",
    status_ok: "정상",
    status_partial: "부분",
    status_error: "사용 불가",
    status_placeholder: "플레이스홀더",
    status_copy: "`/exchange/api/latest.json`을 불러오는 중입니다.",
    fetch_error: "환율 API 데이터를 불러오지 못했습니다.",
    status_label: "상태",
    updated: "파이프라인 날짜",
    pairs: "통화쌍",
    pair_title: "주요 환율 페어",
    coverage: "{ready}/{total} 통화쌍 준비됨",
    regime: "레짐",
    alerts: "알림",
    source: "데이터 소스",
    as_of_prefix: "기준일",
    signal_on: "활성",
    signal_off: "비활성",
    usd_strength: "달러 강도",
    asia_fx_pressure: "아시아 FX 압력",
    krw_risk_alert: "원화 리스크 알림",
    yen_breakout_alert: "엔화 돌파 알림",
    primary_source: "기본 소스",
    tickers: "티커",
    period: "조회 기간",
    daily_change: "일간 변화",
    z_score: "20일 Z점수",
    no_pairs: "표시할 유효 환율 데이터가 아직 없습니다."
  },
  ja: {
    eyebrow: "クロスマーケット FX",
    title: "為替ダッシュボード",
    copy: "ドル中心の通貨ペア、レジームタグ、警報状態をまとめて見る構造化 FX モニターです。パイプラインが有効と宣言した値だけを描画します。",
    widget: "ウィジェット",
    api: "APIメタデータ",
    schema: "APIスキーマ",
    home: "アプリハブ",
    loading: "読み込み中…",
    status_ok: "正常",
    status_partial: "部分",
    status_error: "利用不可",
    status_placeholder: "プレースホルダー",
    status_copy: "`/exchange/api/latest.json` を読み込み中です。",
    fetch_error: "為替APIデータを読み込めませんでした。",
    status_label: "状態",
    updated: "パイプライン日付",
    pairs: "ペア",
    pair_title: "主要為替ペア",
    coverage: "{ready}/{total} ペア準備完了",
    regime: "レジーム",
    alerts: "アラート",
    source: "データソース",
    as_of_prefix: "基準日",
    signal_on: "有効",
    signal_off: "無効",
    usd_strength: "ドル強度",
    asia_fx_pressure: "アジア FX 圧力",
    krw_risk_alert: "ウォンリスク警報",
    yen_breakout_alert: "円ブレイクアウト警報",
    primary_source: "主要ソース",
    tickers: "ティッカー",
    period: "参照期間",
    daily_change: "日次変化",
    z_score: "20日 Zスコア",
    no_pairs: "表示できる有効な為替データがまだありません。"
  }
};

const PAIR_META = {
  USDKRW: { label: "USD/KRW", accent: "#d93025", digits: 2 },
  USDJPY: { label: "USD/JPY", accent: "#2563eb", digits: 3 },
  EURUSD: { label: "EUR/USD", accent: "#0f766e", digits: 4 }
};

const params = new URLSearchParams(window.location.search);
const preferred = params.get("lang");
const navigatorLangs = [...(navigator.languages || []), navigator.language]
  .filter(Boolean)
  .map((value) => String(value).toLowerCase());
const lang = preferred && ["ko", "ja", "en"].includes(preferred)
  ? preferred
  : navigatorLangs.some((value) => value.startsWith("ko"))
    ? "ko"
    : navigatorLangs.some((value) => value.startsWith("ja"))
      ? "ja"
      : "en";
const t = I18N[lang];

function interpolate(template, values) {
  return template.replace(/\{(\w+)\}/g, (_, key) => values[key] ?? "");
}

function formatPairValue(pairKey, value) {
  if (value == null || Number.isNaN(value)) return "-";
  return Number(value).toFixed(PAIR_META[pairKey]?.digits ?? 2);
}

function formatPercent(value) {
  if (value == null || Number.isNaN(value)) return "-";
  const sign = value > 0 ? "+" : "";
  return `${sign}${Number(value).toFixed(2)}%`;
}

function formatZ(value) {
  if (value == null || Number.isNaN(value)) return "-";
  const sign = value > 0 ? "+" : "";
  return `${sign}${Number(value).toFixed(2)}`;
}

function severityClass(value) {
  if (value > 0) return "pos";
  if (value < 0) return "neg";
  return "flat";
}

function renderPairs(data) {
  const pairGrid = document.getElementById("pairGrid");
  const entries = Object.entries(data.pairs || {}).filter(([, pair]) => pair && pair.value != null);
  document.getElementById("coverageValue").textContent = interpolate(t.coverage, {
    ready: entries.length,
    total: Object.keys(PAIR_META).length
  });

  if (!entries.length) {
    pairGrid.innerHTML = `<div class="detail-row"><strong>${t.no_pairs}</strong><span>-</span></div>`;
    return;
  }

  pairGrid.innerHTML = entries.map(([key, pair]) => `
    <article class="pair-card" style="--accent:${PAIR_META[key]?.accent || "#2563eb"}">
      <div class="pair-symbol">${key}</div>
      <div class="pair-label">${PAIR_META[key]?.label || key}</div>
      <div class="pair-value">${formatPairValue(key, pair.value)}</div>
      <div class="pair-sub ${severityClass(pair.daily_change_pct)}">${formatPercent(pair.daily_change_pct)}</div>
      <div class="pair-metrics">
        <div class="metric">
          <span class="metric-label">${t.daily_change}</span>
          <span class="metric-value ${severityClass(pair.daily_change_pct)}">${formatPercent(pair.daily_change_pct)}</span>
        </div>
        <div class="metric">
          <span class="metric-label">${t.z_score}</span>
          <span class="metric-value ${severityClass(pair.z_score_20d)}">${formatZ(pair.z_score_20d)}</span>
        </div>
      </div>
    </article>
  `).join("");
}

function renderDetailRow(label, value) {
  return `<div class="detail-row"><strong>${label}</strong><span>${value}</span></div>`;
}

function renderRegime(data) {
  const regime = data.regime || {};
  document.getElementById("regimeItems").innerHTML = [
    renderDetailRow(t.usd_strength, regime.usd_strength || "-"),
    renderDetailRow(t.asia_fx_pressure, regime.asia_fx_pressure || "-")
  ].join("");
}

function renderSignals(data) {
  const signals = data.signals || {};
  document.getElementById("signalItems").innerHTML = [
    `<div class="detail-row"><strong>${t.krw_risk_alert}</strong><span><span class="badge ${signals.krw_risk_alert ? "alert" : "good"}">${signals.krw_risk_alert ? t.signal_on : t.signal_off}</span></span></div>`,
    `<div class="detail-row"><strong>${t.yen_breakout_alert}</strong><span><span class="badge ${signals.yen_breakout_alert ? "alert" : "good"}">${signals.yen_breakout_alert ? t.signal_on : t.signal_off}</span></span></div>`
  ].join("");
}

function renderSource(data) {
  const source = data.data_source || {};
  const tickers = source.tickers || {};
  document.getElementById("sourceItems").innerHTML = [
    renderDetailRow(t.primary_source, source.primary || "-"),
    renderDetailRow(t.period, source.period || "-"),
    renderDetailRow(t.tickers, Object.entries(tickers).map(([key, value]) => `${key}=${value}`).join(", "))
  ].join("");
}

document.documentElement.lang = lang;
document.getElementById("eyebrow").textContent = t.eyebrow;
document.getElementById("title").textContent = t.title;
document.getElementById("copy").textContent = t.copy;
document.getElementById("widgetLink").textContent = t.widget;
document.getElementById("apiLink").textContent = t.api;
document.getElementById("schemaLink").textContent = t.schema;
document.getElementById("homeLink").textContent = t.home;
document.getElementById("statusLabel").textContent = t.status_label;
document.getElementById("updatedLabel").textContent = t.updated;
document.getElementById("statusValue").textContent = t.loading;
document.getElementById("statusCopy").textContent = t.status_copy;
document.getElementById("pairSectionLabel").textContent = t.pairs;
document.getElementById("pairSectionTitle").textContent = t.pair_title;
document.getElementById("regimeLabel").textContent = t.regime;
document.getElementById("signalLabel").textContent = t.alerts;
document.getElementById("sourceLabel").textContent = t.source;

fetch("/exchange/api/latest.json")
  .then((response) => response.ok ? response.json() : Promise.reject(new Error("bad status")))
  .then((data) => {
    const status = data.status || "placeholder";
    const statusValue = document.getElementById("statusValue");
    statusValue.textContent = t[`status_${status}`] || status;
    statusValue.className = `overview-value ${status === "ok" ? "ok" : status === "partial" ? "partial" : status === "error" ? "error" : ""}`;
    document.getElementById("statusCopy").textContent = data.error_message || t.status_copy;
    document.getElementById("updatedValue").textContent = data.pipeline_date || "-";
    document.getElementById("asOfCopy").textContent = `${t.as_of_prefix} ${data.as_of_date || "-"}`;
    renderPairs(data);
    renderRegime(data);
    renderSignals(data);
    renderSource(data);
  })
  .catch(() => {
    const statusValue = document.getElementById("statusValue");
    statusValue.textContent = t.status_error;
    statusValue.className = "overview-value error";
    document.getElementById("statusCopy").textContent = t.fetch_error;
    document.getElementById("pairGrid").innerHTML = `<div class="detail-row"><strong>${t.fetch_error}</strong><span>-</span></div>`;
  });
