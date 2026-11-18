"""把 art/game/fig_*.webp 和 anim_*.webp（序列帧条，见 build_anim.py）写进 index.html（游戏是单个文件，图片用 base64 内嵌）。换了图之后重跑一次。
用法：python3 tools/art/embed_figs.py
"""
import base64, pathlib, re
root = pathlib.Path(__file__).resolve().parents[2]
html = root / "index.html"; s = html.read_text(encoding="utf-8")
figs = ",\n".join(f"  {k}: 'data:image/webp;base64,{base64.b64encode((root / 'art' / 'game' / f'fig_{k}.webp').read_bytes()).decode()}'" for k in ["shield", "spear", "bow", "horse"])
import json
meta = json.loads((root / "art" / "game" / "anim.json").read_text()) if (root / "art" / "game" / "anim.json").exists() else {}
anims = ",\n".join(f"  {k}: {{ n: {m['n']}, w: {m['w']}, h: {m['h']}, src: 'data:image/webp;base64,{base64.b64encode((root / 'art' / 'game' / f'anim_{k}.webp').read_bytes()).decode()}' }}" for k, m in meta.items())
block = f"/*FIG-BEGIN*/\nconst FIG = {{\n{figs}\n}};\n// 火山出的动作视频抽成的序列帧条：n 帧横排，单帧 w×h\nconst ANIM = {{\n{anims}\n}};\n/*FIG-END*/"
s2, n = re.subn(r"/\*FIG-BEGIN\*/.*?/\*FIG-END\*/", lambda m: block, s, flags=re.S)
assert n == 1, "index.html 里没找到 /*FIG-BEGIN*/ … /*FIG-END*/"
html.write_text(s2, encoding="utf-8"); print("已写入", len(block) // 1024, "KB")
