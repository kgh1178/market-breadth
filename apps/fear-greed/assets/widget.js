const I18N = {
  en: {
    eyebrow: "Risk Snapshot",
    title: "Market Fear Index",
    copy: "Compare fear conditions across the US, Korea, Japan, and crypto in one compact widget.",
    updated: "Updated",
    loading: "Loading…",
    status_ok: "Healthy",
    status_partial: "Partial",
    status_error: "Unavailable",
    status_copy: "Fetching `/fear-greed/api/latest.json`.",
    fetch_error: "Could not load Market Fear Index data.",
    dashboard: "Full Dashboard",
    us: "United States",
    kr: "Korea",
    jp: "Japan",
    crypto: "Crypto",
    as_of: "As of",
    score_extreme_fear: "Extreme fear",
    score_fear: "Fear",
    score_neutral: "Neutral",
    score_greed: "Greed",
    score_extreme_greed: "Extreme greed"
  },
  ko: {
    eyebrow: "리스크 스냅샷",
    title: "시장별 공포지수",
    copy: "미국, 한국, 일본, 크립토 시장의 공포 상태를 한 화면에서 비교하는 compact 위젯입니다.",
    updated: "업데이트",
    loading: "불러오는 중…",
    status_ok: "정상",
    status_partial: "부분",
    status_error: "사용 불가",
    status_copy: "`/fear-greed/api/latest.json`을 불러오는 중입니다.",
    fetch_error: "시장별 공포지수 데이터를 불러오지 못했습니다.",
    dashboard: "전체 대시보드",
    us: "미국",
    kr: "한국",
    jp: "일본",
    crypto: "크립토",
    as_of: "기준일",
    score_extreme_fear: "극단적 공포",
    score_fear: "공포",
    score_neutral: "중립",
    score_greed: "탐욕",
    score_extreme_greed: "극단적 탐욕"
  },
  ja: {
    eyebrow: "リスクスナップショット",
    title: "市場別恐怖指数",
    copy: "米国、韓国、日本、暗号資産市場の恐怖状態を 1 画面で比較する compact ウィジェットです。",
    updated: "更新",
    loading: "読み込み中…",
    status_ok: "正常",
    status_partial: "部分",
    status_error: "利用不可",
    status_copy: "`/fear-greed/api/latest.json` を読み込み中です。",
    fetch_error: "市場別恐怖指数データを読み込めませんでした。",
    dashboard: "全体ダッシュボード",
    us: "米国",
    kr: "韓国",
    jp: "日本",
    crypto: "暗号資産",
    as_of: "基準日",
    score_extreme_fear: "極端な恐怖",
    score_fear: "恐怖",
    score_neutral: "中立",
    score_greed: "貪欲",
    score_extreme_greed: "極端な貪欲"
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

function labelText(label) {
  return t[`score_${label}`] || label || "-";
}

function formatScore(value) {
  return value == null || Number.isNaN(value) ? "-" : `${Number(value).toFixed(2)}%`;
}

function statusText(status) {
  return t[`status_${status}`] || status || "-";
}

function renderMarketCards(data) {
  const grid = document.getElementById("marketGrid");
  const markets = data.markets || {};
  grid.innerHTML = ["us", "kr", "jp", "crypto"].map((marketId) => {
    const market = markets[marketId] || {};
    const score = market.score || {};
    return `
      <a class="market-card" style="--accent:${MARKET_META[marketId].accent};--accent-soft:${MARKET_META[marketId].tint}" href="/fear-greed/dashboard#${marketId}">
        <div class="market-head">
          <div>
            <div class="market-chip">${MARKET_META[marketId].chip}</div>
            <div class="market-name">${t[marketId]}</div>
          </div>
          <span class="market-status ${market.status || "error"}">${statusText(market.status)}</span>
        </div>
        <div class="market-score">${formatScore(score.value)}</div>
        <div class="market-label">${labelText(score.label)}</div>
        <div class="market-meta">
          <span>${t.as_of}</span>
          <strong>${market.as_of_date || "-"}</strong>
        </div>
      </a>
    `;
  }).join("");
}

document.documentElement.lang = lang;
document.getElementById("eyebrow").textContent = t.eyebrow;
document.getElementById("title").textContent = t.title;
document.getElementById("copy").textContent = t.copy;
document.getElementById("updatedLabel").textContent = t.updated;
document.getElementById("statusPill").textContent = t.loading;
document.getElementById("statusCopy").textContent = t.status_copy;
document.getElementById("dashboardLink").textContent = t.dashboard;

fetch("/fear-greed/api/latest.json")
  .then((response) => response.ok ? response.json() : Promise.reject(new Error("bad status")))
  .then((data) => {
    const status = data.status || "error";
    const statusPill = document.getElementById("statusPill");
    statusPill.className = `status-pill ${status}`;
    statusPill.textContent = statusText(status);
    document.getElementById("statusCopy").textContent = data.error_message || t.status_copy;
    document.getElementById("updatedValue").textContent = data.pipeline_date || "-";
    renderMarketCards(data);
  })
  .catch(() => {
    const statusPill = document.getElementById("statusPill");
    statusPill.className = "status-pill error";
    statusPill.textContent = t.status_error;
    document.getElementById("statusCopy").textContent = t.fetch_error;
    document.getElementById("marketGrid").innerHTML = "";
  });
