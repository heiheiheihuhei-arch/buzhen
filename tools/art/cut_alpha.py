"""把透明底的素材表（Seedream 5.5 直接出的 RGBA 图）按连通块切开，拼成一张等格图集。
用法：python3 tools/art/cut_alpha.py 素材表.png 输出.webp 每行几个 格子边长
小碎块（石子、草屑）并到最近的大块里。按从上到下、从左到右排号。打印每块缩放后的 [宽, 高]，游戏里按这个取图。
"""
import subprocess, sys, json, pathlib, tempfile
src, out, per, cell = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", src], capture_output=True, text=True).stdout.strip().split(",")
W, H = int(probe[0]), int(probe[1]); K = 4; w, h = W // K, H // K
a = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-vf", f"alphaextract,scale={w}:{h}:flags=area", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
seen = bytearray(w * h); boxes = []
for s in range(w * h):
    if a[s] < 40 or seen[s]: continue
    st = [s]; seen[s] = 1; x0 = x1 = s % w; y0 = y1 = s // w; n = 0
    while st:
        p = st.pop(); n += 1; x, y = p % w, p // w
        x0 = min(x0, x); x1 = max(x1, x); y0 = min(y0, y); y1 = max(y1, y)
        for q in (p - 1 if x else -1, p + 1 if x < w - 1 else -1, p - w, p + w):
            if 0 <= q < w * h and not seen[q] and a[q] >= 40: seen[q] = 1; st.append(q)
    boxes.append([x0, y0, x1, y1, n])
big = [b for b in boxes if b[4] >= 900]
for b in boxes:
    if b[4] >= 900: continue
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    t = min(big, key=lambda g: max(g[0] - cx, cx - g[2], 0) + max(g[1] - cy, cy - g[3], 0))
    t[0] = min(t[0], b[0]); t[1] = min(t[1], b[1]); t[2] = max(t[2], b[2]); t[3] = max(t[3], b[3])
big.sort(key=lambda b: (round((b[1] + b[3]) / 2 / (h / 3.2)), b[0]))
tmp = pathlib.Path(tempfile.mkdtemp()); sizes = []; ins = []; flt = []
rows = -(-len(big) // per)
for i, b in enumerate(big):
    x, y, bw, bh = b[0] * K - 4, b[1] * K - 4, (b[2] - b[0] + 1) * K + 8, (b[3] - b[1] + 1) * K + 8
    s = min((cell - 4) / bw, (cell - 4) / bh); pw, ph = round(bw * s), round(bh * s); sizes.append([pw, ph])
    f = tmp / f"{i}.png"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-vf", f"crop={bw}:{bh}:{max(0,x)}:{max(0,y)},scale={pw}:{ph}:flags=lanczos", str(f)], check=True)
    ins += ["-i", str(f)]
    ox, oy = (i % per) * cell + (cell - pw) // 2, (i // per) * cell + cell - ph
    flt.append(f"[{'bg' if i == 0 else 'o' + str(i - 1)}][{i + 1}]overlay={ox}:{oy}[o{i}]")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"color=c=black@0:s={per * cell}x{rows * cell},format=rgba", *ins,
                "-filter_complex", "[0]copy[bg];" + ";".join(flt), "-map", f"[o{len(big) - 1}]", "-frames:v", "1", "-c:v", "libwebp", "-quality", "88", out], check=True)
print(json.dumps(sizes))
