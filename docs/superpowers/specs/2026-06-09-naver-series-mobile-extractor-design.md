# naver_series_mobile — 안드로이드 앱 기반 시리즈 본문 추출기 설계

- 날짜: 2026-06-09
- 상태: 설계 승인 → 구현 계획 작성 예정
- 작성 맥락: `naver_books_dl`(Windows 메모리 덤프 방식)의 자매 프로젝트. 사이드 프로젝트.

---

## 1. 배경 / 동기

### 1.1 출발점
`naverpaper` 프로젝트가 **Playwright 디바이스 에뮬레이션**(`playwright.devices['Galaxy S9+']`, `headless=True`)으로 리눅스 서버(Oracle Cloud, Synology)에서 네이버 서비스를 다루는 것을 보고, "시리즈도 모바일 기반으로 본문을 가져올 수 있지 않을까?"라는 발상에서 시작.

### 1.2 핵심 사실 — 모바일 *웹* 에뮬레이션은 본문에 안 통한다 (검증됨)
`naverpaper`가 통하는 이유는 네이버페이 캠페인 페이지가 **평범한 웹페이지**라 DOM에서 바로 긁히기 때문. 그러나 시리즈 본문은 다르다. `naver_books_dl/_probe`에 이미 동일한 시도(`probe_viewer.py`, Galaxy S9+ 에뮬레이션)가 있었고 결과는:

- 모바일 웹 뷰어에서 잡힌 긴 텍스트는 **전부 상세페이지 UI**(회차목록·랭킹·푸터)뿐, **본문은 0**.
- 모바일에서 "첫화보기"를 누르면 본문을 DOM에 그리지 않고 **네이티브 앱(`nepub://`)을 띄움**.
- `viewerLaunchUrl` 응답은 본문 HTTPS 주소가 아니라 OTP 토큰 하나뿐:
  ```
  nepub://width=1024;height=768;auth=true;otp=3509107384
  ```
- 즉, 암호화된 EPUB 다운로드 + Fasoo DRM 복호화는 **오직 네이티브 앱만** 수행. 브라우저/HTTP 클라이언트로 접근 가능한 평문 엔드포인트는 없다.

### 1.3 그래서 "모바일 방식"의 진짜 의미
통하는 형태는 "모바일 웹 긁기"가 아니라 **실제 안드로이드 시리즈 앱을 (에뮬레이터에서) 구동해, 앱이 복호화한 평문을 Frida 후킹/메모리 덤프로 캡처**하는 것 — 즉 현재 Windows에서 NaverBooks.exe로 하는 일의 **안드로이드 + 리눅스 버전**. DRM을 직접 깨지 않고 "공식 앱이 푼 결과를 읽는" 원칙은 그대로 유지한다.

### 1.4 왜 굳이 옮기나 (이 프로젝트의 가치)
- **Windows 탈출**: 현재 방식은 Windows + NaverBooks.exe + CEF 온스크린 렌더 + Win32 `ReadProcessMemory`에 묶여 있음.
- **깔끔한 추출**: 메모리 전체를 더듬는 블라인드 스캔 대신, 앱이 복호화한 데이터를 정확한 지점에서 결정적으로 가로채기.
- **이식성**: 리눅스로 완전 이주 → 추후 redroid 기반 Docker화/헤드리스 운영 가능성.

---

## 2. 목표 / 비목표

### 목표
- 리눅스 위에서 안드로이드 시리즈 앱을 헤드리스 구동.
- 본인이 라이센스 보유한 회차의 본문 평문을 캡처해 `.txt`로 저장.
- 기존 `naver_books_dl`과 동일한 출력 포맷(`{content_id}_{vol:04d}.txt`, `info.xml`, `cover.jpg`)으로 호환.
- 앱 hookability를 1단계 정찰로 먼저 검증(go/no-go).

### 비목표 (적어도 초기)
- DRM 알고리즘 자체의 리버스/복호화 재구현 (Fasoo를 직접 깨지 않음 — 기존 원칙).
- 24/7 무인 서버 자동수집 운영 (구조는 열어두되 초기 목표 아님).
- iOS 지원.
- 만화(이미지) 콘텐츠 (텍스트 소설 우선).

---

## 3. 핵심 결정 사항 (브레인스토밍 합의)

| 항목 | 결정 |
|---|---|
| 핵심 가치 | Windows 탈출 + 깔끔한(결정적) 추출 |
| 실행 환경 | Linux 완전 이주, KVM 가속 에뮬레이터 + Frida |
| 코드 형태 | 완전 새 사이드 프로젝트 (`naver_series_mobile`), 기존에서 로직만 차용 |
| 추출 전략 | 정찰 스파이크 → **A. Frida 후킹 1순위**, **B. 메모리 스캔 폴백** |
| 런타임 | 스파이크는 Android Studio AVD, 검증 후 redroid 이식 |
| 인증 | 앱 로그인 1회 처리 후 emulator userdata 스냅샷으로 세션 영속화 |

