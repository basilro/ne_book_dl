#!/usr/bin/env bash
# harness 컨테이너 안에서 실행. adb 연결 보장 후 observe.py 기동.
# 사용: bash scripts/recon.sh           # 후킹 관찰(기본)
#       bash scripts/recon.sh memscan   # 메모리 스캔 폴백
set -euo pipefail

ADB_TARGET="${ADB_TARGET:-redroid:5555}"
PKG="${NSM_PACKAGE:-com.nhn.android.nbooks}"
MODE="${1:-observe}"

adb start-server >/dev/null 2>&1 || true
adb connect "${ADB_TARGET}" >/dev/null
adb -s "${ADB_TARGET}" wait-for-device

case "${MODE}" in
  observe) python recon/observe.py --package "${PKG}" ;;
  memscan) python recon/memscan.py --package "${PKG}" ;;
  *) echo "사용: bash scripts/recon.sh [observe|memscan]"; exit 2 ;;
esac
