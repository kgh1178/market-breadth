const I18N = {
  en: {
    eyebrow: "Cross-Market Risk",
    title: "Market Fear Index Dashboard",
    copy: "Track fear conditions across the US, Korea, Japan, and crypto with structured per-market status metadata and comparable detail panels.",
    widget: "Widget",
    api: "API Metadata",
    schema: "API Schema",
    home: "App Hub",
    loading: "Loading…",
    status_ok: "Healthy",
    status_partial: "Partial",
    status_error: "Unavailable",
    status_copy: "Fetching `/fear-greed/api/latest.json`.",
    fetch_error: "Could not load Market Fear Index data.",
    status_label: "Status",
    updated: "Pipeline date",
    as_of_prefix: "As of",
    overview_label: "Markets",
    overview_title: "Fear snapshots by market",
    us: "United States",
    kr: "Korea",
    jp: "Japan",
    crypto: "Crypto",
    score_extreme_fear: "Extreme fear",
    score_fear: "Fear",
    score_neutral: "Neutral",
    score_greed: "Greed",
    score_extreme_greed: "Extreme greed",
    momentum: "Momentum",
    volatility: "Volatility",
    credit: "Credit",
    breadth: "Breadth",
    safe_haven_flow: "Safe-haven flow",
    fx_stress: "FX stress",
    relative_strength: "Relative strength",
    contrarian_bias: "Contrarian bias",
    turning_point_alert: "Turning-point alert",
    risk_on: "Risk-on",
    neutral: "Neutral",
    risk_off: "Risk-off",
    signal_on: "Active",
    signal_off: "Inactive",
    components: "Components",
    signals: "Signals",
    meta: "Status",
    z_score: "Z-score",
    as_of: "As of",
    error: "Error"
  },
  ko: {
    eyebrow: "크로스마켓 리스크",
    title: "시장별 공포지수 대시보드",
    copy: "미국, 한국, 일본, 크립토 시장의 공포 상태를 구조화된 시장 메타데이터 기준으로 비교하는 대시보드입니다.",
    widget: "위젯",
    api: "API 메타데이터",
    schema: "API 스키마",
    home: "앱 허브",
    loading: "불러오는 중…",
    status_ok: "정상",
    status_partial: "부분",
    status_error: "사용 불가",
    status_copy: "`/fear-greed/api/latest.json`을 불러오는 중입니다.",
    fetch_error: "시장별 공포지수 데이터를 불러오지 못했습니다.",
    status_label: "상태",
    updated: "파이프라인 날짜",
    as_of_prefix: "기준일",
    overview_label: "시장",
    overview_title: "시장별 공포 스냅샷",
    us: "미국",
    kr: "한국",
    jp: "일본",
    crypto: "크립토",
    score_extreme_fear: "극단적 공포",
    score_fear: "공포",
    score_neutral: "중립",
    score_greed: "탐욕",
    score_extreme_greed: "극단적 탐욕",
    momentum: "모멘텀",
    volatility: "변동성",
    credit: "크레딧",
    breadth: "브레드스",
    safe_haven_flow: "안전자산 선호",
    fx_stress: "환율 스트레스",
    relative_strength: "상대강도",
    contrarian_bias: "역발상 바이어스",
    turning_point_alert: "전환점 알림",
    risk_on: "리스크 온",
    neutral: "중립",
    risk_off: "리스크 오프",
    signal_on: "활성",
    signal_off: "비활성",
    components: "컴포넌트",
    signals: "시그널",
    meta: "상태",
    z_score: "Z점수",
    as_of: "기준일",
    error: "오류"
  },
  ja: {
    eyebrow: "クロスマーケットリスク",
    title: "市場別恐怖指数ダッシュボード",
    copy: "米国、韓国、日本、暗号資産市場の恐怖状態を、構造化された市場メタデータ基準で比較するダッシュボードです。",
    widget: "ウィジェット",
    api: "APIメタデータ",
    schema: "APIスキーマ",
    home: "アプリハブ",
    loading: "読み込み中…",
    status_ok: "正常",
    status_partial: "部分",
    status_error: "利用不可",
    status_copy: "`/fear-greed/api/latest.json` を読み込み中です。",
    fetch_error: "市場別恐怖指数データを読み込めませんでした。",
    status_label: "状態",
    updated: "パイプライン日付",
    as_of_prefix: "基準日",
    overview_label: "市場",
    overview_title: "市場別恐怖スナップショット",
    us: "米国",
    kr: "韓国",
    jp: "日本",
    crypto: "暗号資産",
    score_extreme_fear: "極端な恐怖",
    score_fear: "恐怖",
    score_neutral: "中立",
    score_greed: "貪欲",
    score_extreme_greed: "極端な貪欲",
    momentum: "モメンタム",
    volatility: "ボラティリティ",
    credit: "クレジット",
    breadth: "ブレッドス",
    safe_haven_flow: "安全資産選好",
    fx_stress: "為替ストレス",
    relative_strength: "相対強度",
    contrarian_bias: "逆張りバイアス",
    turning_point_alert: "転換点アラート",
    risk_on: "リスクオン",
    neutral: "中立",
    risk_off: "リスクオフ",
    signal_on: "有効",
    signal_off: "無効",
    components: "コンポーネント",
    signals: "シグナル",
    meta: "状態",
    z_score: "Zスコア",
    as_of: "基準日",
    error: "エラー"
  }
};

