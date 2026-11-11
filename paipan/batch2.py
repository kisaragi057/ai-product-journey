"""
paipan/batch2.py —— 结构化数据 v2（Day 16）

和 batch.py（v1）的区别，以及为什么新开一个文件而不是改它：
  · v1 的 schema 只有「五行 5 列」，v2 要拆成「五行 × 阴阳」10 列，还分本气/藏干两个口径。
  · schema 变了就不要悄悄覆盖旧文件 —— v1 那份还得让 Day 15 的 notebook 能重跑。
    （Day 15 的错题 #50 就是这个：生成物被无备份覆盖，昨天的练习就演不成了。）
  · 产出三个文件，全在 paipan/data/ 下，都被 .gitignore 挡住（*.csv），不进仓库：
      charts_v2.csv      7305 行，32 列，含「时间未知」的样本
      zhi_canggan.csv    12 行对照表，专门用来在 pandas 里练 merge

两个统计口径（这是产品口径，不是技术问题）：
  A 本气版：四天干 + 四地支本气 = 恒 8 个字
  B 藏干版：四天干 + 地支全部藏干 = 12~15 个字，随月份变

运行：
    .venv/bin/python paipan/batch2.py
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from core import (GAN_WX, ZHI, ZHI_CANGGAN, ZHI_WX, compute_pillars,
                  count_wx, is_yang, shichen_of)

START = datetime(1960, 1, 1)
# 窗口取 60 年（1960-01-01 ~ 2019-12-31），不是 20 年。
# 理由见错题 #65：年柱 60 一个甲子循环，20 年 ÷ 12 不整除会让年支分布有偏
# （实测 2000-2019 那 20 个年柱里 11 个本气为阳 → 年支本气阳率 0.5449，7.4σ）。
# 60 年 = 恰好 1 个完整甲子循环：每个年柱出现且仅出现一次，年支、年干同时归匀。
# 顺带这也更贴合真实用户：1960-2019 覆盖 6-66 岁，比只取 2000-2019 合理。
DAYS = 21915                      # 60 年，含 15 个闰年
OUT_DIR = Path(__file__).parent / "data"
KU = {"未": "木", "戌": "火", "丑": "金", "辰": "水"}   # 四库（已用十二长生实测核对）

WX_KEY = {"木": "mu", "火": "huo", "土": "tu", "金": "jin", "水": "shui"}
YY_KEY = {"阳": "yang", "阴": "yin"}
PAIRS = [(w, y) for w in "木火土金水" for y in "阳阴"]

# 列名 ↔ (五行, 阴阳) 用一张对照表绑死，不靠字符串切片猜（猜一次就错一次，见下方 A_PAIRS 注释）
A_PAIRS = [(f"a_{WX_KEY[w]}_{YY_KEY[y]}", w, y) for w, y in PAIRS]
B_PAIRS = [(f"b_{WX_KEY[w]}_{YY_KEY[y]}", w, y) for w, y in PAIRS]
A_COLS = [c for c, _, _ in A_PAIRS]
B_COLS = [c for c, _, _ in B_PAIRS]

FIELDS = (["date", "weekday", "hour", "minute", "shichen", "time_unknown",
           "year_pillar", "month_pillar", "day_pillar", "hour_pillar",
           "day_master", "day_master_wx", "day_master_yy",
           "day_zhi", "day_zhi_wx", "day_zhi_shixing_yy", "day_zhi_benqi", "day_zhi_ku"]
          + A_COLS + B_COLS + ["a_total", "b_total"])


def make_reference():
    """12 行地支对照表。它是 core 那张表的「导出物」，不是第二份真相 ——
    只从 ZHI_CANGGAN 生成，不许手写第二遍。"""
    rows = []
    for z in ZHI:
        hidden = ZHI_CANGGAN[z]
        rows.append({
            "zhi": z,
            "wx": ZHI_WX[z],
            "benqi": hidden[0],
            "benqi_wx": GAN_WX[hidden[0]],
            "benqi_yy": "阳" if is_yang(hidden[0]) else "阴",
            "shixing_yy": "阳" if ZHI.index(z) % 2 == 0 else "阴",
            "hidden_count": len(hidden),
            "hidden_join": "|".join(hidden),
            "ku_of": KU.get(z, "无"),
        })
        assert rows[-1]["benqi_wx"] == rows[-1]["wx"], f"{z} 本气五行和支本身的五行不一致"
    return rows


def make_rows():
    rng = random.Random(20261103)
    rows = []
    for i in range(DAYS):
        d = START + timedelta(days=i)
        # 「时间未知」用随机数抽，不用 i 取模。
        # 我第一版写的是 i % 15 == 7，看着挺公平，实际 15 和天干周期 10 有公因子 5 ——
        # 抽出来的 487 行只覆盖 10 个日主里的几个，groupby 一算就歪。
        # 这是 Day 15 错题 #52 的【原样重犯】，只是这次躲在抽样里。
        unknown = rng.random() < 0.067
        dt = d.replace(hour=12, minute=0) if unknown else d.replace(
            hour=rng.randrange(24), minute=rng.randrange(60))

        pillars = compute_pillars(dt)
        if unknown:
            # 时辰不知道 → 时柱只能空着，三柱排盘。五行也就只有 6 个字。
            pillars = pillars[:3]
            used = dt                                   # 日柱按当天中午取（不假装知道时辰）
        else:
            used = dt

        a = count_wx(pillars, hidden=False)
        b = count_wx(pillars, hidden=True)
        day = pillars[2]
        row = {
            "date": f"{dt:%Y-%m-%d}",
            "weekday": dt.weekday(),
            "hour": "" if unknown else dt.hour,
            "minute": "" if unknown else dt.minute,
            "shichen": "" if unknown else shichen_of(dt.hour),
            "time_unknown": 1 if unknown else 0,
            "year_pillar": pillars[0], "month_pillar": pillars[1],
            "day_pillar": day,
            "hour_pillar": pillars[3] if len(pillars) > 3 else "**",
            "day_master": day[0], "day_master_wx": GAN_WX[day[0]],
            "day_master_yy": "阳" if is_yang(day[0]) else "阴",
            "day_zhi": day[1], "day_zhi_wx": ZHI_WX[day[1]],
            "day_zhi_shixing_yy": "阳" if ZHI.index(day[1]) % 2 == 0 else "阴",
            "day_zhi_benqi": ZHI_CANGGAN[day[1]][0],
            "day_zhi_ku": KU.get(day[1], "无"),
            "a_total": sum(a.values()), "b_total": sum(b.values()),
        }
        for c, w, y in A_PAIRS:
            row[c] = a.get(w + y, 0)
        for c, w, y in B_PAIRS:
            row[c] = b.get(w + y, 0)
        rows.append(row)
    return rows


if __name__ == "__main__":
    import time
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ref = make_reference()
    with open(OUT_DIR / "zhi_canggan.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ref[0].keys()))
        w.writeheader(); w.writerows(ref)

    rows = make_rows()
    with open(OUT_DIR / "charts_v2.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader(); w.writerows(rows)

    unk = sum(r["time_unknown"] for r in rows)
    clash = sum(1 for r in rows if r["day_zhi_shixing_yy"] !=
                ("阳" if is_yang(r["day_zhi_benqi"]) else "阴"))
    print(f"写出 charts_v2.csv {len(rows)} 行 × {len(FIELDS)} 列，zhi_canggan.csv {len(ref)} 行")
    print(f"耗时 {time.time()-t0:.1f} 秒｜时间未知 {unk} 行（{unk/len(rows)*100:.1f}%）")
    print(f"a_total 取值：{sorted({r['a_total'] for r in rows})}｜"
          f"b_total 取值：{sorted({r['b_total'] for r in rows})}")
    ku_n = sum(1 for r in rows if r["day_zhi_ku"] != "无")
    print(f"四库（日支为辰戌丑未）的行数：{ku_n}｜{ku_n/len(rows)*100:.1f}%"
          f"（4/12 = 33.3%，对得上说明抽样没有偏向四季土）")
    print(f"「支性阴阳 ≠ 本气阴阳」的行数：{clash}｜占 {clash/len(rows)*100:.1f}%"
          f"（子午巳亥四个支，理论上约 4/12 = 33.3%）")
    bad = [r for r in rows if r["day_zhi_shixing_yy"] != ("阳" if ZHI.index(r["day_zhi"]) % 2 == 0 else "阴")]
    print(f"自检：支性算法与导出值不一致的行 {len(bad)}")
