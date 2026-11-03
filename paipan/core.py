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

from datetime import datetime
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

# ── 地支藏干表（产品资产，不是库的复制品）──
# 第一位是本气，后面是中气、余气。本气的五行 == 上面 ZHI_WX 那一格，这是免费的校验点。
# 注意「巳」这里写的是 丙庚戊；通行书上也常见 丙戊庚 的写法，中余气顺序各派不一致，
# 但本气都是丙 —— 所以顺序不敏感、本气敏感。core.py 的自测就是按这个口径断言的。
ZHI_CANGGAN = {"子": ["癸"],           "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"],
               "卯": ["乙"],           "辰": ["戊", "乙", "癸"], "巳": ["丙", "庚", "戊"],
               "午": ["丁", "己"],     "未": ["己", "丁", "乙"], "申": ["庚", "壬", "戊"],
               "酉": ["辛"],           "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"]}

# ── 子时口径开关 ──
# 1 = 早子时派：23:00-24:00 归【次日】（Day 13 定的口径）
# 2 = 夜子时派：日柱留在当天，但时柱按次日干起 —— 这是 lunar_python 的【默认值】
# 换句话说：库默认站在我们口径的对立面。以前我用「手动 +1 天」去硬掰，只掰到了四柱字符串，
# 藏干 / 地势 / 十神 这些派生字段仍然按当天算 —— Day 16 改用它自带的开关，一处生效，处处生效。
ZI_SECT = 1


def is_yang(gan: str) -> bool:
    """甲丙戊庚壬为阳。天干序号（在 GAN 里的下标）是偶数就是阳。"""
    return GAN.index(gan) % 2 == 0


def shichen_of(hour: int) -> str:
    """把 0-23 点换算成十二时辰名。

    子时跨 23 点和 0 点，所以不能直接 hour // 2 —— 那样 23 点会跑到「戌」。
    先 +1 再整除，等于把「23:00」当成新一轮的起点，最后 % 12 绕回开头。
    """
    idx = ((hour + 1) // 2) % 12
    return SHICHEN[idx]


def build_solar(dt: datetime):
    """datetime → Solar。全项目只有这一处在构造 Solar，参数写法不许再出现第二遍。"""
    return Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0)


def build_ec(dt: datetime):
    """唯一的 EightChar 入口。任何人要算八字，都从这里拿，不许自己 new 一个。

    为什么必须有这个函数：库里所有派生字段（藏干、地势、十神、纳音）都看 sect。
    如果各处各建对象、只有一处设了 sect，就会出现
    「显示的日柱是未、藏干算的是午」这种【不报错的串号】—— Day 16 就是这么发现的。
    """
    ec = build_solar(dt).getLunar().getEightChar()
    ec.setSect(ZI_SECT)
    return ec


def compute_pillars(dt: datetime) -> list:
    """给公历出生日期时间，返回 [年柱, 月柱, 日柱, 时柱]。

    立春分年：精确到分钟（Day 13 实测）。
    早子时派：23:00-24:00 归次日 —— 现在由 build_ec 里的 setSect(1) 负责，
    不再手动 +1 天。行为与旧写法逐字等价（36525 组对比，0 组不同），
    但派生字段从此跟着一起对。
    """
    ec = build_ec(dt)
    return [ec.getYear(), ec.getMonth(), ec.getDay(), ec.getTime()]


def count_wx(pillars: list, hidden: bool = False) -> dict:
    """数五行 × 阴阳，返回 10 个键：{'木阳':1,'木阴':0,'火阳':2,...}。

    hidden=False → 只算 8 个字：4 天干 + 4 地支的本气干（口径 A）
    hidden=True  → 地支展开成全部藏干（口径 B），字数随月份不同（12-15 个）

    阴阳按【干自己】定（甲丙戊庚壬为阳），不按支性定。
    理由：这里数的是干，不是地支这个字。支性阴阳是 UI 给地支卡片贴的标签，
    两者在子午巳亥四个支上会不一样，别混——但本表两处都不许出现第二套算法。
    """
    out = {}
    for p in pillars:
        gan = p[0]
        zhi = p[1]
        stems = ZHI_CANGGAN[zhi] if hidden else [ZHI_CANGGAN[zhi][0]]
        for g in [gan] + stems:
            key = GAN_WX[g] + ("阳" if is_yang(g) else "阴")
            out[key] = out.get(key, 0) + 1
    for w in "木火土金水":
        for y in "阳阴":
            out.setdefault(w + y, 0)
    return out


