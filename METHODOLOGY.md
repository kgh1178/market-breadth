# Market Breadth Methodology

## 가격 데이터 산출 기준 (Price Data Basis)

**모든 가격 데이터는 주식 분할(Stock Split)은 반영하되, 배당(Dividend)은 반영하지 않은 순수 종가(Close)를 기준으로 합니다.**
이는 Barchart($S5FI) 및 S&P 공식 방법론과 동일한 스펙입니다.

종료 가격 산정을 위해 Barchart 호환 기준에 따라, 배당 지급에 따른 주가 하락은 정상적인 가격 흐름으로 간주하며 별도의 보조 조정을 가하지 않습니다. 

## 브레드스(Breadth) 산출 방식

- 위 기준에 따라, MA 윈도우 미달 종목(결측값 등)을 분모(n_valid)에서 제외하고 정상 산출 가능한 활성 종목만을 활용하여 백분율로 계산합니다.
- 계산식: `(count_above / n_valid) * 100`

## 신뢰 구간 및 정규화
- DEFF (Design Effect) 및 ICC (Intraclass Correlation)를 통한 군집 표본 오차 보정 Wilson 신뢰 구간을 산출합니다.
- 시계열 Logit-Z 점수를 통해 상호 비교 가능한 백분위 및 지표 값으로 정규화합니다.

## 2. 가격 기준 (Price Basis) — 2026-03 개정

### 2.1 원칙

본 시스템은 **split-adjusted, dividend-unadjusted** 종가(Close)를 사용하여
이동평균(SMA)과 breadth를 산출합니다.

| 항목 | 사용 가격 | 비고 |
|---|---|---|
| SMA(50), SMA(200) | Close (split-only) | Barchart S5FI 호환 |
| breadth 비교 | Close vs SMA(Close) | 동일 기준 |
| 사용하지 않는 열 | Adj Close | 배당 조정 포함 → 편향 유발 |

### 2.2 근거

Barchart는 $S5FI/$S5TH 산출 시 다음을 명시합니다:

> "Calculations are adjusted for stock splits but not dividend distributions."

배당 조정(dividend-adjusted) 가격으로 SMA를 계산하면,
배당락일 이전의 모든 과거 가격이 배당액만큼 하향 수정됩니다.
이로 인해 SMA가 실제보다 낮아지고, `Close > SMA` 비교에서
breadth가 **체계적으로 과대 추정**됩니다.

S&P 500의 평균 배당수익률 약 1.3%를 고려하면,
50일 SMA에서 약 **3-8pp의 과대 편향**이 발생합니다.
이 편향은 고배당주 비율이 높은 시기에 더욱 심화됩니다.

### 2.3 구현

```python
# yfinance
yf.download(tickers, auto_adjust=False)  # Close = split-only
# breadth_engine.py
close = prices_df["Close"]               # <- 이 열만 사용
```

### 2.4 검증 기준

| 지표 | 목표 | 비교 대상 |
|---|---|---|
| 일별 오차 | <= +-3 pp | Barchart $S5FI |
| Pearson r | >= 0.97 | 6개월 시계열 |
| RMSE | <= 3 pp | 6개월 시계열 |
| 체계적 편향 | <= +-1 pp | 평균 차이 |
