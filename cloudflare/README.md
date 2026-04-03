# Cloudflare Multi-App Deployment

이 디렉터리는 `api.jstockinsight.kr`를 앱 허브로 운영하기 위한 Cloudflare 스캐폴딩입니다.

기준 시점:
- 업데이트: `2026-04-04`

## 현재 운영 상태

- `api.jstockinsight.kr`
  - Cloudflare Pages 프로젝트 `market-breadth`에 연결됨
  - 앱 허브 홈, `/breadth`, `/breadth/dashboard`를 정적 서빙
- `jstockinsight-api`
  - Worker custom domain 없음
  - 아래 API route만 담당
    - `api.jstockinsight.kr/breadth/api/*`
    - `api.jstockinsight.kr/fear-greed/api/*`
    - `api.jstockinsight.kr/exchange/api/*`
- `breadth-producer`
  - cron 전용 producer Worker로 배포됨
  - 공개 앱 엔드포인트가 아니라 상태 확인용 `fetch()`만 제공
- `ancient-field-05d1`
  - 기본 `Hello World!` Worker였고, 현재 운영 route에는 연결되지 않음
  - 삭제 후보

## 목표 구조

- `Pages`
  - `/` -> 앱 허브 홈
  - `/breadth` -> 마켓 브레드스 위젯
  - `/breadth/dashboard` -> 마켓 브레드스 대시보드
  - `/fear-greed`, `/exchange` -> 후속 앱 placeholder
- `API Worker`
  - `/:app/api/*` -> 앱별 R2 JSON 응답
- `R2`
  - `breadth/latest.json`
  - `breadth/metadata.json`
  - `breadth/signals.json`
  - `breadth/sp500.json`
  - `breadth/nikkei225.json`
  - `breadth/kospi200.json`
  - `fear-greed/latest.json`
  - `fear-greed/metadata.json`
  - `fear-greed/schema.json`
  - `exchange/latest.json`
  - `exchange/metadata.json`
  - `exchange/schema.json`
- `Producer Workers`
  - 앱별 스케줄/산출물 생성 책임 분리

## 현재 구현 범위

- `api-worker/`
  - `/breadth/api/latest.json` 같은 경로를 R2 key `breadth/latest.json`으로 매핑
- `producers/`
  - 앱별 Worker 분리 스캐폴딩
  - breadth는 현재 Python 파이프라인이 실제 생성기를 계속 담당하고, Cloudflare producer는 후속 재구현 대상
- `scripts/`
  - `cloudflare_preflight.sh`: 생성 + 빌드 + 테스트
  - `cloudflare_sync_r2.sh`: `docs/breadth/api/*.json` -> R2 업로드
  - `cloudflare_deploy_workers.sh`: Worker / Producer `wrangler deploy`

## 운영 원칙

- GitHub: 코드와 CI의 source of truth
- Cloudflare: 운영 앱, 운영 API, 운영 스케줄의 source of truth
- breadth 프런트는 구조화된 `latest.json` 메타데이터만 소비하고, UI에서 freshness/error를 추론하지 않음
- Pages는 앱 페이지를 담당하고, Worker는 `/api/*` 경로만 담당한다

## 다음 문서

- [DEPLOYMENT.md](/Users/dean/Dev/#Git/market-breadth/cloudflare/DEPLOYMENT.md)
  - Pages / Worker / R2 실제 배포 순서
  - cutover 체크리스트
  - rollback 절차
