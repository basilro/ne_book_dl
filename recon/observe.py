"""실행 중인 시리즈 앱에 Frida attach → observe.js 로드 → 캡처 분류·저장.

사용:
    python recon/observe.py --package com.nhn.android.nbooks
    # 패키지명 확인: adb shell pm list packages | grep -i nhn
"""
import argparse
import json
import sys
import time
from pathlib import Path

import frida

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nsm.textutil import classify_capture  # noqa: E402

OUT = Path(__file__).resolve().parent / 'out'
SCRIPT = Path(__file__).resolve().parent / 'frida' / 'observe.js'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--package', required=True, help='앱 패키지명 또는 프로세스명')
    ap.add_argument('--spawn', action='store_true', help='attach 대신 새로 spawn')
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    device = frida.get_usb_device(timeout=10)
    print(f'[*] device: {device}')

    if args.spawn:
        pid = device.spawn([args.package])
        session = device.attach(pid)
    else:
        session = device.attach(args.package)
    print(f'[*] attached to {args.package}')

    seen = {'n': 0}

    def on_message(message, data):
        if message.get('type') != 'send':
            print(f'[frida] {message}')
            return
        payload = message['payload']
        src = payload.get('source', '?')
        if 'lib' in payload or 'path' in payload or 'url' in payload:
            print(f'[lib/url] {src}: {payload}')
            return
        body = data.decode('utf-8', 'replace') if isinstance(data, (bytes, bytearray)) else (data or '')
        info = classify_capture(body)
        seen['n'] += 1
        idx = seen['n']
        flag = 'BODY!' if info['probably_body'] else 'ui?'
        print(f'[{idx:03d}][{flag}] {src} hangul={info["korean"]} html={info["has_html"]} '
              f'len={payload.get("length")} :: {info["preview"]!r}')
        (OUT / f'cap_{idx:03d}_{src.replace(".", "_")}.txt').write_text(body, encoding='utf-8')
        (OUT / f'cap_{idx:03d}_{src.replace(".", "_")}.json').write_text(
            json.dumps({**payload, **{k: v for k, v in info.items() if k != 'preview'}},
                       ensure_ascii=False, indent=1), encoding='utf-8')

    script = session.create_script(SCRIPT.read_text(encoding='utf-8'))
    script.on('message', on_message)
    script.load()
    if args.spawn:
        device.resume(pid)
    print('[*] observe.js loaded. 앱에서 회차를 열어보세요. Ctrl+C 로 종료.')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\n[*] 종료')
        session.detach()


if __name__ == '__main__':
    main()
