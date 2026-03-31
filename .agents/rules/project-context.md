## 가격 데이터 규칙 (2026-03-31 개정)

### 필수 규칙 (MUST)

1. yfinance 호출 시 반드시 `auto_adjust=False` 사용
2. breadth/SMA 계산은 `Close` 열만 사용
   (split-adjusted, dividend-unadjusted)
3. `Adj Close` 열은 breadth 계산에 절대 사용 금지
4. 분모는 `n_valid` (SMA 산출 가능한 종목 수)이며,
   `n_total`과 구분하여 JSON에 출력
5. SMA rolling에 `min_periods=window` 반드시 적용

### 금지 규칙 (MUST NOT)

- `auto_adjust=True` 사용 금지
- `Adj Close`를 SMA, breadth, 시그널 계산에 입력하는 것 금지
- SMA 분모에 데이터 부족 종목 포함 금지

### 배경

2026-03 분석에서 공식 S5FI 대비 +3~10pp 과대 추정 발견.
근본 원인: `auto_adjust=True`가 배당 조정을 포함하여
과거 SMA를 낮추고 breadth를 인플레이트함.
Barchart 공식: "adjusted for stock splits but not dividend distributions"