def wuxing_count(pillars: list) -> dict:
    """旧接口：只给五行总数（{'木':2,'火':3,...}），app.py 还在用。

    刻意不重写一遍逻辑，而是从 count_wx 合并出来 ——
    同一份事实只允许一个来源（Day 16 的串号教训就是这么来的）。
    """
    out = {}
    for key, n in count_wx(pillars).items():
        out[key[0]] = out.get(key[0], 0) + n
    return out



def lunar_date_str(dt: datetime) -> str:
    """把公历转成「2000年冬月廿五」这种中文农历日期。

    注意：这里的「年」是【农历年】（正月初一换），跟八字里的【年柱】（立春换）
    是两套换算法，不是同一个东西。页面上两个都要显示，别混。
    """
    lunar = build_solar(dt).getLunar()
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

    # ══════════════════════════════════════════════════
    # Day 16 新增：派生字段不许和显示的日柱分家
    # ══════════════════════════════════════════════════
    print("\n── 派生字段一致性 ──")
    # ① 藏干表（我们自己写的）vs 库的返回：本气必须严格相等，中余气只看集合
    n = 0
    for i in range(400):
        dt = (datetime(2000, 1, 1) + __import__("datetime").timedelta(days=i)).replace(hour=12)
        ec = build_ec(dt)
        zhi = ec.getDay()[1]
        mine, theirs = ZHI_CANGGAN[zhi], ec.getDayHideGan()
        assert mine[0] == theirs[0], f"{dt} 本气不符：我 {mine[0]} 库 {theirs[0]}"
        assert set(mine) == set(theirs), f"{dt} 藏干内容不符：{mine} vs {theirs}"
        n += 1
    print(f"✅ 藏干表与库一致（{n} 天，本气严格、中余气看集合）")

    # ② 五鼠遁：自己按口诀推时柱，和库给的比 —— 一条完全独立的渠道
    #    甲己还加甲、乙庚丙作初、丙辛从戊起、丁壬庚子居、戊癸何方发、壬子是真途
    DUN = {"甲": 0, "己": 0, "乙": 2, "庚": 2, "丙": 4, "辛": 4, "丁": 6, "壬": 6, "戊": 8, "癸": 8}
    bad = 0
    for i in range(240):
        for hh in (0, 9, 14, 22, 23):
            dt = (datetime(2000, 1, 1) + __import__("datetime").timedelta(days=i)).replace(hour=hh, minute=30)
            ec = build_ec(dt)
            zhi_idx = ((hh + 1) // 2) % 12                       # 时辰在地支上的序号
            expect = GAN[(DUN[ec.getDayGan()] + zhi_idx) % 10] + ZHI[zhi_idx]
            if expect != ec.getTime():
                bad += 1
                if bad <= 2:
                    print(f"   ❌ {dt:%m-%d %H:%M} 我推 {expect} 库 {ec.getTime()} 日干 {ec.getDayGan()}")
    print(f"{'✅' if bad == 0 else '❌'} 五鼠遁独立推时柱 240 天 × 5 时段，不符 {bad} 组"
          f"（这条同时也证明了 sect=1 自洽：23 点的时柱确实按【次日干】起）")

    # ③ 串号回归靶子：日柱的地支，必须就是藏干所属的那个地支
    for hh in (12, 23, 0):
        dt = datetime(2000, 10, 15, hh, 30)
        ec = build_ec(dt)
        p = compute_pillars(dt)
        assert p[2][1] == ZHI[ec.getDayZhiIndex()], f"{hh} 点串号：柱 {p[2]} 藏干 {ec.getDayHideGan()}"
        assert ec.getDayHideGan()[0] in GAN_WX and \
               GAN_WX[ec.getDayHideGan()[0]] == ZHI_WX[p[2][1]], f"{hh} 点本气五行与日支不符"
        print(f"✅ {hh:02d}:30 日柱 {p[2]}｜日主 {ec.getDayGan()}｜藏干 {ec.getDayHideGan()}｜地势 {ec.getDayDiShi()}")


