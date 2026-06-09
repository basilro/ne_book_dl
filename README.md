# naver_series_mobile

리눅스 위 안드로이드 네이버 시리즈 앱을 헤드리스 구동해, 앱이 복호화한
회차 본문 평문을 Frida 후킹(폴백: 메모리 스캔)으로 캡처하는 추출기.
DRM 자체를 깨지 않고 공식 앱이 화면에 펼친 본문을 읽는 개인 백업 도구.
본인이 라이센스 보유한 콘텐츠만 대상.

설계: `docs/superpowers/specs/2026-06-09-naver-series-mobile-extractor-design.md`
현재 단계: M1 정찰 스파이크 — `docs/RUNBOOK-m1.md` 참고.

## 개발 환경
    python -m venv .venv && . .venv/bin/activate
    pip install -r requirements-dev.txt
    pytest
