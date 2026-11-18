"""把 AI 出的素材表（白底、部件互不重叠）切成一个个透明的部件图。
做法：从图的四边往里漫水填充「接近白色」的像素当背景（部件内部的白色不会被挖掉），
剩下的按连通块分开，每块按外接框裁出来，背景变透明，边缘按离白色的远近做半透明（抗锯齿）。
用法：python3 tools/art/cut_sheet.py 素材表.png 输出目录 [最小面积]
第 4 个参数是「多白算背景」（默认 232）。
会打印每个部件的编号、位置、大小，并出一张带编号的预览图（输出目录/_index.jpg）。
"""
import pathlib, subprocess, sys, struct, zlib
from collections import deque

src, out = sys.argv[1], pathlib.Path(sys.argv[2])
min_area = int(sys.argv[3]) if len(sys.argv) > 3 else 400
WHITE = int(sys.argv[4]) if len(sys.argv) > 4 else 232   # 背景有浅灰投影时调低（比如 190），把投影也当背景
out.mkdir(parents=True, exist_ok=True)
wh = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", src],
                    capture_output=True, text=True, check=True).stdout.strip().split(",")
W, H = int(wh[0]), int(wh[1])
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout

def whiteness(i):
    r, g, b = raw[i], raw[i + 1], raw[i + 2]
    return min(r, g, b)

# 背景：从边上漫水，接近白（最暗的通道 ≥ 232）且颜色不鲜艳
bg = bytearray(W * H)
q = deque()
for x in range(W):
    q.append(x); q.append((H - 1) * W + x)
for y in range(H):
    q.append(y * W); q.append(y * W + W - 1)
while q:
    p = q.popleft()
    if bg[p]: continue
    i = p * 3; r, g, b = raw[i], raw[i + 1], raw[i + 2]
    if min(r, g, b) < WHITE or max(r, g, b) - min(r, g, b) > 18: continue
    bg[p] = 1
    x, y = p % W, p // W
    if x > 0: q.append(p - 1)
    if x < W - 1: q.append(p + 1)
    if y > 0: q.append(p - W)
    if y < H - 1: q.append(p + W)

# 部件围住的纯白洞（弓和弦之间、两腿之间）：从边上漫不进去，单独找出来当背景。第 5 个参数是洞至少多少像素，0 = 不找
HOLE = int(sys.argv[5]) if len(sys.argv) > 5 else 0
if HOLE:
    seen = bytearray(W * H)
    for p0 in range(W * H):
        if bg[p0] or seen[p0]: continue
        i = p0 * 3
        if min(raw[i:i + 3]) < 243 or max(raw[i:i + 3]) - min(raw[i:i + 3]) > 8: continue
        seen[p0] = 1; st = [p0]; reg = []
        while st:
            p = st.pop(); reg.append(p); x = p % W
            for nb in ((p - 1) if x > 0 else -1, (p + 1) if x < W - 1 else -1, p - W, p + W):
                if 0 <= nb < W * H and not bg[nb] and not seen[nb]:
                    j = nb * 3
                    if min(raw[j:j + 3]) >= 236 and max(raw[j:j + 3]) - min(raw[j:j + 3]) <= 12: seen[nb] = 1; st.append(nb)
        if len(reg) >= HOLE:
            for p in reg: bg[p] = 1

# 连通块
lab = [0] * (W * H); comps = []
for p0 in range(W * H):
    if bg[p0] or lab[p0]: continue
    n = len(comps) + 1; lab[p0] = n; st = [p0]; x0 = x1 = p0 % W; y0 = y1 = p0 // W; area = 0
    while st:
        p = st.pop(); area += 1; x, y = p % W, p // W
        x0 = min(x0, x); x1 = max(x1, x); y0 = min(y0, y); y1 = max(y1, y)
        for nb in ((p - 1) if x > 0 else -1, (p + 1) if x < W - 1 else -1, (p - W) if y > 0 else -1, (p + W) if y < H - 1 else -1):
            if nb >= 0 and not bg[nb] and not lab[nb]: lab[nb] = n; st.append(nb)
    comps.append((n, x0, y0, x1, y1, area))
comps = [c for c in comps if c[5] >= min_area]
comps.sort(key=lambda c: (c[2] // 60, c[1]))

def write_png(path, w, h, rgba):
    rows = b"".join(b"\0" + bytes(rgba[y * w * 4:(y + 1) * w * 4]) for y in range(h))
    ch = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + ch(b"IDAT", zlib.compress(rows, 9)) + ch(b"IEND", b""))

pad = 2
for k, (n, x0, y0, x1, y1, area) in enumerate(comps, 1):
    x0 = max(0, x0 - pad); y0 = max(0, y0 - pad); x1 = min(W - 1, x1 + pad); y1 = min(H - 1, y1 + pad)
    w, h = x1 - x0 + 1, y1 - y0 + 1
    rgba = bytearray(w * h * 4)
    for yy in range(h):
        for xx in range(w):
            p = (y0 + yy) * W + (x0 + xx); i = p * 3; o = (yy * w + xx) * 4
            rgba[o:o + 3] = raw[i:i + 3]
            if lab[p] == n: a = 255
            elif bg[p]:
                # 背景里离部件很近、又不是纯白的像素（抗锯齿的边）留一点半透明
                a = max(0, min(255, int((250 - whiteness(i)) * 255 / 40)))
                near = any(0 <= (p + d) < W * H and lab[p + d] == n for d in (-1, 1, -W, W))
                a = a if near else 0
            else: a = 0
            rgba[o + 3] = a
    write_png(out / f"{k:02d}.png", w, h, rgba)
    print(f"{k:02d}  位置 ({x0},{y0})  大小 {w}×{h}")

# 带编号的预览
vf = ["scale=1280:-1"]
for k, (n, x0, y0, x1, y1, a) in enumerate(comps, 1):
    vf.append(f"drawbox=x={x0 // 2}:y={y0 // 2}:w={(x1 - x0) // 2}:h={(y1 - y0) // 2}:c=red@0.6:t=2")
    vf.append(f"drawtext=text='{k}':x={x0 // 2 + 4}:y={y0 // 2 + 2}:fontsize=22:fontcolor=red:borderw=3:bordercolor=white")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-vf", ",".join(vf), "-q:v", "3", str(out / "_index.jpg")], check=True)
