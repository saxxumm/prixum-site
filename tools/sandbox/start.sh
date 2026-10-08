#!/bin/sh
# Starts Prixum or Prism Launcher with fresh demo data on a hidden screen and returns once it is drawn.
# usage: start.sh <prixum|prism> <ru|en>
# env:   VW, VH (screen size, default 1920x1200), QT_SCALE_FACTOR (default 1.5), THEME, WALLPAPER, MASCOT
set -e
app=$1
lang=$2
here=$(dirname "$(readlink -f "$0")")
work="$here/work"
sock=/tmp/claude-1000/sandbox.sock
mkdir -p "$work" /tmp/claude-1000

python3 "$here/ctl.py" quit > /dev/null 2>&1 || true
for _ in 1 2 3 4 5 6 7 8 9 10; do [ -S "$sock" ] || break; sleep 0.5; done
rm -f "$sock"

pgrep -f "proxy_out.py /tmp/claude-1000/np.sock" > /dev/null || \
    setsid python3 "$here/proxy_out.py" /tmp/claude-1000/np.sock > "$work/proxy.log" 2>&1 < /dev/null &

if [ "$app" = prixum ]; then
    name=PrixumLauncher
    bin=/home/saxxumm/.local/opt/prixumlauncher/bin/prixumlauncher
else
    name=PrismLauncher
    bin=/usr/bin/prismlauncher
fi
export VW="${VW:-1920}" VH="${VH:-1200}" QT_SCALE_FACTOR="${QT_SCALE_FACTOR:-1.5}"
python3 "$here/make_demo.py" "$work/demo-$app" "$app" "$lang" > /dev/null
setsid unshare --user --map-root-user --net --mount "$here/run.sh" "$name" "$work/demo-$app" "$bin" "$sock" \
    "/tmp/claude-1000/sandbox-launcher.log" > "$work/run.log" 2>&1 < /dev/null &

for _ in $(seq 1 120); do [ -S "$sock" ] && break; sleep 0.5; done
[ -S "$sock" ] || { echo "the sandbox did not come up, see $work/run.log"; exit 1; }
python3 "$here/ctl.py" settle quiet=1 limit=20 > /dev/null
echo "running $app ($lang) at ${VW}x${VH}, scale $QT_SCALE_FACTOR"
