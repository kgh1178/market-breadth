const I18N = {
  en: {
    eyebrow: "Risk Pulse",
    title: "Fear & Greed Monitor",
    copy: "A compact risk pulse that turns structured market inputs into a single Fear & Greed score without client-side heuristics.",
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
    status_copy: "Fetching `/fear-greed/api/latest.json`.",
    fetch_error: "Could not load Fear & Greed API data.",
    score: "Score",
    z_score: "Z-score",
    inputs: "Inputs",
    signals: "Signals",
    source: "Source",
    as_of: "As of",
    bias: "Bias",
    momentum: "Momentum",
    volatility: "Volatility",
    credit: "Credit",
    breadth: "Breadth",
    safe_haven_flow: "Safe-haven flow",
    contrarian_bias: "Contrarian bias",
    turning_point_alert: "Turning-point alert",
    risk_on: "Risk-on",
    neutral: "Neutral",
    risk_off: "Risk-off",
    signal_on: "Active",
    signal_off: "Inactive",
    score_extreme_fear: "Extreme fear",
    score_fear: "Fear",
    score_neutral: "Neutral",
    score_greed: "Greed",
    score_extreme_greed: "Extreme greed"
  },
  ko: {
    eyebrow: "리스크 펄스",
    title: "공포·탐욕 모니터",
    copy: "구조화된 입력값을 바탕으로 클라이언트 추론 없이 하나의 공포·탐욕 점수로 압축한 리스크 펄스입니다.",
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
    status_copy: "`/fear-greed/api/latest.json`을 불러오는 중입니다.",
    fetch_error: "공포·탐욕 API 데이터를 불러오지 못했습니다.",
    score: "점수",
    z_score: "Z점수",
    inputs: "입력값",
    signals: "시그널",
    source: "소스",
    as_of: "기준일",
    bias: "바이어스",
    momentum: "모멘텀",
    volatility: "변동성",
    credit: "크레딧",
    breadth: "브레드스",
    safe_haven_flow: "안전자산 선호",
    contrarian_bias: "역발상 바이어스",
    turning_point_alert: "전환점 알림",
    risk_on: "리스크 온",
    neutral: "중립",
    risk_off: "리스크 오프",
    signal_on: "활성",
    signal_off: "비활성",
    score_extreme_fear: "극단적 공포",
    score_fear: "공포",
    score_neutral: "중립",
    score_greed: "탐욕",
    score_extreme_greed: "극단적 탐욕"
  },
  ja: {
    eyebrow: "リスクパルス",
    title: "恐怖・貪欲モニター",
    copy: "構造化された入力値から、クライアント側の推測なしに 1 つの恐怖・貪欲スコアへ圧縮したリスクパルスです。",
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
    status_copy: "`/fear-greed/api/latest.json` を読み込み中です。",
    fetch_error: "恐怖・貪欲 API データを読み込めませんでした。",
    score: "スコア",
    z_score: "Zスコア",
    inputs: "入力値",
    signals: "シグナル",
    source: "ソース",
    as_of: "基準日",
    bias: "バイアス",
    momentum: "モメンタム",
    volatility: "ボラティリティ",
    credit: "クレジット",
    breadth: "ブレッドス",
    safe_haven_flow: "安全資産選好",
    contrarian_bias: "逆張りバイアス",
    turning_point_alert: "転換点アラート",
    risk_on: "リスクオン",
    neutral: "中立",
    risk_off: "リスクオフ",
    signal_on: "有効",
    signal_off: "無効",
    score_extreme_fear: "極端な恐怖",
    score_fear: "恐怖",
    score_neutral: "中立",
    score_greed: "貪欲",
    score_extreme_greed: "極端な貪欲"
  }
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

function percentWidth(value) {
  if (value == null || Number.isNaN(value)) return "0%";
  return `${Math.max(0, Math.min(100, Number(value)))}%`;
}

function scoreTone(value) {
  if (value == null) return "warn";
  if (value < 20) return "alert";
  if (value < 40) return "warn";
  if (value < 60) return "warn";
  return "good";
}

function labelText(key) {
  return t[`score_${key}`] || key || "-";
}

function formatScore(value) {
  return value == null ? "-" : Number(value).toFixed(2);
}

function formatZ(value) {
  if (value == null || Number.isNaN(value)) return "-";
  const sign = value > 0 ? "+" : "";
  return `${sign}${Number(value).toFixed(2)}`;
}

function renderInputs(data) {
  const entries = Object.entries(data.inputs || {});
  document.getElementById("inputGrid").innerHTML = entries.map(([key, value]) => `
    <div class="metric">
      <div class="metric-name">${t[key] || key}</div>
      <span class="metric-value">${formatScore(value)}</span>
    </div>
  `).join("");
}

function renderSignals(data) {
  const signals = data.signals || {};
  document.getElementById("signalList").innerHTML = [
    [t.contrarian_bias, t[signals.contrarian_bias] || signals.contrarian_bias || "-"],
    [t.turning_point_alert, signals.turning_point_alert ? t.signal_on : t.signal_off]
  ].map(([label, value]) => `
    <div class="signal-chip">
      <strong>${label}</strong>
      <span class="badge ${value === t.signal_on ? "alert" : value === t.risk_on || value === t.risk_off ? "warn" : "good"}">${value}</span>
    </div>
  `).join("");
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
document.getElementById("inputsLabel").textContent = t.inputs;
document.getElementById("signalLabel").textContent = t.signals;
document.getElementById("sourceLabel").textContent = t.source;
document.getElementById("asOfLabel").textContent = t.as_of;
document.getElementById("biasLabel").textContent = t.bias;
document.getElementById("scoreLabel").textContent = t.score;
document.getElementById("zLabel").textContent = t.z_score;
document.getElementById("statusPill").textContent = t.loading;
document.getElementById("statusCopy").textContent = t.status_copy;

fetch("/fear-greed/api/latest.json")
  .then((response) => response.ok ? response.json() : Promise.reject(new Error("bad status")))
  .then((data) => {
    const status = data.status || "placeholder";
    const score = data.score || {};
    const statusPill = document.getElementById("statusPill");
    statusPill.className = `status-pill ${status}`;
    statusPill.textContent = t[`status_${status}`] || status;
    document.getElementById("statusCopy").textContent = data.error_message || t.status_copy;
    document.getElementById("updatedValue").textContent = data.pipeline_date || "-";
    document.getElementById("scoreValue").textContent = formatScore(score.value);
    document.getElementById("scoreState").textContent = labelText(score.label);
    document.getElementById("zValue").textContent = formatZ(score.z_score);
    document.getElementById("scoreState").className = `score-state ${scoreTone(score.value)}`;
    document.getElementById("scoreFill").style.width = percentWidth(score.value);
    document.getElementById("sourceValue").textContent = data.data_source?.primary || "-";
    document.getElementById("asOfValue").textContent = data.as_of_date || "-";
    document.getElementById("biasValue").textContent = t[data.signals?.contrarian_bias] || data.signals?.contrarian_bias || "-";
    renderInputs(data);
    renderSignals(data);
  })
  .catch(() => {
    const statusPill = document.getElementById("statusPill");
    statusPill.className = "status-pill error";
    statusPill.textContent = t.status_error;
    document.getElementById("statusCopy").textContent = t.fetch_error;
  });
