"""把 dem.py 取回来的真实地形转成游戏用的：每格高度（层）+ 主要河流折线，写进 index.html 的 DEM 表。
用法：python3 tools/terrain/embed.py
每张图的参数在下面 CFG：step = 多少米算一层；rivers = 要哪几条河（名字: 半宽格数），水库、水渠这些后来才有的不要。
转换：每一行取低处（第 8 百分位）当谷底，沿行抹平，高出谷底的部分 ÷ step 就是层数；抹一遍 3×3；不到 0.12 层的算平地；2.2 层以上是上不去的山。"""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
CFG = {   # rivers：名字: (半宽格数, 深不深)。小河按浅水算，能蹚
  'wuzhang': dict(step=110, rivers={'渭河': (2.6, 1), '石头河': (1.2, 0), '麦李河': (1.0, 0)}),
  'jieting': dict(step=110, rivers={'马家河': (1.2, 0)}),
  'dingjun': dict(step=120, rivers={'汉江': (2.6, 1), '漾水河': (1.2, 0)}),
  'yiling':  dict(step=60,  rivers={'长江': (4.0, 1)}),
  'hulao':   dict(step=45,  rivers={'黄河': (5.0, 1), '汜河': (1.2, 0)}),
}
def conv(name, step, rivers, margin=10):
    d = json.load(open(os.path.join(HERE, 'out', name + '.json'))); E = d['elev']; R, C = len(E), len(E[0])
    base = [sorted(r)[int(C * 0.08)] for r in E]
    base = [sum(base[max(0, i - 8):i + 9]) / len(base[max(0, i - 8):i + 9]) for i in range(R)]
    h = [[max(0, (E[r][c] - base[r] - margin) / step) for c in range(C)] for r in range(R)]
    g = [[sum(h[rr][cc] for rr in range(max(0, r - 1), min(R, r + 2)) for cc in range(max(0, c - 1), min(C, c + 2))) / ((min(R, r + 2) - max(0, r - 1)) * (min(C, c + 2) - max(0, c - 1))) for c in range(C)] for r in range(R)]
    s = ''.join(chr(48 + (0 if v < 0.12 else min(24, round(v * 10)))) for row in g for v in row)
    rv = []
    for w in d['water']:
        if w['kind'] != 'river' or w['name'] not in rivers: continue
        pts = []
        for x, y in w['pts']:
            if -6 <= x <= C + 6 and -6 <= y <= R + 6 and (not pts or abs(x - pts[-1][0]) + abs(y - pts[-1][1]) >= 1.5): pts.append([round(x, 1), round(y, 1)])
        if len(pts) > 1: rv.append([rivers[w['name']][0], rivers[w['name']][1], pts])
    return {'h': s, 'rivers': rv, 'cell': d['cell_m'], 'lat': d['lat'], 'lon': d['lon'], 'rot': d['rot']}
out = {n: conv(n, **c) for n, c in CFG.items()}
js = '// ==DEM 开始：真实地形（tools/terrain/embed.py 生成，别手改）==\nconst DEM = ' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';\n// ==DEM 结束==\n'
p = os.path.join(ROOT, 'index.html'); s = open(p, encoding='utf-8').read()
if '// ==DEM 开始' in s: s = re.sub(r'// ==DEM 开始.*?// ==DEM 结束==\n', lambda m: js, s, flags=re.S)
else: s = s.replace('const MAPS = [', js + 'const MAPS = [', 1)
open(p, 'w', encoding='utf-8').write(s); print({n: (len(v['h']), len(v['rivers'])) for n, v in out.items()}, len(js))
