"""폴백: frida Memory.scan 으로 앱 메모리에서 <html ... </html> 청크 탐색.

사용:
    python recon/memscan.py --package com.nhn.android.nbooks
"""
import argparse
import sys
import time
from pathlib import Path

import frida

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nsm.textutil import classify_capture  # noqa: E402

OUT = Path(__file__).resolve().parent / 'out'

# rw- 영역을 훑어 <html 패턴(UTF-8 "3c 68 74 6d 6c") 검색, 최대 4MB 청크 추출
SCAN_JS = r"""
'use strict';
var PATTERN = '3c 68 74 6d 6c'; // "<html"
function run() {
  var ranges = Process.enumerateRanges({ protection: 'r--', coalesce: true });
  send({ kind: 'info', ranges: ranges.length });
  var hits = 0;
  ranges.forEach(function (r) {
    try {
      Memory.scanSync(r.base, r.size, PATTERN).forEach(function (m) {
        try {
          var max = 4 * 1024 * 1024;
          var avail = r.size - m.address.sub(r.base).toInt32();
          var n = Math.min(max, avail);
          var bytes = Memory.readByteArray(m.address, n);
          hits++;
          send({ kind: 'hit', addr: m.address.toString(), len: n }, bytes);
        } catch (e) {}
      });
    } catch (e) {}
  });
  send({ kind: 'done', hits: hits });
}
run();
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--package', required=True)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    device = frida.get_usb_device(timeout=10)
    session = device.attach(args.package)
    print(f'[*] attached to {args.package}')

    state = {'i': 0}

    def on_message(message, data):
        if message.get('type') != 'send':
            print(f'[frida] {message}')
            return
        p = message['payload']
        if p.get('kind') == 'info':
            print(f'[*] scanning {p["ranges"]} ranges...')
        elif p.get('kind') == 'hit' and data:
            body = bytes(data)
            # </html> 까지로 자르기
            end = body.lower().find(b'</html>')
            if end >= 0:
                body = body[:end + 7]
            info = classify_capture(body)
            if not info['probably_body']:
                return
            state['i'] += 1
            idx = state['i']
            print(f'[hit {idx:03d}] addr={p["addr"]} hangul={info["korean"]} '
                  f':: {info["preview"]!r}')
            (OUT / f'mem_{idx:03d}.txt').write_text(
                body.decode('utf-8', 'replace'), encoding='utf-8')
        elif p.get('kind') == 'done':
            print(f'[*] scan done. raw hits={p["hits"]}, body hits saved={state["i"]}')

    script = session.create_script(SCAN_JS)
    script.on('message', on_message)
    script.load()
    time.sleep(2)
    session.detach()


if __name__ == '__main__':
    main()
