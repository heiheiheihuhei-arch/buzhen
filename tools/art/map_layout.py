"""把地形高度表画成一张色块布局图，给出图模型当参考：照着这个布局画整张地面，画出来才和规则对得上。
用法：python3 tools/art/map_layout.py art/maps/test.json 输出.png [宽 高]
图覆盖整个沙盘（场地 + 四周 3 格外沿，外沿按最近的场内格子算）。黄 = 沙地，绿 = 台地，棕 = 坡。
"""
import json, subprocess, sys
d = json.load(open(sys.argv[1])); out = sys.argv[2]
OW, OH = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (1664, 2624)
C, R, H, MG = d["cols"], d["rows"], d["h"], 3
TC, TR = C + 2 * MG, R + 2 * MG
def col(h):
    if h >= 0.9: return (140, 172, 92)
    if h > 0.05: return (176, 142, 96)
    return (220, 190, 132)
buf = bytearray(OW * OH * 3)
for y in range(OH):
    r = min(R - 1, max(0, int(y * TR / OH) - MG)); row = bytearray()
    for x in range(OW):
        c = min(C - 1, max(0, int(x * TC / OW) - MG)); row += bytes(col(H[r * C + c]))
    buf[y * OW * 3:(y + 1) * OW * 3] = row
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-i", "-", out], input=bytes(buf), check=True)
print(out, OW, OH)
