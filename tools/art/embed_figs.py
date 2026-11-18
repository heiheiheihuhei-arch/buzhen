"""把 art/game/fig_*.webp 写进 index.html（游戏是单个文件，图片用 base64 内嵌）。换了图之后重跑一次。
用法：python3 tools/art/embed_figs.py
"""
import base64, pathlib, re
root = pathlib.Path(__file__).resolve().parents[2]
html = root / "index.html"; s = html.read_text(encoding="utf-8")
figs = ",\n".join(f"  {k}: 'data:image/webp;base64,{base64.b64encode((root / 'art' / 'game' / f'fig_{k}.webp').read_bytes()).decode()}'" for k in ["shield", "spear", "bow", "horse"])
block = f"/*FIG-BEGIN*/\nconst FIG = {{\n{figs}\n}};\n/*FIG-END*/"
s2, n = re.subn(r"/\*FIG-BEGIN\*/.*?/\*FIG-END\*/", lambda m: block, s, flags=re.S)
assert n == 1, "index.html 里没找到 /*FIG-BEGIN*/ … /*FIG-END*/"
html.write_text(s2, encoding="utf-8"); print("已写入", len(block) // 1024, "KB")
