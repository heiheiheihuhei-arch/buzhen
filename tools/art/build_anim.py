"""把火山出的动作视频变成游戏用的序列帧条：抽帧 → 抠掉白底 → 所有动作按同一个框裁齐 → 每个动作拼成一横条 webp。
用法：python3 tools/art/build_anim.py 兵种名 动作=视频.mp4 ...
例：  python3 tools/art/build_anim.py bow idle=art/raw/video/bow_ui_idle/video.mp4 shoot=...
输出：art/game/anim_<兵种>_<动作>.webp，并打印每条的帧数、单帧宽高（embed_figs.py 会读 art/game/anim.json）。
"""
import json, pathlib, struct, subprocess, sys, zlib
from collections import deque
BLEND = 3
SZ, STEP, OUT_H, HOLE = 400, 2, 170, 45      # 抽帧时缩到多大、每几帧取一帧（24 帧/秒取一半 = 12 帧/秒；取三分之一看着卡）、成品单帧高、白洞至少多少像素
root = pathlib.Path(__file__).resolve().parents[2]; unit = sys.argv[1]
def frames(video):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", video, "-vf", f"select='not(mod(n,{STEP}))',scale={SZ}:{SZ}:flags=lanczos", "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    n = len(raw) // (SZ * SZ * 3); return [raw[i * SZ * SZ * 3:(i + 1) * SZ * SZ * 3] for i in range(n)]
def matte(fr):
    """从四边往里漫水：接近白、不鲜艳的算背景。返回 rgba 和外接框"""
    bg = bytearray(SZ * SZ); q = deque()
    for x in range(SZ): q.append(x); q.append((SZ - 1) * SZ + x)
    for y in range(SZ): q.append(y * SZ); q.append(y * SZ + SZ - 1)
    while q:
        p = q.popleft()
        if bg[p]: continue
        i = p * 3; r, g, b = fr[i], fr[i + 1], fr[i + 2]; lo = min(r, g, b)
        if lo < 222 or max(r, g, b) - lo > 16: continue
        bg[p] = 1; x = p % SZ
        if x > 0: q.append(p - 1)
        if x < SZ - 1: q.append(p + 1)
        if p >= SZ: q.append(p - SZ)
        if p < SZ * (SZ - 1): q.append(p + SZ)
    # 被人围住的白洞（弓和弦之间、胳膊和身体之间）：边上漫不进去，单独找；小于 HOLE 像素的不动（眼白、牙）
    seen = bytearray(SZ * SZ)
    for p0 in range(SZ * SZ):
        if bg[p0] or seen[p0]: continue
        i = p0 * 3; lo = min(fr[i:i + 3])
        if lo < 232 or max(fr[i:i + 3]) - lo > 12: continue
        seen[p0] = 1; st = [p0]; reg = []
        while st:
            p = st.pop(); reg.append(p); x = p % SZ
            for nb in ((p - 1) if x > 0 else -1, (p + 1) if x < SZ - 1 else -1, p - SZ, p + SZ):
                if 0 <= nb < SZ * SZ and not bg[nb] and not seen[nb]:
                    j = nb * 3; l2 = min(fr[j:j + 3])
                    if l2 >= 226 and max(fr[j:j + 3]) - l2 <= 14: seen[nb] = 1; st.append(nb)
        if len(reg) >= HOLE:
            for p in reg: bg[p] = 1
    rgba = bytearray(SZ * SZ * 4); x0, y0, x1, y1 = SZ, SZ, 0, 0
    for p in range(SZ * SZ):
        i = p * 3; o = p * 4; rgba[o:o + 3] = fr[i:i + 3]
        if not bg[p]:
            rgba[o + 3] = 255; x = p % SZ; y = p // SZ
            if x < x0: x0 = x
            if x > x1: x1 = x
            if y < y0: y0 = y
            if y > y1: y1 = y
        else:
            x = p % SZ   # 贴着人的背景像素留一点半透明，边缘不发硬
            near = (x > 0 and not bg[p - 1]) or (x < SZ - 1 and not bg[p + 1]) or (p >= SZ and not bg[p - SZ]) or (p < SZ * (SZ - 1) and not bg[p + SZ])
            rgba[o + 3] = max(0, min(255, (248 - min(fr[i:i + 3])) * 6)) if near else 0
    return rgba, (x0, y0, x1, y1)
