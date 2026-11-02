"""
paipan/batch.py —— 把排盘从「一次一个」变成「一次七千个」（Day 15）

为什么要这个文件？三个产品理由，不是练手：
  1. 你要给别人用。别人问「2000 年出生的属龙的有哪些日主」，你不可能手点网页。
  2. 分布本身是免费的正确性检查器。日柱在连续日子里必须严格轮转 60 天一圈，
     只要某一列的数量明显不均，算法或解析就一定有 bug —— 一行代码都还没读。
  3. 接大模型做解读需要语料/测试集。今天这批 CSV 就是明天的输入。

产出：paipan/data/charts.csv（7305 行，2000-01-01 ~ 2019-12-31，每天一条）
      这个文件被 .gitignore 挡住了（*.csv），不会提交 —— 数据不是代码。

运行：
    .venv/bin/python paipan/batch.py
"""

import csv
import random
from pathlib import Path
from datetime import datetime, timedelta

from core import compute_pillars, shichen_of, wuxing_count, GAN_WX

START = datetime(2000, 1, 1)     # 含
DAYS = 7305                       # 20 年 = 7305 天（2000~2019，其中 5 个闰年）
OUT = Path(__file__).parent / "data" / "charts.csv"

FIELDS = ["date", "weekday", "hour", "minute", "shichen",
          "year_pillar", "month_pillar", "day_pillar", "hour_pillar",
          "day_master", "day_master_wx",
          "mu", "huo", "tu", "jin", "shui", "early_zi"]


def make_rows():
    rows = []
    rng = random.Random(20261102)
    for i in range(DAYS):
        d = START + timedelta(days=i)
        # 时刻用带种子的随机数铺满 0-23 点，23 点这个边界自然会被扫到。
        # 关键是它跟日期序号没有任何数学关系，不会跟天干/地支的周期咬合。
        dt = (d.replace(hour=rng.randrange(24), minute=rng.randrange(60)))
        pillars = compute_pillars(dt)
        wx = wuxing_count(pillars)
        assert sum(wx.values()) == 8, f"{dt} 五行加起来不是 8：{wx}"
        rows.append({
            "date": f"{dt:%Y-%m-%d}",
            "weekday": dt.weekday(),                    # 0=周一，6=周日
            "hour": dt.hour,
            "minute": dt.minute,
            "shichen": shichen_of(dt.hour),
            "year_pillar": pillars[0],
            "month_pillar": pillars[1],
            "day_pillar": pillars[2],
            "hour_pillar": pillars[3],
            "day_master": pillars[2][0],                # 日主 = 日柱天干，八字里最关键的一个字
            "day_master_wx": GAN_WX[pillars[2][0]],
            "mu": wx.get("木", 0), "huo": wx.get("火", 0), "tu": wx.get("土", 0),
            "jin": wx.get("金", 0), "shui": wx.get("水", 0),
            "early_zi": 1 if dt.hour >= 23 else 0,      # 这条走了「早子时→次日」规则
        })
    return rows


if __name__ == "__main__":
    import time
    t0 = time.time()
    rows = make_rows()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig = 带 BOM 的 UTF-8。不加 BOM，Excel 双击打开必变乱码（Word/Mac 没事，Excel 有事）。
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"写出 {len(rows)} 行 → {OUT.relative_to(OUT.parents[2])}")
    print(f"耗时 {time.time() - t0:.1f} 秒｜走早子时规则的有 {sum(r['early_zi'] for r in rows)} 行")
    print(f"第一行 {rows[0]['date']} {rows[0]['hour']:02d}:{rows[0]['minute']:02d} → "
          f"{rows[0]['year_pillar']} {rows[0]['month_pillar']} {rows[0]['day_pillar']} {rows[0]['hour_pillar']}")
    print(f"最后一行 {rows[-1]['date']} → {rows[-1]['day_pillar']}")
