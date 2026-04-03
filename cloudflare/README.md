# Cloudflare Multi-App Deployment

이 디렉터리는 `api.jstockinsight.kr`를 앱 허브로 운영하기 위한 Cloudflare 스캐폴딩입니다.

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

## 다음 문서

- [DEPLOYMENT.md](/Users/dean/Dev/#Git/market-breadth/cloudflare/DEPLOYMENT.md)
  - Pages / Worker / R2 실제 배포 순서
  - cutover 체크리스트
  - rollback 절차
