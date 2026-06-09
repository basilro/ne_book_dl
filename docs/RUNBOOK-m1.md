# M1 정찰 런북 (리눅스 + KVM)

> 사람이 리눅스 호스트에서 순서대로 실행. Ubuntu 22.04+ 기준.

## 0. 사전 점검
    egrep -c '(vmx|svm)' /proc/cpuinfo   # > 0 이면 가상화 지원
    ls /dev/kvm                          # 존재해야 함 (없으면 BIOS 가상화 ON + kvm 모듈)
    sudo usermod -aG kvm "$USER"         # 로그아웃/로그인

## 1. Android SDK / 에뮬레이터 (cmdline-tools)
    # https://developer.android.com/studio#command-line-tools-only 에서 linux zip
    mkdir -p ~/Android/cmdline-tools && cd ~/Android/cmdline-tools
    # unzip 후 latest/ 로 배치
    export ANDROID_SDK_ROOT=~/Android
    export PATH=$PATH:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/emulator
    sdkmanager --licenses
    # non-Play(=google_apis, NOT google_apis_playstore) 이미지여야 adb root 가능
    sdkmanager "platform-tools" "emulator" "system-images;android-33;google_apis;x86_64"
    avdmanager create avd -n nsm -k "system-images;android-33;google_apis;x86_64" -d pixel_5

## 2. 에뮬레이터 헤드리스 기동
    emulator -avd nsm -no-window -no-audio -gpu swiftshader_indirect -no-snapshot &
    adb wait-for-device
    adb root                              # google_apis 이미지에서 성공해야 함
    adb shell getprop ro.build.version.release

## 3. frida-server 설치 (디바이스 아키텍처 x86_64)
    pip install frida-tools               # 호스트. 버전 메모: frida --version
    # https://github.com/frida/frida/releases 에서 frida-server-<버전>-android-x86_64.xz
    unxz frida-server-*-android-x86_64.xz
    adb push frida-server-*-android-x86_64 /data/local/tmp/frida-server
    adb shell chmod 755 /data/local/tmp/frida-server
    adb shell "/data/local/tmp/frida-server &"
    frida-ps -U | head                    # 디바이스 프로세스 보이면 OK

## 4. 시리즈 앱 설치 + 로그인
    adb install /path/to/네이버시리즈.apk   # 본인이 확보한 APK
    # 앱 실행 후 로그인(2단계 인증 계정은 '애플리케이션 비밀번호' 사용)
    adb shell monkey -p com.nhn.android.nbooks 1   # 앱 시작(패키지명 확인 필요)
    # 패키지명 확인:
    adb shell pm list packages | grep -i -E 'nhn|series|book'

## 5. 관찰 실행 + 회차 열기
    # 터미널 A: 관찰 시작 (패키지명은 4에서 확인한 값)
    python recon/observe.py --package com.nhn.android.nbooks
    # 터미널 B 또는 화면: 앱에서 본인 라이센스 보유(또는 무료) 회차 1편 진입
    # → 터미널 A 에 [BODY!] 로그가 뜨고 recon/out/cap_*.txt 가 본문이면 = A(후킹) go

## 6. 후킹이 본문을 못 잡으면 폴백
    # 회차를 화면에 띄운 상태에서:
    python recon/memscan.py --package com.nhn.android.nbooks
    # recon/out/mem_*.txt 에 본문이 나오면 = B(메모리 스캔) go

## 7. 결과 기록
    docs/FINDINGS-m1.md 의 표를 채운다.