---

## 4. 아키텍처 (5계층)

```
┌─ ① Android 런타임 (AVD/redroid on KVM, headless) ──────────┐
│   네이버 시리즈 APK 설치 · adb root · frida-server 구동      │
└───────────────────────▲───────────────┬───────────────────┘
        adb / uiautomator2 │               │ frida attach
┌─────────────────────────┴──┐   ┌────────┴───────────────────┐
│ ② app_driver.py            │   │ ③ frida_hook.js + extractor│
│  로그인 시드·세션 영속화     │   │  A: 렌더/복호화 함수 후킹    │
│  작품/회차 네비 → 뷰어 진입  │   │  B: <html> 메모리 스캔(폴백) │
│  렌더 완료 대기             │   │  HTML→텍스트 (기존 로직 포팅)│
└─────────────────────────┬──┘   └────────┬───────────────────┘
                          │               │
┌─────────────────────────┴───────────────┴───────────────────┐
│ ④ client.py (naver_books_dl에서 차용, 순수 requests)         │
│   쿠키→회차목록·OTP·메타(info.xml/cover) — Linux OK 그대로    │
├──────────────────────────────────────────────────────────────┤
│ ⑤ runner: 회차 루프·중복 skip·.txt 저장·이력(_history.json)  │
└──────────────────────────────────────────────────────────────┘
```

### ① Android 런타임
- AVD: Google APIs **non-Play** AOSP x86_64 이미지(→ `adb root` 즉시 가능), KVM 가속, `emulator -no-window`로 헤드리스.
- frida-server를 디바이스에 push 후 실행, 호스트에서 `frida`/`frida-trace`로 attach.
- 시리즈 APK는 수동 확보분을 `adb install` (또는 Aurora Store).

### ② app_driver.py — 앱 제어
- `uiautomator2`(권장) 또는 Appium으로 앱 UI 자동화.
- 로그인 1회 시드(자동입력 또는 수동) → emulator userdata 스냅샷 보존으로 재로그인 회피.
- 대상 작품/회차로 네비게이트 → 뷰어 진입 → 렌더 완료 대기.

### ③ frida_hook.js + extractor.py — 계측/추출
- **A (1순위)**: 정찰로 찾은 지점 후킹해 XHTML/텍스트를 결정적으로 캡처.
- **B (폴백)**: 루팅 환경에서 `/proc/<pid>/mem` 또는 Frida `Memory.scan`으로 `<html>` 청크 스캔.
- HTML→텍스트 변환, 한국어 글자 수 필터, 본문 청크 선택은 `naver_books_dl/extractor.py` 로직 포팅.

### ④ client.py — API/메타 (차용)
- 쿠키→`isLogin`, `volumeMoreList`(회차목록), `viewerLaunchUrl`(OTP), 상세페이지 파싱(메타).
- 순수 `requests`라 리눅스에서 그대로 동작. 회차 네비게이션에 필요한 productNo/volumeNo 매핑 제공.

### ⑤ runner — 오케스트레이션/출력
- 회차 루프, 이미 받은 회차 skip, `.txt` 저장, `info.xml`/`cover.jpg`, 이력(`_history.json`).
- 멀티작품 자동수집·웹훅 알림은 후속(기존 `core.py` 패턴 참고).

---

## 5. 1단계 — 정찰 스파이크 (go/no-go, 최우선)

전체 설계의 전제(앱 hookability)를 여기서 검증한다.

1. Android 런타임 구축 + `adb root` + frida-server push/실행.
2. 시리즈 APK 설치 → 로그인 → **무료 회차 1편** 뷰어 진입.
3. Frida로 "본문 평문이 어디서·어떤 형태로 나타나나" 동시 관찰:
   - WebView? → `android.webkit.WebView.loadDataWithBaseURL` / `loadUrl` / `evaluateJavascript`
   - localhost 로컬서버? → 소켓/HTTP 후킹
   - 네이티브 TextView? → `TextView.setText`
   - Fasoo `.so`? → `dlopen`/복호화 심볼 추적
   - 메모리에 `<html>`/한국어 본문 존재 여부 스캔
4. **산출물**: 본문 평문화 지점 보고서 → A/B/C 확정 및 다음 단계 진입 여부 결정.

### go/no-go 기준
- **go(A)**: 후킹 한 지점에서 회차 XHTML/텍스트가 결정적으로 잡힘.
- **부분 go(B)**: 후킹은 깨끗하지 않지만 메모리에 평문 `<html>`이 존재 → 메모리 스캔으로 진행.
- **no-go**: 평문이 메모리에도 안 보임(별도 보안 컨테이너/네이티브 렌더 only) → C(접근성/OCR) 검토 또는 중단.

