#!/bin/sh
# Runs inside `unshare --user --map-root-user --net --mount`: loopback only (plus the proxy), a gamescope stub and a
# neutral home /home/steve whose launcher data directory is the demo directory.
# usage: run.sh <data dir name> <demo dir under /home/saxxumm> <launcher binary> <control socket> <log file>
set -e
name=$1
demo=$2
bin=$3
sock=$4
log=$5
here=$(dirname "$(readlink -f "$0")")

ip link set lo up

mount -t tmpfs tmpfs /usr/local/bin
printf '#!/bin/sh\nexit 0\n' > /usr/local/bin/gamescope
chmod +x /usr/local/bin/gamescope

mount -t tmpfs tmpfs /mnt
mkdir /mnt/real
mount --rbind /home/saxxumm /mnt/real
real() { echo "/mnt/real${1#/home/saxxumm}"; }
agent=$(real "$here/agent.py")
# started from the bind, the original path disappears under the tmpfs below
python3 "$(real "$here/proxy_in.py")" /tmp/claude-1000/np.sock &
case "$bin" in /home/saxxumm/*) bin=$(real "$bin") ;; esac
demo=$(real "$demo")

mount -t tmpfs tmpfs /home
mkdir -p "/home/steve/.local/share/$name"
mount --bind "$demo" "/home/steve/.local/share/$name"
export HOME=/home/steve
unset XDG_CONFIG_HOME XDG_DATA_HOME XDG_CACHE_HOME XDG_STATE_HOME
cd /home/steve
export http_proxy=http://127.0.0.1:3128 https_proxy=http://127.0.0.1:3128 no_proxy=localhost,127.0.0.1
exec python3 "$agent" "$sock" "$log" "$bin"
