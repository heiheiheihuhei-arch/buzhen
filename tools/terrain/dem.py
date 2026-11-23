"""取一块真实地形：公开高程瓦片（Terrarium，约 30 米一格）+ OpenStreetMap 的河流，裁成沙盘的格子（60×96，每格取平均高度）。
用法：python3 tools/terrain/dem.py 名字 纬度 经度 东西宽度公里 [转角度数]
  转角：把实地顺时针转多少度再裁（0 = 上北下南；180 = 上南下北），用来让敌军来的方向朝上。
输出：tools/terrain/out/名字.json（elev 每格海拔，water 河流折线，格子坐标）和 名字.png（预览）。
瓦片缓存在 tools/terrain/cache。只用标准库。"""
import json, math, os, struct, sys, urllib.request, urllib.parse, zlib
HERE = os.path.dirname(os.path.abspath(__file__)); CACHE = os.path.join(HERE, 'cache'); OUT = os.path.join(HERE, 'out')
COLS, ROWS, SUB, Z = 60, 96, 3, 12

def png_read(b):
    assert b[:8] == b'\x89PNG\r\n\x1a\n'; p = 8; idat = b''
    while p < len(b):
        n, t = struct.unpack('>I4s', b[p:p + 8]); d = b[p + 8:p + 8 + n]; p += 12 + n
        if t == b'IHDR': w, h, bd, ct = struct.unpack('>IIBB', d[:10]); assert bd == 8 and ct in (2, 6)
        elif t == b'IDAT': idat += d
    bpp = 3 if ct == 2 else 4; raw = zlib.decompress(idat); st = w * bpp; rows = []; prev = bytearray(st); q = 0
    for _ in range(h):
        f = raw[q]; cur = bytearray(raw[q + 1:q + 1 + st]); q += 1 + st
        for i in range(st):
            a = cur[i - bpp] if i >= bpp else 0; b2 = prev[i]; c = prev[i - bpp] if i >= bpp else 0
            if f == 1: cur[i] = (cur[i] + a) & 255
            elif f == 2: cur[i] = (cur[i] + b2) & 255
            elif f == 3: cur[i] = (cur[i] + (a + b2) // 2) & 255
            elif f == 4:
                pa, pb, pc = abs(b2 - c), abs(a - c), abs(a + b2 - 2 * c)
                cur[i] = (cur[i] + (a if pa <= pb and pa <= pc else b2 if pb <= pc else c)) & 255
        rows.append(cur); prev = cur
    return w, h, bpp, rows

def png_write(path, w, h, rgb):
    raw = b''.join(b'\x00' + bytes(rgb[y * w * 3:(y + 1) * w * 3]) for y in range(h))
    def ch(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + ch(b'IDAT', zlib.compress(raw, 6)) + ch(b'IEND', b''))

tiles = {}
def tile(x, y):
    if (x, y) not in tiles:
        f = os.path.join(CACHE, f'{Z}_{x}_{y}.png')
        if not os.path.exists(f):
            os.makedirs(CACHE, exist_ok=True)
            urllib.request.urlretrieve(f'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{Z}/{x}/{y}.png', f)
        tiles[(x, y)] = png_read(open(f, 'rb').read())
    return tiles[(x, y)]
def elev(lat, lon):
    n = 2 ** Z; fx = (lon + 180) / 360 * n; fy = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    w, h, bpp, rows = tile(int(fx), int(fy)); px = min(255, int((fx % 1) * 256)); py = min(255, int((fy % 1) * 256)); r = rows[py]
    return r[px * bpp] * 256 + r[px * bpp + 1] + r[px * bpp + 2] / 256 - 32768

def main():
    name, lat0, lon0, km = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]); rot = math.radians(float(sys.argv[5]) if len(sys.argv) > 5 else 0)
    cell = km / COLS; kx = 111.32 * math.cos(math.radians(lat0)); ky = 110.57
    def ll(c, r):   # 格子坐标 → 经纬度
        ex, ny = (c - COLS / 2) * cell, (ROWS / 2 - r) * cell
        e, n = ex * math.cos(rot) + ny * math.sin(rot), -ex * math.sin(rot) + ny * math.cos(rot)
        return lat0 + n / ky, lon0 + e / kx
    def cr(lat, lon):   # 经纬度 → 格子坐标
        e, n = (lon - lon0) * kx, (lat - lat0) * ky
        ex, ny = e * math.cos(rot) - n * math.sin(rot), e * math.sin(rot) + n * math.cos(rot)
        return ex / cell + COLS / 2, ROWS / 2 - ny / cell
    fine = [[elev(*ll((c + .5) / SUB, (r + .5) / SUB)) for c in range(COLS * SUB)] for r in range(ROWS * SUB)]
    grid = [[round(sum(fine[r * SUB + j][c * SUB + i] for j in range(SUB) for i in range(SUB)) / SUB / SUB, 1) for c in range(COLS)] for r in range(ROWS)]
    # 河流：OSM
    cs = [ll(c, r) for c in (-2, COLS + 2) for r in (-2, ROWS + 2)]; s, n, w, e = min(p[0] for p in cs), max(p[0] for p in cs), min(p[1] for p in cs), max(p[1] for p in cs)
    water = []
    try:
        q = f'[out:json][timeout:40];(way["waterway"~"river|stream|canal"]({s},{w},{n},{e});way["natural"="water"]({s},{w},{n},{e}););out geom;'
        els = None
        for host in ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter', 'https://overpass.private.coffee/api/interpreter', 'https://overpass-api.de/api/interpreter']:
            try:
                req = urllib.request.Request(host, data=urllib.parse.urlencode({'data': q}).encode(), headers={'User-Agent': 'terrain-research-script'})
                els = json.load(urllib.request.urlopen(req, timeout=60))['elements']; break
            except Exception as ex: print('  ', host.split('/')[2], ex)
        for el in els:
            t = el.get('tags', {}); pts = [[round(v, 2) for v in cr(g['lat'], g['lon'])] for g in el.get('geometry', [])]
            if len(pts) > 1 and any(-2 <= x <= COLS + 2 and -2 <= y <= ROWS + 2 for x, y in pts):
                water.append({'kind': t.get('waterway') or 'water', 'name': t.get('name', ''), 'pts': pts})
    except Exception as ex: print('河流没取到：', ex)
    os.makedirs(OUT, exist_ok=True)
    json.dump({'name': name, 'lat': lat0, 'lon': lon0, 'km': km, 'rot': math.degrees(rot), 'cell_m': round(cell * 1000), 'elev': grid, 'water': water}, open(os.path.join(OUT, name + '.json'), 'w'), ensure_ascii=False)
    # 预览：按海拔上色 + 山影，河流画蓝线
    K = 8 // SUB * SUB // SUB or 2; K = 3; W, H = COLS * SUB * K, ROWS * SUB * K; lo = min(map(min, fine)); hi = max(map(max, fine)); img = bytearray(W * H * 3)
    ramp = [(0, (196, 214, 150)), (.25, (226, 214, 160)), (.5, (200, 170, 120)), (.75, (150, 120, 95)), (1, (240, 240, 240))]
    for y in range(ROWS * SUB):
        for x in range(COLS * SUB):
            t = (fine[y][x] - lo) / max(1, hi - lo); k = max(i for i, (a, _) in enumerate(ramp) if a <= t); a, ca = ramp[k]; b, cb = ramp[min(k + 1, len(ramp) - 1)]; u = (t - a) / (b - a) if b > a else 0
            dzx = fine[y][min(x + 1, COLS * SUB - 1)] - fine[y][max(x - 1, 0)]; dzy = fine[min(y + 1, ROWS * SUB - 1)][x] - fine[max(y - 1, 0)][x]
            sh = max(.45, min(1.35, 1 - (dzx + dzy) / (cell * 1000 / SUB) * 1.2))
            col = [max(0, min(255, int((ca[i] + (cb[i] - ca[i]) * u) * sh))) for i in range(3)]
            for j in range(K):
                o = ((y * K + j) * W + x * K) * 3; img[o:o + 3 * K] = bytes(col) * K
    def dot(x, y, col, rad):
        for j in range(-rad, rad + 1):
            for i in range(-rad, rad + 1):
                X, Y = int(x) + i, int(y) + j
                if 0 <= X < W and 0 <= Y < H: o = (Y * W + X) * 3; img[o:o + 3] = bytes(col)
    for wv in water:
        rad = 3 if wv['kind'] == 'river' else 1; col = (40, 110, 200) if wv['kind'] != 'stream' else (90, 150, 215); P = wv['pts']
        for (x0, y0), (x1, y1) in zip(P, P[1:]):
            st = max(1, int(math.hypot(x1 - x0, y1 - y0) * SUB * K))
            for k in range(st + 1): dot((x0 + (x1 - x0) * k / st) * SUB * K, (y0 + (y1 - y0) * k / st) * SUB * K, col, rad)
    png_write(os.path.join(OUT, name + '.png'), W, H, img)
    print(f'{name}: 每格 {cell * 1000:.0f} 米，海拔 {lo:.0f}～{hi:.0f} 米，河流 {len(water)} 条：', sorted({w["name"] for w in water if w["name"]}))
main()
