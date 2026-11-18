"""画阵：小兵各动作的视频提示词（火山 Seedance，图生视频，之后抽帧抠图）。
用法：python3 tools/art/video_jobs.py 任务名...   —— 生成到 art/raw/video/<任务名>/
"""
import concurrent.futures as cf, subprocess, sys

TAIL = "背景从头到尾都是纯白色，没有地面、没有阴影、没有任何其他东西；镜头完全固定不动，不推拉不平移；角色始终完整地在画面中间，大小不变，画面里只有这一个角色，不要出现任何特效和文字。"
WHO = "Q版卡通游戏角色动画。这个三国弓兵小兵四分之三侧面朝右，始终朝着这个方向，不转身、不回头。"
# 任务名: (用哪张图, 秒数, 动作)。图必须先垫成正方形、四周留白（sq.png）：视频是 1:1，竖长的图会被裁掉头和脚
JOBS = {
    "bow_ui_idle": ("art/cut/bow_ui/sq.png", 4, "原地待命：保持拉着弓瞄准的姿势，轻微的呼吸起伏，身体微微上下动，偶尔眨一下眼，盔缨和领巾轻轻飘动。动作很小很平稳，结尾和开头的姿势一样，可以无缝循环。"),
    "bow_ui_shoot": ("art/cut/bow_ui/sq.png", 4, "射箭：先把弓弦再往后拉满，然后松手，把箭向右方射出去，弓弦弹回、身体跟着一震；接着从背后的箭袋里抽出一支新箭搭在弦上重新拉开，回到和视频开头完全一样的姿势。只射一箭，动作干脆。"),
    "bow_ui_cheer": ("art/cut/bow_ui/sq.png", 4, "胜利欢呼：把弓高高举过头顶，开心地原地蹦跳两下，表情得意地笑，然后放下弓，重新拉开，回到和视频开头完全一样的姿势。"),
}

def run(name):
    pic, dur, act = JOBS[name]
    r = subprocess.run([sys.executable, "-I", "tools/art/gen_video.py", pic, f"art/raw/video/{name}", WHO + act + TAIL,
                        "--model", "doubao-seedance-1-0-pro-fast-251015", "--dur", str(dur)], capture_output=True, text=True)
    return f"{name}: " + ((r.stdout.strip().splitlines() or [""])[-1][:140] if r.returncode == 0 else r.stderr.strip()[-400:])

if __name__ == "__main__":
    with cf.ThreadPoolExecutor(4) as ex:
        for line in ex.map(run, sys.argv[1:] or list(JOBS)): print(line, flush=True)