def png(path, w, h, rgba):
    rows = b"".join(b"\0" + bytes(rgba[y * w * 4:(y + 1) * w * 4]) for y in range(h))
    ch = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + ch(b"IDAT", zlib.compress(rows, 6)) + ch(b"IEND", b""))
acts = {}; box = [SZ, SZ, 0, 0]
for arg in sys.argv[2:]:
    name, video = arg.split("=", 1); fs = frames(video)
    # 循环接缝：视频最后一帧常常回不到开头的姿势，循环时会跳一下。在后四成里找和第一帧最像的那帧收尾，再把末尾 BLEND 帧渐变回第一帧
    def dist(a, b): return sum(abs(a[i] - b[i]) for i in range(0, len(a), 37))
    lo = int(len(fs) * 0.6); end = min(range(lo, len(fs)), key=lambda k: dist(fs[k], fs[0])); print(name, "原", len(fs), "帧，收在第", end + 1, "帧，接缝差", dist(fs[end], fs[0]) // 1000, "（最后一帧是", dist(fs[-1], fs[0]) // 1000, "）")
    ms = [matte(f) for f in fs[:end + 1]]
    for j in range(1, BLEND + 1):
        t = 1 - j / (BLEND + 1); src, tgt = ms[len(ms) - j][0], ms[0][0]   # 倒数第 j 帧，越靠后越接近第一帧
        ms[len(ms) - j] = (bytearray(round(src[i] * (1 - t) + tgt[i] * t) for i in range(len(src))), ms[len(ms) - j][1])
    acts[name] = ms
    for _, (a, b, c, d) in acts[name]: box = [min(box[0], a), min(box[1], b), max(box[2], c), max(box[3], d)]
x0, y0, x1, y1 = max(0, box[0] - 2), max(0, box[1] - 2), min(SZ - 1, box[2] + 2), min(SZ - 1, box[3] + 2); w, h = x1 - x0 + 1, y1 - y0 + 1
meta_path = root / "art" / "game" / "anim.json"; meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
tmp = root / "art" / "cut" / f"anim_{unit}"; tmp.mkdir(parents=True, exist_ok=True)
# 站位：拿第一个动作的第一帧，量出人的头顶、脚底和两脚中间的位置（占单帧的比例），游戏里靠它把脚对准落点、按人的身高定大小
r0 = next(iter(acts.values()))[0][0]; rows = [yy for yy in range(h) if any(r0[((y0 + yy) * SZ + x0 + xx) * 4 + 3] > 128 for xx in range(w))]
top, bot = rows[0], rows[-1]; foot = [xx for yy in range(bot - max(2, (bot - top) // 14), bot + 1) for xx in range(w) if r0[((y0 + yy) * SZ + x0 + xx) * 4 + 3] > 128]
anchor = {"top": round(top / h, 3), "bot": round((bot + 1) / h, 3), "fx": round((min(foot) + max(foot)) / 2 / w, 3)}; print("站位", anchor)
for name, fs in acts.items():
    n = len(fs); strip = bytearray(w * n * h * 4)
    for k, (rgba, _) in enumerate(fs):
        for yy in range(h):
            src = ((y0 + yy) * SZ + x0) * 4; dst = (yy * w * n + k * w) * 4; strip[dst:dst + w * 4] = rgba[src:src + w * 4]
    p = tmp / f"{name}.png"; png(p, w * n, h, strip)
    fw = round(w * OUT_H / h); out = root / "art" / "game" / f"anim_{unit}_{name}.webp"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(p), "-vf", f"scale={fw * n}:{OUT_H}:flags=lanczos", str(tmp / f"{name}_s.png")], check=True)
    subprocess.run(["cwebp", "-quiet", "-q", "74", "-alpha_q", "85", str(tmp / f"{name}_s.png"), "-o", str(out)], check=True)
    meta[f"{unit}_{name}"] = {"n": n, "w": fw, "h": OUT_H, "fps": 24 // STEP, **anchor}
    print(name, "帧数", n, "单帧", fw, "x", OUT_H, "文件", out.stat().st_size // 1024, "KB")
meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