---

## 6. 런타임 선택: AVD-first → redroid-later

- **스파이크 = Android Studio AVD**: non-Play AOSP 이미지로 `adb root` 즉시, KVM 가속, frida-server 설치 쉬움, `-no-window` 헤드리스. 가장 빨리 띄울 수 있어 go/no-go에 최적.
- **검증 후 redroid 이식**: Docker 안드로이드, root 기본 → 헤드리스/서버/Docker화 종착지. 단 호스트 커널에 `binder_linux` 모듈 필요(`modprobe binder_linux devices="binder,hwbinder,vndbinder"`) — 배포 커널 따라 안 될 수 있어 스파이크 단계에서는 회피.

---

## 7. 인증 / 세션 (naverpaper 발상 차용)

앱은 쿠키 주입이 어렵다. 따라서:
- **앱 로그인 화면을 1회 처리**(id/pw 자동입력 또는 수동) 후, emulator **userdata 스냅샷으로 세션 영속화**. naverpaper가 Playwright `storage_state`를 DB에 저장해 재로그인을 피하는 것과 동일한 원리.
- 2단계 인증 계정은 **네이버 애플리케이션 비밀번호** 사용.
- 한편 ④ `client.py`(API)는 별도로 Cookie-Editor 쿠키를 사용 — 회차목록/OTP/메타 조회용. (앱 세션과 API 쿠키는 분리 운용)

---

## 8. 재사용 자산 (`naver_books_dl`에서)

| 자산 | 용도 | 이식성 |
|---|---|---|
| `client.py` | 회차목록·OTP·로그인검증·메타 | 순수 requests, 그대로 OK |
| `extractor._html_to_text`, 한국어 필터, `pick_main_chapter` | HTML→텍스트, 본문 선별 | 함수 단위 포팅 |
| `meta.py` | `info.xml` + `cover.jpg` (ComicInfo) | 그대로 OK |
| 저장 포맷 | `{title}/{content_id}_{vol:04d}.txt` | 동일 유지 |
| `history.py` | 다운로드 이력 | 후속 단계에서 차용 |

**새로 작성**: ① 런타임 부트스트랩 스크립트, ② `app_driver.py`, ③ `frida_hook.js`(+ Android용 메모리 스캔 폴백).

---

## 9. 출력 포맷

기존과 동일하게 유지하여 라이브러리/리더 호환:
```
out/
└── {작품명}/
    ├── info.xml          # ComicInfo
    ├── cover.jpg
    ├── {content_id}_0001.txt
    └── ...
```

---

## 10. 리스크 / 미해결 질문

- **[linchpin] 앱 hookability 불명** → 1단계 스파이크가 해소.
- **루팅/에뮬 탐지 · Play Integrity**: 앱이 root 감지로 로그인/다운로드를 막을 수 있음 → Magisk DenyList / Frida stealth 필요할 수 있음(1단계에서 드러남).
- **콘텐츠 다운로드 디바이스 바인딩** 가능성(OTP가 특정 기기에 묶일 수 있음).
- **redroid binder 커널 모듈** 호스트 의존 → AVD-first로 우회.
- **앱 버전 업데이트 시 후킹 지점 깨짐** → B(메모리 스캔) 폴백 유지로 완충.
- **법적/약관**: 본인이 합법적으로 접근 가능한(라이센스 보유) 콘텐츠만. DRM 자체를 깨지 않고 공식 앱이 화면에 펼친 본문을 읽는 도구. 개인 백업 용도.

---

## 11. 단계별 마일스톤

1. **M1 — 정찰 스파이크 (go/no-go)**: 런타임+frida 구축, 앱 설치/로그인, 본문 평문화 지점 규명. → A/B/C 확정.
2. **M2 — 최소 추출 PoC**: 회차 1편 → `.txt` (확정된 메커니즘으로).
3. **M3 — 드라이버 자동화**: app_driver로 작품/회차 네비 + 세션 영속화 + 렌더 대기 안정화.
4. **M4 — runner 통합**: 회차 루프·중복 skip·`info.xml`/`cover`·이력. 기존 출력 포맷 호환.
5. **M5 (선택) — redroid 이식 / 헤드리스·Docker화**.

---

## 12. 법적 / 윤리 주의

`naver_books_dl`과 동일 원칙을 명시적으로 계승한다:
> 본인 계정으로 합법적으로 접근 가능한(구매·구독·라이센스 보유) 콘텐츠만 대상. 본인이 화면으로 볼 수 있는 본문을 자동화로 추출하는 개인 백업 도구이며, DRM 자체를 깨지 않는다(공식 앱의 복호화 결과를 읽을 뿐).