const MARKET_META = {
  us: { accent: "#0f766e", tint: "rgba(15,118,110,.12)", chip: "US" },
  kr: { accent: "#ef4444", tint: "rgba(239,68,68,.12)", chip: "KR" },
  jp: { accent: "#2563eb", tint: "rgba(37,99,235,.12)", chip: "JP" },
  crypto: { accent: "#c68000", tint: "rgba(198,128,0,.14)", chip: "CR" }
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

function statusText(status) {
  return t[`status_${status}`] || status || "-";
}

function labelText(label) {
  return t[`score_${label}`] || label || "-";
}

function formatScore(value) {
  return value == null || Number.isNaN(value) ? "-" : `${Number(value).toFixed(2)}%`;
}

function formatZ(value) {
  if (value == null || Number.isNaN(value)) return "-";
  const sign = value > 0 ? "+" : "";
  return `${sign}${Number(value).toFixed(2)}`;
}

function badge(value, tone) {
  return `<span class="badge ${tone}">${value}</span>`;
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function detailRow(label, value) {
  return `<div class="detail-row"><strong>${label}</strong><span>${value}</span></div>`;
}

function componentRows(components) {
  return Object.entries(components || {}).map(([key, value]) => detailRow(t[key] || key, formatScore(value))).join("");
}

function signalRows(signals) {
  const bias = t[signals?.contrarian_bias] || signals?.contrarian_bias || "-";
  const biasTone = signals?.contrarian_bias === "neutral" ? "good" : "warn";
  return [
    detailRow(t.contrarian_bias, badge(bias, biasTone)),
    detailRow(
      t.turning_point_alert,
      badge(signals?.turning_point_alert ? t.signal_on : t.signal_off, signals?.turning_point_alert ? "alert" : "good")
    )
  ].join("");
}

function metaRows(market) {
  return [
    detailRow(t.as_of, market.as_of_date || "-"),
    detailRow(t.z_score, formatZ(market.score?.z_score)),
    detailRow(t.error, market.error_message || "-")
  ].join("");
}

function renderOverview(markets) {
  document.getElementById("overviewGrid").innerHTML = ["us", "kr", "jp", "crypto"].map((marketId) => {
    const market = markets[marketId] || {};
    return `
      <article class="mini-card" style="--accent:${MARKET_META[marketId].accent};--accent-soft:${MARKET_META[marketId].tint}">
        <div class="mini-chip">${MARKET_META[marketId].chip}</div>
        <div class="mini-title">${t[marketId]}</div>
        <div class="mini-score">${formatScore(market.score?.value)}</div>
        <div class="mini-label">${labelText(market.score?.label)}</div>
        <div class="mini-meta">${statusText(market.status)} · ${market.as_of_date || "-"}</div>
      </article>
    `;
  }).join("");
}

function renderDetails(markets) {
  document.getElementById("detailGrid").innerHTML = ["us", "kr", "jp", "crypto"].map((marketId) => {
    const market = markets[marketId] || {};
    const okay = market.status === "ok" || market.status === "partial";
    return `
      <article class="detail-card" id="${marketId}" style="--accent:${MARKET_META[marketId].accent};--accent-soft:${MARKET_META[marketId].tint}">
        <span class="section-kicker">${t[marketId]}</span>
        <div class="detail-title-row">
          <div>
            <div class="detail-chip">${MARKET_META[marketId].chip}</div>
            <div class="detail-title">${t[marketId]}</div>
          </div>
          <span class="detail-status ${market.status || "error"}">${statusText(market.status)}</span>
        </div>
        <div class="detail-score">${formatScore(market.score?.value)}</div>
        <div class="detail-score-label">${labelText(market.score?.label)}</div>
        <div class="detail-z">${t.z_score}: ${formatZ(market.score?.z_score)}</div>
        ${okay ? `
          <div class="detail-columns">
            <section class="detail-block">
              <span class="section-kicker">${t.components}</span>
              <div class="detail-list">${componentRows(market.components)}</div>
            </section>
            <section class="detail-block">
              <span class="section-kicker">${t.signals}</span>
              <div class="detail-list">${signalRows(market.signals)}</div>
            </section>
            <section class="detail-block">
              <span class="section-kicker">${t.meta}</span>
              <div class="detail-list">${metaRows(market)}</div>
            </section>
          </div>
        ` : `<p class="error-copy">${market.error_message || statusText(market.status)}</p>`}
      </article>
    `;
  }).join("");
}

document.documentElement.lang = lang;
setText("eyebrow", t.eyebrow);
setText("title", t.title);
setText("copy", t.copy);
setText("widgetLink", t.widget);
setText("apiLink", t.api);
setText("schemaLink", t.schema);
setText("homeLink", t.home);
setText("statusLabel", t.status_label);
setText("updatedLabel", t.updated);
setText("statusValue", t.loading);
setText("statusCopy", t.status_copy);
setText("overviewLabel", t.overview_label);
setText("overviewTitle", t.overview_title);

fetch("/fear-greed/api/latest.json")
  .then((response) => response.ok ? response.json() : Promise.reject(new Error("bad status")))
  .then((data) => {
    const status = data.status || "error";
    const statusValue = document.getElementById("statusValue");
    statusValue.textContent = statusText(status);
    statusValue.className = `overview-value ${status}`;
    setText("statusCopy", data.error_message || t.status_copy);
    setText("updatedValue", data.pipeline_date || "-");
    setText("asOfCopy", `${t.as_of_prefix} ${data.as_of_date || "-"}`);
    renderOverview(data.markets || {});
    renderDetails(data.markets || {});
  })
  .catch(() => {
    const statusValue = document.getElementById("statusValue");
    statusValue.textContent = t.status_error;
    statusValue.className = "overview-value error";
    setText("statusCopy", t.fetch_error);
    setText("updatedValue", "-");
    setText("asOfCopy", `${t.as_of_prefix} -`);
    document.getElementById("overviewGrid").innerHTML = "";
    document.getElementById("detailGrid").innerHTML = "";
  });
