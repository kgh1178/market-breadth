# Cloudflare Deployment Guide

이 문서는 `api.jstockinsight.kr`를 Cloudflare 멀티앱 허브로 실제 전환할 때 필요한 설정 순서와 cutover 체크리스트를 정리합니다.

기준 시점:
- 작성 기준일: `2026-04-01`
- 운영 목표:
  - `blog.jstockinsight.kr`: Blogger 유지
  - `api.jstockinsight.kr`: Cloudflare Pages + Worker + R2 기반 앱 허브

## 1. 목표 상태

최종 운영 구조는 아래와 같습니다.

```text
GitHub -> Cloudflare Pages
GitHub -> Cloudflare Workers

Cloudflare Pages
  /                       앱 허브 홈
  /breadth               breadth 위젯
  /breadth/dashboard     breadth 대시보드
  /fear-greed            후속 앱
  /exchange              후속 앱

Cloudflare Worker
  /breadth/api/*
  /fear-greed/api/*
  /exchange/api/*

Cloudflare R2
  breadth/latest.json
  breadth/metadata.json
  breadth/signals.json
  breadth/sp500.json
  breadth/nikkei225.json
  breadth/kospi200.json
```

중요 원칙:
- 프런트는 same-origin `/breadth/api/*`만 읽는다.
- GitHub Pages는 더 이상 운영 경로로 사용하지 않는다.
- breadth UI는 `latest.json`의 구조화 상태를 소비하고, UI에서 freshness/error를 새로 추론하지 않는다.

## 2. 리포지토리 기준 준비물

이 저장소에는 이미 다음 자산이 준비되어 있습니다.

