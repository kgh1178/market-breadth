const I18N = {
  en: {
    eyebrow: "Cross-Market FX",
    title: "Exchange Monitor",
    copy: "Live FX snapshot for core USD and Asia pairs, driven by structured status metadata instead of client-side guesses.",
    dashboard: "Dashboard",
    api: "Latest API",
    schema: "API Schema",
    home: "App Hub",
    updated: "Updated",
    loading: "Loading…",
    status_ok: "Healthy",
    status_partial: "Partial",
    status_error: "Unavailable",
    status_placeholder: "Placeholder",
    status_copy: "Fetching `/exchange/api/latest.json`.",
    fetch_error: "Could not load exchange API data.",
    regime: "Regime",
    alerts: "Alerts",
    source: "Source",
    as_of: "As of",
    coverage: "Pair coverage",
    pair_coverage: "{ready}/{total} pairs ready",
    daily_change: "Daily change",
    z_score: "20d z-score",
    usd_strength: "USD strength",
    asia_fx_pressure: "Asia FX pressure",
    krw_risk_alert: "KRW risk alert",
    yen_breakout_alert: "Yen breakout alert",
    signal_on: "Active",
    signal_off: "Inactive",
    no_pairs: "No valid pair metrics are available yet."
  },
  ko: {
    eyebrow: "크로스마켓 FX",
    title: "환율 모니터",
    copy: "핵심 달러 및 아시아 통화쌍을 구조화된 상태 메타데이터 기준으로 보여주는 실시간 FX 스냅샷입니다.",
    dashboard: "대시보드",
    api: "최신 API",
    schema: "API 스키마",
    home: "앱 허브",
    updated: "업데이트",
    loading: "불러오는 중…",
    status_ok: "정상",
    status_partial: "부분",
    status_error: "사용 불가",
    status_placeholder: "플레이스홀더",
    status_copy: "`/exchange/api/latest.json`을 불러오는 중입니다.",
    fetch_error: "환율 API 데이터를 불러오지 못했습니다.",
    regime: "레짐",
    alerts: "알림",
    source: "소스",
    as_of: "기준일",
    coverage: "커버리지",
    pair_coverage: "{ready}/{total} 통화쌍 준비됨",
    daily_change: "일간 변화",
    z_score: "20일 Z점수",
    usd_strength: "달러 강도",
    asia_fx_pressure: "아시아 FX 압력",
    krw_risk_alert: "원화 리스크 알림",
    yen_breakout_alert: "엔화 돌파 알림",
    signal_on: "활성",
    signal_off: "비활성",
    no_pairs: "표시할 유효 환율 데이터가 아직 없습니다."
  },
  ja: {
    eyebrow: "クロスマーケット FX",
    title: "為替モニター",
    copy: "主要ドル系・アジア通貨ペアを、クライアント側の推測ではなく構造化ステータスメタデータで表示する FX スナップショットです。",
    dashboard: "ダッシュボード",
    api: "最新API",
    schema: "APIスキーマ",
    home: "アプリハブ",
    updated: "更新",
    loading: "読み込み中…",
    status_ok: "正常",
    status_partial: "部分",
    status_error: "利用不可",
    status_placeholder: "プレースホルダー",
    status_copy: "`/exchange/api/latest.json` を読み込み中です。",
    fetch_error: "為替APIデータを読み込めませんでした。",
    regime: "レジーム",
    alerts: "アラート",
    source: "ソース",
    as_of: "基準日",
    coverage: "カバレッジ",
    pair_coverage: "{ready}/{total} ペア準備完了",
    daily_change: "日次変化",
    z_score: "20日 Zスコア",
    usd_strength: "ドル強度",
    asia_fx_pressure: "アジア FX 圧力",
    krw_risk_alert: "ウォンリスク警報",
    yen_breakout_alert: "円ブレイクアウト警報",
    signal_on: "有効",
    signal_off: "無効",
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

function formatPairValue(pairKey, value) {
  if (value == null || Number.isNaN(value)) return "-";
  return Number(value).toFixed(PAIR_META[pairKey]?.digits ?? 2);
}

function severityClass(value) {
  if (value > 0) return "pos";
  if (value < 0) return "neg";
  return "flat";
}

function chipTone(value) {
  if (value === "strong" || value === "high") return "alert";
  if (value === "medium" || value === "neutral") return "warn";
  return "good";
}

function renderPairs(data) {
  const pairGrid = document.getElementById("pairGrid");
  const entries = Object.entries(data.pairs || {}).filter(([, pair]) => pair && pair.value != null);

  if (!entries.length) {
    pairGrid.innerHTML = `<div class="empty">${t.no_pairs}</div>`;
  } else {
    pairGrid.innerHTML = entries.map(([key, pair]) => `
      <article class="pair-card" style="--accent:${PAIR_META[key]?.accent || "#2563eb"}">
        <div class="pair-symbol">${key}</div>
        <div class="pair-label">${PAIR_META[key]?.label || key}</div>
        <div class="pair-value">${formatPairValue(key, pair.value)}</div>
        <div class="pair-meta">
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

  document.getElementById("coverageValue").textContent = interpolate(t.pair_coverage, {
    ready: entries.length,
    total: Object.keys(PAIR_META).length
  });
}

function renderRegime(data) {
  const regime = data.regime || {};
  document.getElementById("regimeItems").innerHTML = [
    [t.usd_strength, regime.usd_strength || "-"],
    [t.asia_fx_pressure, regime.asia_fx_pressure || "-"]
  ].map(([label, value]) => `
    <div class="chip ${chipTone(value)}">
      <strong>${label}</strong>
      <span>${value}</span>
    </div>
  `).join("");
}

function renderSignals(data) {
  const signals = data.signals || {};
  document.getElementById("signalItems").innerHTML = [
    [t.krw_risk_alert, !!signals.krw_risk_alert],
    [t.yen_breakout_alert, !!signals.yen_breakout_alert]
  ].map(([label, active]) => `
    <div class="chip ${active ? "alert" : "good"}">
      <strong>${label}</strong>
      <span>${active ? t.signal_on : t.signal_off}</span>
    </div>
  `).join("");
}

function setStatus(data) {
  const status = data.status || "placeholder";
  const pill = document.getElementById("statusPill");
  pill.className = `status-pill ${status}`;
  pill.textContent = t[`status_${status}`] || status;
  document.getElementById("statusCopy").textContent = data.error_message || t.status_copy;
  document.getElementById("updatedValue").textContent = data.pipeline_date || data.date || "-";
  document.getElementById("sourceValue").textContent = data.data_source?.primary || "-";
  document.getElementById("asOfValue").textContent = data.as_of_date || "-";
}

document.documentElement.lang = lang;
document.getElementById("eyebrow").textContent = t.eyebrow;
document.getElementById("title").textContent = t.title;
document.getElementById("copy").textContent = t.copy;
document.getElementById("dashboardLink").textContent = t.dashboard;
document.getElementById("apiLink").textContent = t.api;
document.getElementById("schemaLink").textContent = t.schema;
document.getElementById("homeLink").textContent = t.home;
document.getElementById("updatedLabel").textContent = t.updated;
document.getElementById("regimeLabel").textContent = t.regime;
document.getElementById("signalLabel").textContent = t.alerts;
document.getElementById("sourceLabel").textContent = t.source;
document.getElementById("basisLabel").textContent = t.as_of;
document.getElementById("coverageLabel").textContent = t.coverage;
document.getElementById("statusPill").textContent = t.loading;
document.getElementById("statusCopy").textContent = t.status_copy;

fetch("/exchange/api/latest.json")
  .then((response) => response.ok ? response.json() : Promise.reject(new Error("bad status")))
  .then((data) => {
    setStatus(data);
    renderPairs(data);
    renderRegime(data);
    renderSignals(data);
  })
  .catch(() => {
    const pill = document.getElementById("statusPill");
    pill.className = "status-pill error";
    pill.textContent = t.status_error;
    document.getElementById("statusCopy").textContent = t.fetch_error;
    document.getElementById("pairGrid").innerHTML = `<div class="empty">${t.fetch_error}</div>`;
  });
