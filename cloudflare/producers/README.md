# Producers

앱별 Producer Worker는 각각 자기 앱의 데이터 생성과 R2 publish만 책임집니다.

- `breadth/`: breadth JSON 생성 및 publish
- `fear-greed/`: 공포탐욕 지표 생성 및 publish
- `exchange/`: 환율 데이터 생성 및 publish

현재 breadth는 Python 파이프라인을 계속 사용하고 있고, Cloudflare 네이티브 producer는 다음 단계에서 재구현 대상으로 둡니다.
