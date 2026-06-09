# Docker 정찰 런북 (redroid + harness)

> 리눅스 호스트 기준. redroid 는 KVM 이 아니라 **호스트 커널**에서 Android 를
> 컨테이너로 돌린다. 따라서 호스트 커널에 binder 모듈이 있어야 한다.

## 0. 호스트 사전 준비 (필수)
    # binder 커널 모듈 로드 (재부팅 시 사라지므로 /etc/modules-load.d 등록 권장)
    sudo modprobe binder_linux devices="binder,hwbinder,vndbinder"
    ls /dev/binderfs 2>/dev/null || sudo mount -t binder binder /dev/binderfs
    # 구형 커널은 ashmem 도 필요할 수 있음:
    sudo modprobe ashmem_linux 2>/dev/null || true
    # Docker + compose 설치 확인
    docker --version && docker compose version

> 모듈이 없으면 redroid 컨테이너는 부팅 직후 죽는다(`docker compose logs redroid` 로 확인).
> 클라우드/관리형 커널이라 모듈을 못 올리는 경우 → 설계 §6 의 AVD 경로(`RUNBOOK-m1.md`)를 쓴다.

## 1. 스택 기동
    git clone https://github.com/basilro/ne_book_dl.git
    cd ne_book_dl
    docker compose up -d --build
    # Android 부팅 대기(최초 30~90초). 부팅 로그:
    docker compose logs -f redroid          # "Boot completed" 보이면 준비됨

## 2. 디바이스 연결 확인 (harness 안에서)
    docker compose exec harness bash
    adb connect redroid:5555
    adb devices                              # redroid:5555  device 떠야 함
    adb shell getprop ro.product.cpu.abi     # x86_64 또는 arm64-v8a

## 3. 시리즈 APK 설치
    # 호스트에서: 본인이 확보한 APK 를 apk/ 에 복사 (예: apk/series.apk)
    #   → 컨테이너 /apk 로 마운트됨
    docker compose exec harness adb -s redroid:5555 install /apk/series.apk
    docker compose exec harness adb -s redroid:5555 shell pm list packages | grep -i -E 'nhn|series|book'
    # 위에서 확인한 정확한 패키지명을 .env 의 NSM_PACKAGE 로 지정하거나 명령에 직접 사용

## 4. 화면 조작 = 호스트에서 scrcpy (헤드리스라 컨테이너엔 화면 없음)
    # 호스트에 scrcpy 설치 (apt install scrcpy 등)
    adb connect localhost:5555
    scrcpy -s localhost:5555
    # 뜬 창에서: 시리즈 앱 로그인(2단계 인증 계정은 '애플리케이션 비밀번호')
    #            → 본인 라이센스 보유(또는 무료) 회차 1편 진입
    # /data 가 볼륨(redroid-data)으로 영속화되므로 로그인은 한 번만.

## 5. frida-server 설치/기동 (harness 안에서)
    docker compose exec harness bash scripts/setup-frida.sh
    # → frida-ps -U 목록이 보이면 OK

## 6. 관찰 실행
    # 회차를 scrcpy 화면에 띄운 상태에서:
    docker compose exec harness bash scripts/recon.sh           # 후킹 관찰
    # [BODY!] 로그 + recon/out/cap_*.txt 가 본문이면 → A(후킹) go
    # 후킹이 본문을 못 잡으면:
    docker compose exec harness bash scripts/recon.sh memscan   # 메모리 스캔 폴백
    # recon/out/mem_*.txt 에 본문이 나오면 → B(폴백) go

## 7. 결과 기록 / 정리
    # recon/out/ 결과는 호스트 리포에 그대로 보인다(볼륨 마운트).
    # docs/FINDINGS-m1.md 의 표를 채워 go/no-go 판정.
    docker compose down            # 중지 (redroid-data 는 보존)
    # 완전 초기화하려면: docker compose down && rm -rf redroid-data

## 참고 / 트러블슈팅
- redroid 가 바로 죽음 → 0번 binder 모듈 미로드가 대부분. `docker compose logs redroid`.
- `frida-ps -U` 가 device 못 찾음 → harness 안에서 `adb connect redroid:5555` 먼저.
- frida 버전 불일치 에러 → setup-frida.sh 가 python frida 버전에 맞춰 받지만,
  redroid 의 frida-server 가 죽어있으면 5번 재실행.
- 앱이 root/에뮬 탐지로 로그인·다운로드 거부 → Magisk DenyList 등 우회 필요(이 단계에서 드러남).
- 환경값 바꾸기: 리포 루트에 `.env` 만들어 `NSM_PACKAGE=...`, `REDROID_IMAGE=redroid/redroid:14.0.0-latest` 지정.
