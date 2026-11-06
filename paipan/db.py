"""
paipan/db.py —— 排盘记录存进 SQLite（Day 18：数据库与 SQL 基础）

为什么这里要一个数据库，而不是接着用 CSV？两者根本不是一回事：

  charts_v2.csv  = 批量【样本】，7305 行机器生成，只读、整体重写、没人改单行
  charts 表      = 用户【记录】，一条条插进去、要按人查、要改要删、要多人同时写

  数据库给你的三样 CSV/JSON 给不了的：
    1. 查询：`WHERE name=? ORDER BY created_at DESC LIMIT 1` —— 不用把整个文件读进内存
    2. 并发：两个人同时排盘不会互相覆盖（CSV 同写＝其中一个丢了）
    3. 约束：字段类型、非空、主键，写错了当场拒绝你，而不是留着三个月后炸

★ 本文件最重要的一条设计决定：口径（sect）必须一起存。
  同一个生日，早子时派和夜子时派给出的日柱【不一样】（Day 17 实测过）。
  历史记录如果只存「此人生于 2000-10-15，日柱丁未」，
  等哪天你改口径，这批记录就变成了无法解释的谜题——你不知道它是哪个口径算的。
  存了口径，任何一行记录都能被重新验算。这是数据的可复现性，不是洁癖。

运行（建库 + 自检）：
    .venv/bin/python paipan/db.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "charts.db"

# ── 表结构：先写在这里，再建表。DDL 是设计，不是副产品 ──
SCHEMA = """
CREATE TABLE IF NOT EXISTS charts (
    id           INTEGER PRIMARY KEY,          -- 自增主键，每行一个身份证
    name         TEXT    NOT NULL DEFAULT '',  -- 允许空串（匿名），但不许 NULL
    gender       TEXT    NOT NULL CHECK (gender IN ('男','女')),
    birth_date   TEXT    NOT NULL,             -- 'YYYY-MM-DD'，ISO 格式才能直接比大小排序
    birth_time   TEXT,                         -- 可为 NULL = 时辰未知（NULL 就是「不知道」，不是「无」）
    time_known   INTEGER NOT NULL DEFAULT 1,   -- SQLite 没有布尔，0/1 是约定俗成
    year_pillar  TEXT    NOT NULL,
    month_pillar TEXT    NOT NULL,
    day_pillar   TEXT    NOT NULL,
    hour_pillar  TEXT,
    day_master   TEXT    NOT NULL,             -- 日主，查询最常用来筛的那个字
    sect         INTEGER NOT NULL,             -- ★ 口径：1=早子时派。不存它，这行无法复现
    created_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_charts_name ON charts(name, created_at);
"""


def connect():
    """打开连接。数据库文件不存在就自动建——这就是 SQLite「零配置」的意思。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row          # 让查询结果能用列名取，而不是只能 r[3]
    return con


def init(con) -> None:
    """建表。生命周期归调用方管——这个函数不关连接。
    （我第一版写成 init(con=None) 里自己 connect 又自己 close，
     结果 main 拿到的 con 已经关了：Cannot operate on a closed database。
     一个函数要么拥有连接，要么不碰它，别 halfway。）"""
    con.executescript(SCHEMA)
    con.commit()


def save_chart(con, payload: dict) -> int:
    """把接口返回的那个 JSON 存成一行。

    注意：入参就是 build_payload 的返回值，字段一一对齐。
    这样接口和存储共用同一份结构——两处各定义一遍字段，早晚会漂（Day 17 的 gender 教训）。
    """
    inp = payload["input"]
    p = payload["pillars"]
    cur = con.execute(
        """INSERT INTO charts (name, gender, birth_date, birth_time, time_known,
                               year_pillar, month_pillar, day_pillar, hour_pillar,
                               day_master, sect)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (inp["name"], inp["gender"], inp["date"], inp["time"],
         1 if inp["time_known"] else 0,
         p["year"], p["month"], p["day"], p["hour"],
         payload["day_master"]["gan"], payload["convention"]["sect"]),
    )
    con.commit()
    return cur.lastrowid


def latest_for(con, name: str, limit: int = 10):
    """按人查历史。参数化查询——字符串拼接是 SQL 注入的入口。"""
    # 排序用 id DESC 就够：id 是主键、唯一，所以顺序 100% 确定，
    # 而且 SQLite 倒着走主键即可，不用为 created_at 建 TEMP B-TREE（Day 18 实测）。
    # 只有当你要按【业务时间】排（回填历史记录、或以后加了 updated_at）时，
    # 才换成 created_at DESC, id DESC —— 注意第二列不可省，因为 created_at 不唯一。
    return con.execute(
        "SELECT * FROM charts WHERE name = ? ORDER BY id DESC LIMIT ?",
        (name, limit),
    ).fetchall()


def all_charts(con, limit: int = 50):
    return con.execute(
        "SELECT * FROM charts ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()


def stats(con):
    """聚合下推到数据库做。别把全表捞进 Python 再循环数——那是 CSV 的思路。"""
    return con.execute(
        """SELECT day_master, COUNT(*) AS n
           FROM charts GROUP BY day_master ORDER BY n DESC, day_master"""
    ).fetchall()


def row_to_dict(r):
    return {k: r[k] for k in r.keys()}


if __name__ == "__main__":
    import json
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from api import build_payload

    con = connect()
    init(con)
    con.execute("DELETE FROM charts")          # 自检用可复现库：每次从头开始
    con.commit()

    # ① 存三条：有时间的、时辰未知的、换个人的
    samples = [
        ("2000-10-15", "23:30", "林测试", "男"),
        ("2000-10-15", None, "林测试", "男"),      # 同一天，时辰未知
        ("1988-03-20", "07:15", "陈测试", "女"),
    ]
    ids = []
    for date_s, time_s, name, gender in samples:
        payload = build_payload(date_s, time_s, name, gender)
        ids.append(save_chart(con, payload))
    print("插入 3 行，自增 id =", ids)

    # ② 关键点：同一天有时辰 / 无时辰，日柱不同 —— 这两行都存下来了
    rows = latest_for(con, "林测试")
    print("\n按名字查『林测试』（新的在前）：")
    for r in rows:
        print(f"  {r['birth_date']} {str(r['birth_time']):>6}｜日柱 {r['day_pillar']}"
              f"｜time_known={r['time_known']}｜口径 sect={r['sect']}｜{r['created_at']}")
    assert {x["day_pillar"] for x in rows} == {"丁未", "丙午"}, "同一天的两种时辰应给出两个日柱"
    print("  ✅ 两种口径下的日柱都留痕了，且各自带 sect —— 这行数据三个月后还能解释")

    # ③ NULL 不是空串：时辰未知存的是 NULL
    n_null = con.execute("SELECT COUNT(*) FROM charts WHERE birth_time IS NULL").fetchone()[0]
    n_empty = con.execute("SELECT COUNT(*) FROM charts WHERE birth_time = ''").fetchone()[0]
    print(f"\nbirth_time IS NULL 的行: {n_null}｜= '' 的行: {n_empty}"
          f"（IS NULL 才能捞到，写 = NULL 永远返回 0 行——SQL 最经典的坑）")
    wrong = con.execute("SELECT COUNT(*) FROM charts WHERE birth_time = NULL").fetchone()[0]
    print(f"  演示：WHERE birth_time = NULL 命中 {wrong} 行 ← 看着对，永远查不到东西")

    # ④ CHECK 约束：写进非法性别应被数据库当场拒绝
    try:
        con.execute("INSERT INTO charts (name,gender,birth_date,year_pillar,month_pillar,"
                    "day_pillar,day_master,sect) VALUES ('x','中','2000-01-01','a','b','c','d',1)")
        print("\n❌ CHECK 没生效，非法性别被收下了")
    except sqlite3.IntegrityError as e:
        print(f"\n✅ CHECK 约束拦住了非法值：{e}")

    # ⑤ 参数化查询：这就是为什么不能拼接字符串
    evil = "'; DROP TABLE charts; --"
    hit = latest_for(con, evil)
    alive = con.execute("SELECT COUNT(*) FROM charts").fetchone()[0]
    print(f"拿注入串当名字查：命中 {len(hit)} 行，表里还剩 {alive} 行 → 表活着 ✅")

    # ⑥ 聚合下推
    print("\n按日主聚合（GROUP BY 在数据库里做）：")
    print("  " + "，".join(f"{s['day_master']} {s['n']}" for s in stats(con)))

    con.close()
    print(f"\n库文件：{DB_PATH}（{DB_PATH.stat().st_size} 字节，被 .gitignore 的 data/ 挡住，不进仓库）")
