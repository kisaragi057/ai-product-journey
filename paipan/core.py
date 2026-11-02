"""
paipan/core.py —— 排盘核心算法（Day 15 从 app.py 抽出来）

为什么要抽这一个文件？
  Day 13 的时候，排盘逻辑埋在 app.py 的 build_chart 里，和拼 HTML 字符串混在一起。
  今天 batch.py 要批量跑两万个生日，网页也要跑，命令行还要跑。
  如果三处各写一份算法，它们迟早会分叉：页面显示 A，分析数据算出 B。
  这种 bug 最难查——因为每一处「单独看都是对的」。
  所以立一条规矩：**一处算法，多处使用**（英文叫 single source of truth）。

这个文件里【不许】出现：HTML、print、文件读写、网络请求。
它只做一件事：进一个 datetime，出四柱。纯计算，给什么输入永远得什么输出。

运行（自测）：
    .venv/bin/python paipan/core.py
"""

from datetime import datetime, timedelta
from lunar_python import Solar

# ── 天干地支的本名（顺序有意义，别改）──
GAN = "甲乙丙丁戊己庚辛壬癸"          # 10 天干
ZHI = "子丑寅卯辰巳午未申酉戌亥"      # 12 地支
SHICHEN = list(ZHI)                   # 时辰就是地支，不用另写一遍 —— 同一份事实只写一次

# ── 五行映射表：天干、地支分开，因为它们属的五行不是一回事 ──
GAN_WX = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
          "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
ZHI_WX = {"子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
          "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}


def shichen_of(hour: int) -> str:
    """把 0-23 点换算成十二时辰名。

    子时跨 23 点和 0 点，所以不能直接 hour // 2 —— 那样 23 点会跑到「戌」。
    先 +1 再整除，等于把「23:00」当成新一轮的起点，最后 % 12 绕回开头。
    """
    idx = ((hour + 1) // 2) % 12
    return SHICHEN[idx]


def compute_pillars(dt: datetime) -> list:
    """给一个公历出生日期时间，返回四个柱：[年柱, 月柱, 日柱, 时柱]。

    立春分年：lunar_python 的 EightChar 已经按【分钟】精确处理，实测过（Day 13）。

    早子时派（Day 13 定的规矩）：23:00-24:00 出生的，日柱算次日。
      ★ 只替换 pillars[2]，其余三柱一个都不动。
        Day 14 的教训：当时图省事把整个日期 +1 天重新排盘，日柱是对了，
        但时柱跟着被推走了（壬子 → 甲子）。修好一个弄坏一个，叫回归 bug。
    """
    solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0)
    ec = solar.getLunar().getEightChar()
    pillars = [ec.getYear(), ec.getMonth(), ec.getDay(), ec.getTime()]

    if dt.hour >= 23:
        nd = dt + timedelta(days=1)
        pillars[2] = (Solar.fromYmdHms(nd.year, nd.month, nd.day, nd.hour, nd.minute, 0)
                      .getLunar().getEightChar().getDay())

    return pillars


def wuxing_count(pillars: list) -> dict:
    """数四柱里五个行各出现几次。返回 {'木': 2, '水': 3, ...}。

    只算【地支本气】，没算藏干 —— 一个地支只按它本来的五行星一次。
    藏干是 Day 16+ 的事（寅里藏甲丙戊，那就不再是「1 个木」了）。
    所以总数恒等于 8（四天干 + 四地支），这一点等下在 pandas 里当成校验用。
    """
    wx = {}
    for p in pillars:
        for ch in p:
            key = GAN_WX.get(ch) or ZHI_WX.get(ch)
            if key:
                wx[key] = wx.get(key, 0) + 1
    return wx


def lunar_date_str(dt: datetime) -> str:
    """把公历转成「2000年冬月廿五」这种中文农历日期。

    注意：这里的「年」是【农历年】（正月初一换），跟八字里的【年柱】（立春换）
    是两套换算法，不是同一个东西。页面上两个都要显示，别混。
    """
    solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0)
    lunar = solar.getLunar()
    return f"{lunar.getYear()}年{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}日"


if __name__ == "__main__":
    # ── 边界自测 ──────────────────────────────────────────
    # 下面这些期望值【不是】从本程序的输出抄来的（那等于自证，零价值）。
    # 它们来自三条互相独立的渠道：
    #   ① lunar_python（本库）
    #   ② cnlunar（另一个作者写的另一套实现）—— 两个库结果必须一致
    #   ③ 纯日期算术：1949-10-01 = 甲子日（公开可查），距今天数 % 60 直接推
    #      （这条完全不用命理库，所以它不可能是命理库的 bug）
    # 三个渠道对 2000-10-16 = 丁未 是一致的。Day 13 的教训：只测一个 API 就信它。
    cases = [
        (datetime(2000, 2, 4, 20, 39), (0, "己卯"), "立春是 20:41，前一分钟年柱还属上一年（己卯=1999）"),
        (datetime(2000, 2, 4, 20, 41), (0, "庚辰"), "立春那一分钟起，年柱换庚辰（2000 龙年）"),
        (datetime(2000, 2, 4, 20, 41), (2, "壬辰"), "换年柱【不许】波及日柱——同一天还是壬辰"),
        (datetime(2000, 10, 15, 22, 59), (2, "丙午"), "22:59 还没到子时，日柱留在当天（丙午）"),
        (datetime(2000, 10, 15, 23, 0), (2, "丁未"), "23:00 整点就跳次日，边界是闭区间"),
        (datetime(2000, 10, 15, 23, 30), (2, "丁未"), "早子时派：日柱按次日（= 10/16 的丁未）"),
        (datetime(2000, 10, 15, 23, 30), (3, "庚子"), "★ 时柱仍是当刻的子时，没被 +1 天推走（回归靶子）"),
        (datetime(2000, 10, 16, 12, 0), (2, "丁未"), "正午出生不触发规则，日柱同样是丁未"),
    ]
    fails = 0
    for dt, (which, expect), why in cases:
        got = compute_pillars(dt)[which]
        ok = got == expect
        fails += 0 if ok else 1
        print(f"{'✅' if ok else '❌'} {dt:%Y-%m-%d %H:%M} 「{'年月日时'[which]}柱」期望 {expect} 实得 {got}｜{why}")

    # 再加两条「关系断言」：不查任何资料，靠逻辑就该成立
    a = compute_pillars(datetime(2000, 10, 15, 12, 0))
    b = compute_pillars(datetime(2000, 10, 16, 12, 0))
    cycle = [GAN[i % 10] + ZHI[i % 12] for i in range(60)]      # 六十甲子表，自己拼
    step = (cycle.index(b[2]) - cycle.index(a[2])) % 60
    assert step == 1, f"相邻两天日柱应前进 1 位，实得 {step}"
    print(f"\n相邻两天的日柱 {a[2]} → {b[2]}，在六十甲子上前进 {step} 位 ✅")
    print(f"四柱总字数 = {sum(len(p) for p in a)}（每柱 2 个字，共 8）")

    wx = wuxing_count(a)
    print(f"今天样例五行 {wx} 合计 {sum(wx.values())}（应恒等于 8：4 天干 + 4 地支本气）")
    assert sum(wx.values()) == 8, "五行总数不是 8，说明映射表或柱子里混进了意料外的字"
    print(f"\n{len(cases)} 条边界用例：{'全部通过 ✅' if fails == 0 else f'失败 {fails} 条 ❌'}")

