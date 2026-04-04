const I18N = {
  en: {
    eyebrow: "Risk Pulse",
    title: "Fear & Greed Dashboard",
    copy: "A structured risk dashboard that blends momentum, volatility, credit, breadth, and safe-haven flow into a single Fear & Greed score.",
    widget: "Widget",
    api: "API Metadata",
    schema: "API Schema",
    home: "App Hub",
    loading: "Loading…",
    status_ok: "Healthy",
    status_partial: "Partial",
    status_error: "Unavailable",
    status_placeholder: "Placeholder",
    status_copy: "Fetching `/fear-greed/api/latest.json`.",
    fetch_error: "Could not load Fear & Greed API data.",
    status_label: "Status",
    updated: "Pipeline date",
    as_of_prefix: "As of",
    score_section_label: "Composite score",
    score_section_title: "Fear & Greed score",
    inputs: "Inputs",
    signals: "Signals",
    source: "Data source",
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
    contrarian_bias: "Contrarian bias",
    turning_point_alert: "Turning-point alert",
    risk_on: "Risk-on",
    neutral: "Neutral",
    risk_off: "Risk-off",
    signal_on: "Active",
    signal_off: "Inactive",
    primary_source: "Primary source",
    period: "Lookback",
    breadth_snapshot: "Breadth snapshot"
  },
  ko: {
    eyebrow: "리스크 펄스",
    title: "공포·탐욕 대시보드",
    copy: "모멘텀, 변동성, 크레딧, 브레드스, 안전자산 선호를 하나의 공포·탐욕 점수로 묶어 보여주는 구조화 리스크 대시보드입니다.",
    widget: "위젯",
    api: "API 메타데이터",
    schema: "API 스키마",
    home: "앱 허브",
    loading: "불러오는 중…",
    status_ok: "정상",
    status_partial: "부분",
    status_error: "사용 불가",
    status_placeholder: "플레이스홀더",
    status_copy: "`/fear-greed/api/latest.json`을 불러오는 중입니다.",
    fetch_error: "공포·탐욕 API 데이터를 불러오지 못했습니다.",
    status_label: "상태",
    updated: "파이프라인 날짜",
    as_of_prefix: "기준일",
    score_section_label: "종합 점수",
    score_section_title: "공포·탐욕 점수",
    inputs: "입력값",
    signals: "시그널",
    source: "데이터 소스",
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
    contrarian_bias: "역발상 바이어스",
    turning_point_alert: "전환점 알림",
    risk_on: "리스크 온",
    neutral: "중립",
    risk_off: "리스크 오프",
    signal_on: "활성",
    signal_off: "비활성",
    primary_source: "기본 소스",
    period: "조회 기간",
    breadth_snapshot: "브레드스 스냅샷"
  },
  ja: {
    eyebrow: "リスクパルス",
    title: "恐怖・貪欲ダッシュボード",
    copy: "モメンタム、ボラティリティ、クレジット、ブレッドス、安全資産選好を 1 つの恐怖・貪欲スコアにまとめて表示する構造化リスクダッシュボードです。",
    widget: "ウィジェット",
    api: "APIメタデータ",
    schema: "APIスキーマ",
    home: "アプリハブ",
    loading: "読み込み中…",
    status_ok: "正常",
    status_partial: "部分",
    status_error: "利用不可",
    status_placeholder: "プレースホルダー",
    status_copy: "`/fear-greed/api/latest.json` を読み込み中です。",
    fetch_error: "恐怖・貪欲 API データを読み込めませんでした。",
    status_label: "状態",
    updated: "パイプライン日付",
    as_of_prefix: "基準日",
    score_section_label: "総合スコア",
    score_section_title: "恐怖・貪欲スコア",
    inputs: "入力値",
    signals: "シグナル",
    source: "データソース",
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
    contrarian_bias: "逆張りバイアス",
    turning_point_alert: "転換点アラート",
    risk_on: "リスクオン",
    neutral: "中立",
    risk_off: "リスクオフ",
    signal_on: "有効",
    signal_off: "無効",
    primary_source: "主要ソース",
    period: "参照期間",
    breadth_snapshot: "ブレッドススナップショット"
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

function scoreTone(value) {
  if (value == null) return "warn";
  if (value < 20) return "alert";
  if (value < 40) return "warn";
  if (value < 60) return "good";
  if (value < 80) return "warn";
  return "alert";
}

function formatScore(value) {
  return value == null || Number.isNaN(value) ? "-" : Number(value).toFixed(2);
}

function formatZ(value) {
  if (value == null || Number.isNaN(value)) return "-";
  const sign = value > 0 ? "+" : "";
  return `${sign}${Number(value).toFixed(2)}`;
}

function labelText(label) {
  return t[`score_${label}`] || label || "-";
}

function detailRow(label, value) {
  return `<div class="detail-row"><strong>${label}</strong><span>${value}</span></div>`;
}

function badge(value, tone) {
  return `<span class="badge ${tone}">${value}</span>`;
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function renderInputs(data) {
  const inputList = document.getElementById("inputList");
  const inputs = data.inputs || {};
  inputList.innerHTML = [
    detailRow(t.momentum, formatScore(inputs.momentum)),
    detailRow(t.volatility, formatScore(inputs.volatility)),
    detailRow(t.credit, formatScore(inputs.credit)),
    detailRow(t.breadth, formatScore(inputs.breadth)),
    detailRow(t.safe_haven_flow, formatScore(inputs.safe_haven_flow))
  ].join("");
}

function renderSignals(data) {
  const signals = data.signals || {};
  const bias = t[signals.contrarian_bias] || signals.contrarian_bias || "-";
  const biasTone = signals.contrarian_bias === "neutral" ? "good" : "warn";
  document.getElementById("signalList").innerHTML = [
    detailRow(t.contrarian_bias, badge(bias, biasTone)),
    detailRow(
      t.turning_point_alert,
      badge(signals.turning_point_alert ? t.signal_on : t.signal_off, signals.turning_point_alert ? "alert" : "good")
    )
  ].join("");
}

function renderSource(data) {
  const source = data.data_source || {};
  document.getElementById("sourceList").innerHTML = [
    detailRow(t.primary_source, source.primary || "-"),
    detailRow(t.period, source.period || "-"),
    detailRow(t.breadth_snapshot, source.breadth_snapshot || "-")
  ].join("");
}

function renderScore(data) {
  const score = data.score || {};
  const tone = scoreTone(score.value);
  const scoreValue = document.getElementById("scoreValue");
  scoreValue.textContent = formatScore(score.value);
  scoreValue.style.color = tone === "alert" ? "#d93025" : tone === "warn" ? "#c68000" : "#0f766e";
  const scoreState = document.getElementById("scoreState");
  scoreState.textContent = labelText(score.label);
  scoreState.style.color = scoreValue.style.color;
  setText("zValue", formatZ(score.z_score));
  document.getElementById("scoreFill").style.width = `${Math.max(0, Math.min(100, Number(score.value || 0)))}%`;
  setText("biasValue", t[data.signals?.contrarian_bias] || data.signals?.contrarian_bias || "-");
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
setText("scoreSectionLabel", t.score_section_label);
setText("scoreSectionTitle", t.score_section_title);
setText("inputsLabel", t.inputs);
setText("signalLabel", t.signals);
setText("sourceLabel", t.source);

fetch("/fear-greed/api/latest.json")
  .then((response) => response.ok ? response.json() : Promise.reject(new Error("bad status")))
  .then((data) => {
    const status = data.status || "placeholder";
    const statusValue = document.getElementById("statusValue");
    statusValue.textContent = t[`status_${status}`] || status;
    statusValue.className = `overview-value ${status === "ok" ? "ok" : status === "partial" ? "partial" : status === "error" ? "error" : ""}`;
    setText("statusCopy", data.error_message || t.status_copy);
    setText("updatedValue", data.pipeline_date || data.date || "-");
    setText("asOfCopy", `${t.as_of_prefix} ${data.as_of_date || "-"}`);
    renderScore(data);
    renderInputs(data);
    renderSignals(data);
    renderSource(data);
  })
  .catch(() => {
    const statusValue = document.getElementById("statusValue");
    statusValue.textContent = t.status_error;
    statusValue.className = "overview-value error";
    setText("statusCopy", t.fetch_error);
    setText("updatedValue", "-");
    setText("asOfCopy", `${t.as_of_prefix} -`);
    setText("scoreValue", "-");
    setText("scoreState", "-");
    setText("zValue", "-");
    setText("biasValue", "-");
    document.getElementById("scoreFill").style.width = "0%";
    document.getElementById("inputList").innerHTML = detailRow(t.inputs, t.fetch_error);
    document.getElementById("signalList").innerHTML = detailRow(t.signals, t.fetch_error);
    document.getElementById("sourceList").innerHTML = detailRow(t.source, t.fetch_error);
  });
