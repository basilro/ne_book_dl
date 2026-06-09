#!/usr/bin/env bash
# harness 컨테이너 안에서 실행. redroid 에 adb 연결 → 디바이스 ABI 맞는
# frida-server(python frida 버전과 동일) 다운로드 → push → 실행.
set -euo pipefail

ADB_TARGET="${ADB_TARGET:-redroid:5555}"
BIN="/data/local/tmp/frida-server"

echo "[*] adb connect ${ADB_TARGET}"
adb start-server >/dev/null 2>&1 || true
adb connect "${ADB_TARGET}" >/dev/null
adb -s "${ADB_TARGET}" wait-for-device

FRIDA_VER="$(frida --version)"
ABI="$(adb -s "${ADB_TARGET}" shell getprop ro.product.cpu.abi | tr -d '\r')"
case "${ABI}" in
  x86_64)      FA=x86_64 ;;
  arm64-v8a)   FA=arm64 ;;
  x86)         FA=x86 ;;
  armeabi-v7a) FA=arm ;;
  *) echo "[!] 알 수 없는 ABI '${ABI}', x86_64 로 시도"; FA=x86_64 ;;
esac

URL="https://github.com/frida/frida/releases/download/${FRIDA_VER}/frida-server-${FRIDA_VER}-android-${FA}.xz"
echo "[*] download ${URL}"
wget -qO /tmp/frida-server.xz "${URL}"
unxz -f /tmp/frida-server.xz

adb -s "${ADB_TARGET}" push /tmp/frida-server "${BIN}" >/dev/null
adb -s "${ADB_TARGET}" shell "chmod 755 ${BIN}"

# redroid 는 기본 root. 기존 frida-server 정리 후 detached 실행.
adb -s "${ADB_TARGET}" shell "su 0 sh -c 'pkill -f frida-server || true'" >/dev/null 2>&1 || true
adb -s "${ADB_TARGET}" shell "su 0 sh -c '${BIN} -D'" >/dev/null 2>&1 &
sleep 2

echo "[*] frida-server ${FRIDA_VER} (${FA}) started"
echo "[*] frida-ps -U (상위 15):"
frida-ps -U | head -n 15