- 정적 앱 소스
  - [apps/hub/index.html](/Users/dean/Dev/#Git/market-breadth/apps/hub/index.html)
  - [apps/breadth/widget.html](/Users/dean/Dev/#Git/market-breadth/apps/breadth/widget.html)
  - [apps/breadth/dashboard.html](/Users/dean/Dev/#Git/market-breadth/apps/breadth/dashboard.html)
- 정적 빌드 스크립트
  - [scripts/build_static_apps.py](/Users/dean/Dev/#Git/market-breadth/scripts/build_static_apps.py)
- API Worker
  - [cloudflare/api-worker/src/index.ts](/Users/dean/Dev/#Git/market-breadth/cloudflare/api-worker/src/index.ts)
  - [cloudflare/api-worker/wrangler.toml](/Users/dean/Dev/#Git/market-breadth/cloudflare/api-worker/wrangler.toml)
- Producer 스캐폴딩
  - [cloudflare/producers/breadth/wrangler.toml](/Users/dean/Dev/#Git/market-breadth/cloudflare/producers/breadth/wrangler.toml)
- 운영 스크립트
  - [cloudflare_preflight.sh](/Users/dean/Dev/#Git/market-breadth/scripts/cloudflare_preflight.sh)
  - [cloudflare_sync_r2.sh](/Users/dean/Dev/#Git/market-breadth/scripts/cloudflare_sync_r2.sh)
  - [cloudflare_deploy_workers.sh](/Users/dean/Dev/#Git/market-breadth/scripts/cloudflare_deploy_workers.sh)

## 2.1 권장 실행 순서

cutover 직전에는 아래 순서가 가장 안전합니다.

```bash
scripts/cloudflare_preflight.sh
scripts/cloudflare_sync_r2.sh --dry-run
scripts/cloudflare_sync_r2.sh
scripts/cloudflare_deploy_workers.sh api
scripts/cloudflare_deploy_workers.sh breadth
```

설명:
- `cloudflare_preflight.sh`
  - breadth JSON 재생성
  - 정적 앱 빌드
  - 테스트 실행
- `cloudflare_sync_r2.sh`
  - `docs/breadth/api/*.json`를 `jstockinsight-app-data/breadth/*`로 업로드
- `cloudflare_deploy_workers.sh`
  - API Worker와 producer를 `wrangler deploy`로 배포

## 3. Cloudflare 리소스 생성 순서

권장 순서:

1. R2 bucket 생성
2. API Worker 생성
3. Pages 프로젝트 생성
4. Custom domain 연결
5. breadth producer 연결
6. cutover

이 순서를 권장하는 이유:
- 데이터 저장소와 API를 먼저 안정화해야 프런트를 붙여도 stale/mixed 상태가 생기지 않습니다.

## 4. R2 설정

생성할 bucket:
- `jstockinsight-app-data`

초기 key 구조:
- `breadth/latest.json`
- `breadth/metadata.json`
- `breadth/signals.json`
- `breadth/sp500.json`
- `breadth/nikkei225.json`
- `breadth/kospi200.json`

초기 적재 방법:
- 현재 로컬 생성물 `docs/breadth/api/*.json`을 대응 key로 업로드

예시 매핑:
- `docs/breadth/api/latest.json` -> `breadth/latest.json`
- `docs/breadth/api/sp500.json` -> `breadth/sp500.json`

주의:
- `docs/api/*`는 legacy 경로입니다.
- 운영 적재 기준은 `docs/breadth/api/*`만 사용합니다.

## 5. API Worker 설정

현재 Worker 설정 파일:
- [cloudflare/api-worker/wrangler.toml](/Users/dean/Dev/#Git/market-breadth/cloudflare/api-worker/wrangler.toml)

핵심 값:
- Worker 이름: `jstockinsight-api`
- Route: `api.jstockinsight.kr/*`
- R2 binding: `APP_DATA`

Worker 역할:
- `/breadth/api/*`, `/fear-greed/api/*`, `/exchange/api/*` 경로를 받아 내부적으로 R2 key `{app}/{rest}`로 매핑
- 예:
  - `/breadth/api/latest.json` -> `breadth/latest.json`
  - `/fear-greed/api/latest.json` -> `fear-greed/latest.json`

응답 정책:
- `content-type: application/json; charset=utf-8`
- `cache-control: public, max-age=300`
- object 미존재 시 JSON 404

배포 전 확인:
- zone 이름이 실제 Cloudflare zone과 일치하는지
- bucket 이름이 실제 생성된 R2 bucket과 일치하는지

## 6. Pages 설정

Pages 프로젝트는 Git integration 기준으로 생성합니다.

권장 값:
- Project name: `jstockinsight-apps`
- Production branch: `master`
- Build command:
  ```bash
  python3 scripts/build_static_apps.py
  ```
- Build output directory:
  ```bash
  docs
  ```

필요 이유:
- 저장소 소스는 `apps/` 아래에 있고, 실제 정적 배포물은 `docs/`에 생성됩니다.

Pages에서 서빙되는 주요 경로:
- `/`
- `/breadth`
- `/breadth/dashboard`
- `/fear-greed`
- `/exchange`

정적 redirect:
- [docs/_redirects](/Users/dean/Dev/#Git/market-breadth/docs/_redirects)
  - `/widget.html -> /breadth`
  - `/api/* -> /breadth/api/*`

주의:
- Worker route는 Pages와 충돌하지 않도록 API 경로에만 걸려야 합니다.
- Cloudflare route 규칙상 와일드카드는 경로 끝에만 둘 수 있으므로, 앱별 API 경로를 각각 명시합니다.
- 현재 저장소 설정은 다음처럼 맞춰져 있습니다.
  - `api.jstockinsight.kr/breadth/api/*`
  - `api.jstockinsight.kr/fear-greed/api/*`
  - `api.jstockinsight.kr/exchange/api/*`

운영 원칙:
1. Pages custom domain은 `api.jstockinsight.kr`
2. Worker는 `/breadth/api/*`, `/fear-greed/api/*`, `/exchange/api/*`만 가로챔

대안:
- Worker를 Pages Functions로 흡수하는 방식도 가능하지만, 현재 저장소 스캐폴딩은 별도 Worker 방식을 전제로 합니다.

## 7. breadth Producer 설정

현재 breadth producer는 스캐폴딩 단계입니다.

- [cloudflare/producers/breadth/src/index.ts](/Users/dean/Dev/#Git/market-breadth/cloudflare/producers/breadth/src/index.ts)
- [cloudflare/producers/breadth/wrangler.toml](/Users/dean/Dev/#Git/market-breadth/cloudflare/producers/breadth/wrangler.toml)

Cron:
- `30 6 * * 1-5`
- `0 8 * * 1-5`

현재 현실적인 운영 단계:
- 1단계: Python 파이프라인으로 JSON 생성
- 2단계: 결과물을 R2에 publish
- 3단계: 이후 Cloudflare native producer로 재구현

즉 cutover 1차에서는:
- Pages + Worker + R2는 Cloudflare로 이전
- breadth 생성 로직 자체는 당장은 기존 Python 파이프라인을 유지 가능

## 8. GitHub Actions 역할

완전 이전 후 GitHub Actions의 권장 역할:
- 테스트
- 정적 검증
- 빌드 검증

제거 대상:
- 운영 JSON을 repo에 커밋하는 흐름
- GitHub Pages 운영 역할

과도기 권장:
- 먼저 Cloudflare를 붙인 뒤에도 GitHub Actions는 테스트 전용으로 남긴다.

## 9. Cutover 체크리스트

### 9.1 사전 점검

- [ ] `python3 -m pytest -q` 통과
- [ ] `python3 scripts/build_static_apps.py` 실행 후 `docs/` 구조 확인
- [ ] `docs/breadth/api/latest.json`에 `status`, `as_of_date`, `series_valid`, `metrics_valid` 존재
- [ ] `docs/_redirects` 존재
- [ ] API Worker 소스가 `/ :app /api/*` -> R2 key `{app}/{rest}` 매핑
- [ ] R2 bucket `jstockinsight-app-data` 생성

### 9.2 R2 적재

- [ ] `breadth/latest.json` 업로드
- [ ] `breadth/metadata.json` 업로드
- [ ] `breadth/signals.json` 업로드
- [ ] `breadth/sp500.json` 업로드
- [ ] `breadth/nikkei225.json` 업로드
- [ ] `breadth/kospi200.json` 업로드

### 9.3 Worker 배포

- [ ] `APP_DATA` binding 연결
- [ ] route를 API 경로 전용으로 제한
- [ ] `/breadth/api/latest.json` 응답 확인
- [ ] 없는 경로에서 JSON 404 확인

### 9.4 Pages 배포

- [ ] GitHub integration 연결
- [ ] build command = `python3 scripts/build_static_apps.py`
- [ ] output dir = `docs`
- [ ] `/`에서 앱 허브 표시 확인
- [ ] `/breadth`에서 위젯 표시 확인
- [ ] `/breadth/dashboard`에서 대시보드 표시 확인
- [ ] `/fear-greed`, `/exchange` placeholder 확인

### 9.5 실제 cutover

- [ ] `api.jstockinsight.kr` DNS를 Pages 기준으로 연결
- [ ] API Worker route 우선순위 확인
- [ ] 브라우저에서 `/breadth/api/latest.json` same-origin fetch 확인
- [ ] `?lang=ko`, `?lang=ja`, `?lang=en` 확인
- [ ] `status=error` 시장에서 stale 차트 미노출 확인

### 9.6 cutover 후 운영 확인

- [ ] Cloudflare Pages production deployment 성공
- [ ] Worker logs에서 404/500 급증 여부 확인
- [ ] R2 object 최신 timestamp 확인
- [ ] breadth 위젯과 대시보드 모두 최신 데이터 반영 확인

## 10. Rollback 절차

문제가 생기면 rollback은 다음 우선순위로 진행합니다.

1. DNS rollback
- `api.jstockinsight.kr`를 이전 호스트로 되돌리거나 temporary maintenance로 전환

2. Worker route disable
- API Worker route를 제거해 Pages 충돌을 해제

3. R2 object freeze
- producer를 멈추고 마지막 정상 object를 유지

4. GitHub fallback
- 필요 시 기존 GitHub 기반 정적 산출물을 임시 참조

주의:
- 가장 위험한 상태는 `Pages는 Cloudflare`, `API는 GitHub`, `batch는 다른 경로`로 섞이는 것입니다.
- rollback도 하나의 source of truth를 유지하는 방향으로 해야 합니다.

## 11. 운영 메모

- breadth JSON 계약은 유지해야 합니다.
  - `latest.json`:
    - `status`
    - `as_of_date`
    - `series_valid`
    - `metrics_valid`
    - `error_code`
    - `error_message`
  - `signals.json`:
    - `partial_data`
    - signal별 `valid`
    - `required_markets`
    - `missing_markets`
    - `invalid_reason`

- 이 계약은 UI가 stale/error를 추론하지 않기 위한 핵심입니다.
- 이후 Cloudflare native breadth producer를 만들 때도 이 shape를 그대로 보존해야 합니다.
