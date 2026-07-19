#!/bin/sh
# Simulate a late joiner: load the cluster's save in a scratch container.
# A joining client rebuilds Lua state exactly this way (save + control.lua).
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
set -e
docker cp cluster-factorio_0-1:/factorio/saves/open_world.zip /tmp/fle-loadtest.zip
docker run --rm --entrypoint /bin/sh --platform linux/arm64 \
  -v /tmp/fle-loadtest.zip:/save/open_world.zip \
  factoriotools/factorio:2.0.77 -c '
    mkdir -p /factorio/saves && cp /save/open_world.zip /factorio/saves/ &&
    timeout 40 /bin/box64 /opt/factorio/bin/x64/factorio \
      --start-server /factorio/saves/open_world.zip 2>&1 |
    grep -E "FLE-BAKE|rror|failed|InGame|Loading script.dat|on_load" | head -10'
