#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NOVNC_ROOT="$ROOT_DIR/.novnc-root"
CHROMIUM_BIN="${CHROMIUM_BIN:-/home/codespace/.cache/ms-playwright/chromium-1148/chrome-linux/chrome}"
DISPLAY_NUM="${DISPLAY_NUM:-99}"
VNC_PORT="${VNC_PORT:-5900}"
NOVNC_PORT="${NOVNC_PORT:-6080}"
PROFILE_DIR="${PROFILE_DIR:-/tmp/chrome-profile}"

mkdir -p "$NOVNC_ROOT" "$PROFILE_DIR" /tmp/.X11-unix
chmod 1777 /tmp/.X11-unix

if [ ! -x "$CHROMIUM_BIN" ]; then
  echo "Chromium binary not found at $CHROMIUM_BIN" >&2
  exit 1
fi

if [ -d /usr/share/novnc ]; then
  rm -rf "$NOVNC_ROOT"/*
  cp -r /usr/share/novnc/. "$NOVNC_ROOT"/
fi

cat > "$NOVNC_ROOT/index.html" <<'HTML'
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="0; url=/vnc.html" />
    <title>GitHub</title>
  </head>
  <body>
    <p>Loading remote desktop…</p>
    <p><a href="/vnc.html">Open the desktop</a></p>
  </body>
</html>
HTML

cat > "$NOVNC_ROOT/favicon-github.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <rect width="24" height="24" rx="5" fill="#24292f"/>
  <path fill="#ffffff" d="M12 2C6.48 2 2 6.58 2 12.25c0 4.53 2.87 8.37 6.84 9.73.5.1.68-.22.68-.48v-1.7c-2.78.62-3.37-1.36-3.37-1.36-.46-1.18-1.12-1.49-1.12-1.49-.9-.63.07-.62.07-.62 1 .07 1.53 1.04 1.53 1.04.9 1.57 2.35 1.12 2.92.86.09-.67.35-1.13.64-1.39-2.22-.26-4.56-1.14-4.56-5.08 0-1.12.39-2.04 1.03-2.76-.1-.25-.45-1.29.1-2.69 0 0 .84-.27 2.75 1.05A9.3 9.3 0 0 1 12 6.77c.85 0 1.71.12 2.51.34 1.91-1.32 2.75-1.05 2.75-1.05.55 1.4.2 2.44.1 2.69.64.72 1.03 1.64 1.03 2.76 0 3.95-2.34 4.82-4.57 5.07.36.32.68.95.68 1.92v2.85c0 .26.18.58.69.48A10.26 10.26 0 0 0 22 12.25C22 6.58 17.52 2 12 2Z"/>
</svg>
SVG

python3 - "$NOVNC_ROOT" <<'PY'
import os
import sys
import re
root = sys.argv[1]
for filename in ['vnc.html', 'vnc_lite.html']:
    path = os.path.join(root, filename)
    if not os.path.exists(path):
        continue
    with open(path, 'r', encoding='utf-8') as fh:
        text = fh.read()
    text = text.replace('<title>noVNC</title>', '<title>GitHub</title>')
    text = text.replace('<title>School Project Browser</title>', '<title>GitHub</title>')
    text = text.replace('<title>School Project Remote Browser</title>', '<title>GitHub</title>')
    text = text.replace('/favicon.svg', '/favicon-github.svg?v=2')
    if '<link rel="icon"' not in text:
        text = text.replace('</head>', '    <link rel="icon" href="/favicon-github.svg?v=2" type="image/svg+xml">\n    <link rel="shortcut icon" href="/favicon-github.svg?v=2">\n</head>', 1)
    text = text.replace('document.title = "noVNC"', 'document.title = "GitHub"')
    text = text.replace('document.title = "School Project Browser"', 'document.title = "GitHub"')
    if 'document.title = "GitHub"' not in text:
        text = text.replace('</head>', '<script>window.addEventListener("load", () => { document.title = "GitHub"; });</script>\n</head>', 1)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)
PY

pkill -f "Xvfb :$DISPLAY_NUM" >/dev/null 2>&1 || true
pkill -f "x11vnc -display :$DISPLAY_NUM" >/dev/null 2>&1 || true
pkill -f "websockify --web $NOVNC_ROOT $NOVNC_PORT localhost:$VNC_PORT" >/dev/null 2>&1 || true
pkill -f "$CHROMIUM_BIN" >/dev/null 2>&1 || true

rm -f /tmp/.X11-unix/X$DISPLAY_NUM

Xvfb :"$DISPLAY_NUM" -screen 0 1280x960x24 >/tmp/xvfb.log 2>&1 &

display=":$DISPLAY_NUM"
export DISPLAY="$display"

CHROMIUM_FLAGS=(
  --no-sandbox
  --disable-gpu
  --disable-software-rasterizer
  --disable-dev-shm-usage
  --enable-unsafe-swiftshader
  --use-gl=swiftshader
  --enable-features=AcceleratedVideoDecodeLinuxZeroCopyGL,PlatformHEVCDecoderSupport,VaapiVideoEncoder,UseOzonePlatform
  --ignore-gpu-blocklist
  --disable-features=UseChromeOSDirectVideoDecoder
  --autoplay-policy=no-user-gesture-required
  --media-cache-size=104857600
  --disk-cache-size=1073741824
  --no-first-run
  --no-default-browser-check
  --disable-background-networking
  --disable-sync
  --disable-extensions
  --remote-debugging-port=9222
  --user-data-dir="$PROFILE_DIR"
)

"$CHROMIUM_BIN" "${CHROMIUM_FLAGS[@]}" >/tmp/chrome.log 2>&1 &

x11vnc -display "$display" -forever -shared -nopw -listen 0.0.0.0 -xkb -noxdamage -rfbport "$VNC_PORT" >/tmp/x11vnc.log 2>&1 &

websockify --web "$NOVNC_ROOT" "$NOVNC_PORT" "localhost:$VNC_PORT" >/tmp/novnc.log 2>&1 &

echo "Remote browser is starting on http://127.0.0.1:${NOVNC_PORT}/"
