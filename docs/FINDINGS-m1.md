# M1 정찰 결과 / go-no-go

작성일: ____   /   앱 버전: ____   /   디바이스: AVD android-33 x86_64 google_apis

## 1. 환경 체크
- [ ] /dev/kvm 사용 가능
- [ ] AVD non-Play 이미지에서 `adb root` 성공
- [ ] frida-server 기동 + `frida-ps -U` 정상
- [ ] 시리즈 APK 설치 + 로그인 성공
- [ ] 루팅/에뮬 탐지로 막힘? (예/아니오 + 증상)

## 2. 패키지/구조
- 패키지명: ____
- 로드된 네이티브 라이브러리(dlopen/loadLibrary 로그 중 의심): ____
- 본문 뷰어가 WebView인가 네이티브인가 (관찰 근거): ____

## 3. 캡처 결과 (recon/out)
| 출처(source) | hangul | has_html | 본문? | 비고 |
|---|---|---|---|---|
| WebView.loadDataWithBaseURL |  |  |  |  |
| WebView.evaluateJavascript |  |  |  |  |
| TextView.setText |  |  |  |  |
| memscan(<html>) |  |  |  |  |

## 4. 판정
- [ ] **go (A)**: 후킹 한 지점에서 회차 본문 XHTML/텍스트 결정적 캡처 → 후킹 지점: ____
- [ ] **부분 go (B)**: 메모리 스캔에서 본문 `<html>` 확보
- [ ] **no-go**: 평문이 메모리에도 없음 → C(접근성/OCR) 검토 또는 중단

## 5. 다음 단계 메모 (M2 계획 입력)
- 확정 메커니즘: ____
- 안정적 캡처를 위해 필요한 대기/네비 조건: ____
- 우회 필요했던 보호(루트탐지 등): ____
