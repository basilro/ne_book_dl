# 런타임 결정 기록 (2026-06-09)

> 시놀로지 배포를 검토하다 발견한 제약과, 그에 따른 런타임 방향 결정. 클라우드
> 우분투에서 개발을 이어갈 때 이 맥락을 잃지 않기 위한 기록.

## 1. 검증된 핵심 사실 — 시놀로지 단독 추출은 불가능

시리즈 소설 본문 평문은 **오직 공식 네이티브 앱(Windows NaverBooks 또는 안드로이드 앱)만**
만들어낸다. 헤드리스 브라우저·순수 HTTP로는 불가.

근거 (`naver_books_dl/_probe` 탐사 기록):
- PC·모바일 웹 뷰어 모두 "회차 보기" 클릭 시 `nepub://...otp=<숫자>` 커스텀 스킴으로
  **네이티브 앱에 위임**한다. 본문 HTTPS 엔드포인트가 없다.
- 브라우저가 받은 큰 응답은 상세페이지 HTML · **독자 댓글** · 회차 메타뿐 —
  소설 본문은 단 한 조각도 네트워크로 오지 않았다.
- 따라서 naverpaper처럼 "크롬으로 웹페이지 긁기"가 통하지 않는다(그건 평범한 웹페이지였기 때문).

결론: **시놀로지(평범한 유저스페이스 Docker)는 본문 복호화를 단독으로 못 한다.**
DSM 커널에 binder 모듈이 없어 redroid도 직접 못 돌린다.

## 2. 런타임 옵션 (앱을 어디서 돌릴 것인가)

본문 복호화에는 다음 중 하나가 반드시 필요:

| 옵션 | 비용 | 추가 컴퓨터 | 모바일 | 비고 |
|---|---|---|---|---|
| 1. 공기계 폰 루팅 + frida | 폰 1대 루팅(Magisk) | 0 | ✅ 진짜 기기 | 에뮬 탐지 없음, 시놀로지=조율자 |
| 2. 리눅스 호스트 + redroid | 상시 리눅스/클라우드 | 1대 | ✅ 에뮬 | 에뮬 탐지 리스크, root 기본 |
| 3. 기존 Windows NaverBooks | 윈도우 PC | (윈도우) | ❌ | 이미 작동(naver_books_dl) |

- 시놀로지 VMM 안 Ubuntu VM 경로는 **사양 부족**으로 제외.
- 무루팅 + 추가기기 0 + 시놀로지 단독 = 불가 (DRM 뷰어가 보통 `FLAG_SECURE`로
  스크린샷까지 막아 OCR 우회도 대개 막힘).

## 3. 현재 결정

- **개발은 클라우드 우분투 VM에서 진행** (Windows 개발기에선 redroid/frida/Android
  테스트 불가). 옵션 2(리눅스+redroid)를 우선 검증하되, 정찰 결과에 따라 옵션 1도 가능.
- 시놀로지는 (선택) 상시 조율/저장/알림 역할로만 둘 수 있다 — 추출 런타임은 아님.

## 4. 클라우드 우분투에서 이어받기

```bash
git clone https://github.com/basilro/ne_book_dl.git
cd ne_book_dl
# IaaS VM 은 커널을 제어할 수 있어 binder 모듈 로드 가능:
sudo apt update && sudo apt install -y linux-modules-extra-$(uname -r) docker.io docker-compose-plugin
sudo modprobe binder_linux devices="binder,hwbinder,vndbinder"
docker compose up -d --build      # docs/RUNBOOK-docker.md 참고
```

클라우드 주의:
- **해외 IP 로그인 차단**: 네이버 보안설정에서 해외 로그인 차단 해제 필요(naverpaper README와 동일 이슈).
- 콘텐츠 라이센스/OTP가 계정·지역에 묶일 수 있음 — 정찰에서 확인.
- redroid x86_64 이미지 = x86_64 클라우드 VM. (ARM VM이면 arm64 이미지 자동.)

## 5. 다음 할 일
- 클라우드 우분투에서 `docs/RUNBOOK-docker.md`대로 redroid 기동 → 시리즈 APK 설치/로그인
  → `scripts/setup-frida.sh` → `scripts/recon.sh` 로 M1 정찰.
- `docs/FINDINGS-m1.md` 채워 go/no-go 판정 → M2(최소 추출 PoC) 계획.
