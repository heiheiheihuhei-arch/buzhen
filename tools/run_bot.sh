#!/bin/sh
# 挂机机器人：用无界面 Chrome 打开游戏，每波把手里的兵全摆上、开战、选第一张卡，打印每波结果。
# 用法：sh tools/run_bot.sh "draw=1&to=6"    参数：draw=1 每波把兵摆满；to=打几波；p0/pG=改第 1 波兵力和每波增量
# 需要：macOS + Google Chrome（装在 /Applications）+ python3
cd "$(dirname "$0")/.."
mkdir -p out/serve
(printf '<script>window.__errs=[];addEventListener("error",e=>__errs.push(String(e.message)));</script>\n'; cat index.html) > out/serve/index.html
python3 -m http.server 8791 --bind 127.0.0.1 --directory out/serve >/dev/null 2>&1 & SRV=$!
sleep 1
for q in "$@"; do d=out/bot_$(echo "$q" | tr '&=' '__'); rm -rf "$d"
  CDP_SIZE=420,900 python3 tools/cdp.py "http://127.0.0.1:8791/index.html?$q" tools/bot.js "$d" >/dev/null 2>&1
  echo "== $q"; cat "$d/log.txt"; echo; done
kill $SRV
