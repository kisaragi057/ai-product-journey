"""
day06_cleaner.py —— 脏数据清洗与汇总工具

需求（Day 6 实践日，由我作为产品经理定义，5 个决策已确认）：
  输入：week01/day06_dirty.txt
  清洗：去空格 / 全角数字转半角 / 大小写与空格归一 / 单位统一 / 日期统一
  校验：数量必须存在且大于 0；金额用 数量×单价 重算，与原值不一致的行要列出来
  汇总：按【类别】分组，输出 总额 + 条数 + 占总金额百分比
  坏行：跳过并在末尾报告，绝不因为一行坏数据就崩掉整个程序
  输出：文字左对齐、数字右对齐、固定列宽

铁律：报告必须诚实。
  噪声 = 扔掉不算错 | 修补 = 我改了值但留下了记录 | 坏行 = 没法用，交人处理
  这三件事必须分开报告，混在一起就会让人误判。
"""

FILE_PATH = "week01/day06_dirty.txt"
EXPECTED_FIELDS = 7
HEADER = "申报日期,商品名称,类别,数量,单位,单价,金额"

# ── 三张映射表：清洗规则全部显式写出来，不藏在代码逻辑里 ──
# 好处：改规则不用改代码，非程序员也能看懂和校对这张表。
# 这是处理脏数据的标准做法——别名表（alias table），而不是靠算法去猜。

# 全角数字 → 半角数字
FULLWIDTH_DIGITS = {
    "０": "0", "１": "1", "２": "2", "３": "3", "４": "4",
    "５": "5", "６": "6", "７": "7", "８": "8", "９": "9",
}

# 单位别名 → 标准单位
UNIT_MAP = {
    "平方米": "平方米", "㎡": "平方米", "m2": "平方米", "M2": "平方米",
    "卷": "卷", "根": "根", "个": "个", "支": "支", "kg": "kg", "KG": "kg",
}

# 品名别名 → 标准品名
# 键是【归一化之后的形式】（去空格 + 转小写），值是人想要的展示形式
NAME_ALIAS = {
    "eva胶膜": "EVA胶膜",
    "超白压延玻璃": "超白压延玻璃",
    "镀膜玻璃": "镀膜玻璃",
    "光伏玻璃": "光伏玻璃",
    "铝边框": "铝边框",
    "背板": "背板",
    "接线盒": "接线盒",
    "硅胶": "硅胶",
    "镀磁": "镀磁",
    "焊带": "焊带",
    "玻璃": "玻璃",
}


def normalize_key(text):
    """把文本变成【用来查表匹配】的形式：去空格 + 转小写。
    注意这个值不用于展示，只用于「认出这是同一个东西」。
    这正是你 Day 4 练习C 自己发明的那招：seen 里存小写，输出存原样。"""
    return text.replace(" ", "").lower()


def to_number(text):
    """把文本转成数字。失败返回 None（不抛异常，让调用方决定怎么办）。
    处理的脏活：引号、千分位逗号、全角数字。"""
    cleaned = text.strip().strip('"')                  # 剥掉 "684,000.00" 的引号
    cleaned = cleaned.replace(",", "")                  # 去千分位：684000.00
    for full, half in FULLWIDTH_DIGITS.items():         # 全角转半角
        cleaned = cleaned.replace(full, half)
    try:
        return float(cleaned)                           # 第 10 周才正式学 try，
    except ValueError:                                   # 今天只要能读懂这两行
        return None


def to_halfwidth(text):
    """只做全角数字替换，不动其他。用于日期这种不是纯数字的字段。"""
    result = text
    for full, half in FULLWIDTH_DIGITS.items():
        result = result.replace(full, half)
    return result


# ══════════════════════════════════════════════════════════
# 第 1 步：读文件 + 拆字段 + 分离噪声与坏行（结构层）
# ══════════════════════════════════════════════════════════

with open(FILE_PATH, encoding="utf-8") as f:
    lines = f.read().split("\n")

noise_rows = []       # 空行、表头 —— 不是数据，扔掉
repair_log = []       # 我动过值的地方，必须留痕
bad_rows = []         # 结构不对，没法当数据用
good_rows = []        # 结构完整，进入清洗

for line_num, raw_line in enumerate(lines, start=1):
    if not raw_line.strip():
        noise_rows.append((line_num, "空行"))
        continue

    if raw_line.strip() == HEADER:
        if line_num == 1:
            noise_rows.append((line_num, "表头（第一行，正常）"))
        else:
            noise_rows.append((line_num, "重复表头（出现在中间）"))
        continue

    parts = raw_line.split(",")

    # 特例：金额带千分位逗号且被引号包住 → 被切成了 8 段，拼回 7 段
    if len(parts) == EXPECTED_FIELDS + 1:
        if parts[-2].startswith('"') and parts[-1].endswith('"'):
            merged = parts[-2] + "," + parts[-1]
            parts = parts[:-2] + [merged]
            # ⚠️ 修正上一步的分类错误：这是【修补】，不是噪声
            repair_log.append((line_num, "金额含引号千分位",
                               '"684,000.00" → 684000.00'))

    if len(parts) != EXPECTED_FIELDS:
        bad_rows.append((line_num, f"字段数={len(parts)}（应为{EXPECTED_FIELDS}）", raw_line))
        continue

    good_rows.append({"行号": line_num, "字段": parts})

# ══════════════════════════════════════════════════════════
# 第 2 步：清洗字段值（值层）
# ══════════════════════════════════════════════════════════

cleaned = []

for row in good_rows:
    line_num = row["行号"]
    raw_date, raw_name, raw_cat, raw_qty, raw_unit, raw_price, raw_amount = row["字段"]

    # ── 2.1 去空格（每个字段都要）──
    date_s = raw_date.strip()
    name_s = raw_name.strip()
    cat_s = raw_cat.strip()
    qty_s = raw_qty.strip()
    unit_s = raw_unit.strip()
    price_s = raw_price.strip()
    amount_s = raw_amount.strip()

    # 记录哪些字段原本带空格 —— 这也是修补留痕
    for label, raw_v, clean_v in [("品名", raw_name, name_s), ("类别", raw_cat, cat_s)]:
        if raw_v != clean_v:
            repair_log.append((line_num, f"{label}去空格", f"{raw_v!r} → {clean_v!r}"))

    # ── 2.2 日期统一为 YYYY-MM-DD ──
    date_fixed = to_halfwidth(date_s).replace("/", "-")
    if date_fixed != date_s:
        repair_log.append((line_num, "日期格式统一", f"{date_s!r} → {date_fixed!r}"))
    # 校验：年份必须是 4 位数字开头。不满足就标记，不要瞎猜怎么改。
    year_part = date_fixed.split("-")[0]
    date_ok = len(year_part) == 4 and year_part.isdigit()
    if not date_ok:
        repair_log.append((line_num, "日期可疑（未自动修正）", f"{date_fixed!r} 不是 YYYY-MM-DD"))

    # ── 2.3 品名归一：用别名表把 eva胶膜 / EVA 胶膜 统一成 EVA胶膜 ──
    key = normalize_key(name_s)
    if key in NAME_ALIAS:
        if NAME_ALIAS[key] != name_s:
            repair_log.append((line_num, "品名归一", f"{name_s!r} → {NAME_ALIAS[key]!r}"))
        name_fixed = NAME_ALIAS[key]
    else:
        name_fixed = name_s            # 查不到就不动它 —— 绝不瞎猜品名

    # ── 2.4 类别去空格（同上已做），但【不做别名归并】──
    # 第18行类别是「超白」、第17行是「M2」——这些是语义错误不是写法差异，
    # 程序没有资格推断「你其实想写玻璃」。保留原值，交给第 3 步的汇总把它显形。
    cat_fixed = cat_s

    # ── 2.5 单位映射 ──
    if unit_s in UNIT_MAP:
        if UNIT_MAP[unit_s] != unit_s:
            repair_log.append((line_num, "单位统一", f"{unit_s!r} → {UNIT_MAP[unit_s]!r}"))
        unit_fixed = UNIT_MAP[unit_s]
    else:
        unit_fixed = unit_s
        repair_log.append((line_num, "单位未知", f"{unit_s!r} 不在映射表里，原样保留"))

    # ── 2.6 数值转换（引号、千分位、全角、空值）──
    qty = to_number(qty_s)
    price = to_number(price_s)
    amount_raw = to_number(amount_s)

    if qty is None:
        repair_log.append((line_num, "数量无法转数字", f"{qty_s!r} → None"))

    cleaned.append({
        "行号": line_num,
        "日期": date_fixed,
        "品名": name_fixed,
        "类别": cat_fixed,
        "数量": qty,
        "单位": unit_fixed,
        "单价": price,
        "原金额": amount_raw,
    })

# ══════════════════════════════════════════════════════════
# 第 3 步：业务校验 + 金额重算 + 按类别汇总
# ══════════════════════════════════════════════════════════

business_bad = []       # 业务非法（结构没问题，但值用不了）
amount_mismatch = []    # 金额与重算不符
usable = []             # 真正参与汇总的行

for r in cleaned:
    # 校验一：数量必须存在（第15行是空字符串 → to_number 给了 None）
    if r["数量"] is None:
        business_bad.append((r["行号"], "数量缺失", r["品名"]))
        continue
    # 校验二：数量必须大于 0（第16行是 -50，算术自洽但业务非法）
    if r["数量"] <= 0:
        business_bad.append((r["行号"], f"数量非法（{r['数量']:,.0f}）", r["品名"]))
        continue
    if r["单价"] is None:
        business_bad.append((r["行号"], "单价无法解析", r["品名"]))
        continue

    # ── 金额重算（需求 Q1：以 数量×单价 为准）──
    recomputed = r["数量"] * r["单价"]
    if r["原金额"] is not None and abs(recomputed - r["原金额"]) > 0.01:
        # ⚠️ 为什么用 abs(差) > 0.01 而不是直接 != ？
        # 因为浮点数存不精确（今天实验过 0.1+0.2 = 0.30000000000000004）。
        # 直接比大小会把「本来相等」的两数判成不等。
        amount_mismatch.append((
            r["行号"], r["品名"], r["原金额"], recomputed,
            recomputed - r["原金额"],
        ))
    r["金额"] = recomputed
    usable.append(r)

# ── 按类别分组累加（需求：总额 + 条数 + 占比）──
by_cat = {}
for r in usable:
    if r["类别"] not in by_cat:
        by_cat[r["类别"]] = {"金额": 0.0, "条数": 0}
    by_cat[r["类别"]]["金额"] += r["金额"]     # 字典套字典，值用 += 累加
    by_cat[r["类别"]]["条数"] += 1

grand_total = 0.0
for v in by_cat.values():
    grand_total += v["金额"]


def display_width(text):
    """算出字符串在终端里占几列。中文/全角算 2 列，ASCII 算 1 列。
    —— 这就是昨天说『中文居中做不到』的根本原因：不能只用 len()，
        必须按【显示宽度】算。len('玻璃') 是 2，但它在屏幕上占 4 列。"""
    w = 0
    for ch in text:
        w += 2 if ord(ch) > 0x2E80 else 1
    return w


def pad_right(text, width):
    """左对齐：按显示宽度补空格到 width 列"""
    return text + " " * max(0, width - display_width(text))


# ══════════════════════════════════════════════════════════
# 最终输出
# ══════════════════════════════════════════════════════════

print("═" * 70)
print("按类别汇总")
print("═" * 70)
print(pad_right("类别", 10) + f'{"条数":>7}{"金额":>16}{"占比":>9}')
print("-" * 70)

# 按金额从大到小排。key=lambda 那个写法 Day 8 会正式讲，今天照抄即可。
ordered = sorted(by_cat.items(), key=lambda kv: kv[1]["金额"], reverse=True)
for cat, stat in ordered:
    pct = stat["金额"] / grand_total * 100
    print(pad_right(cat, 10) + f'{stat["条数"]:>7}{stat["金额"]:>16,.2f}{pct:>8.1f}%')

print("-" * 70)
print(pad_right("合计", 10) + f'{len(usable):>7}{grand_total:>16,.2f}{100.0:>8.1f}%')

# ── 五类报告，各自分开，绝不混淆 ──
print()
print("═" * 70)
print("数据质量报告")
print("═" * 70)

print(f"【1】噪声（不是数据，丢弃不算错）—— {len(noise_rows)} 行")
for num, reason in noise_rows:
    print(f"      第{num}行  {reason}")

print()
print(f"【2】修补（我改了值，全部留痕）—— {len(repair_log)} 条")
for num, reason, detail in repair_log:
    print(f"      第{num}行  {pad_right(reason, 18)}{detail}")

print()
print(f"【3】结构坏行（字段数不对）—— {len(bad_rows)} 行")
if not bad_rows:
    print("      无")
for num, reason, content in bad_rows:
    print(f"      第{num}行  {reason}  原文: {content[:40]}")

print()
print(f"【4】业务坏行（结构对但值用不了，未参与汇总）—— {len(business_bad)} 行")
for num, reason, name in business_bad:
    print(f"      第{num}行  {pad_right(reason, 18)}{name}")

print()
print(f"【5】金额不符（重算值 ≠ 原值，已以重算值为准）—— {len(amount_mismatch)} 行")
if not amount_mismatch:
    print("      无")
for num, name, orig, recomputed, diff in amount_mismatch:
    print(f"      第{num}行  {pad_right(name, 12)}原值 {orig:>12,.2f}"
          f" → 重算 {recomputed:>12,.2f}   差 {diff:>+11,.2f}")

# ══════════════════════════════════════════════════════════
# 自检：期望值全部由「独立手算 + 另一套算法」交叉验证得出，
#       不是从上面这段汇总代码里顺手抄来的（那样等于自证，毫无意义）
# ══════════════════════════════════════════════════════════

def run_self_checks():
    assert len(usable) == 13, "可用行数应为 13"
    assert len(business_bad) == 2, "业务坏行应为 2 行（第15、16行）"
    assert len(amount_mismatch) == 1, "金额不符应只有 1 行"
    assert amount_mismatch[0][0] == 14, "那行应是第 14 行"
    assert abs(amount_mismatch[0][4] - (-20000.0)) < 0.01, "第14行差额应为 -20000"
    assert by_cat["玻璃"]["条数"] == 4, "玻璃应 4 条"
    assert abs(by_cat["玻璃"]["金额"] - 2454000.00) < 0.01, "玻璃合计 2,454,000"
    assert abs(by_cat["胶膜"]["金额"] - 636000.00) < 0.01, "胶膜合计 636,000"
    assert abs(by_cat["化工"]["金额"] - 137900.00) < 0.01, "化工合计 137,900"
    assert abs(by_cat["超白"]["金额"] - 684000.00) < 0.01, "超白合计 684,000"
    assert abs(by_cat["边框"]["金额"] - 15360.00) < 0.01, "边框合计 15,360"
    assert abs(grand_total - 4131260.00) < 0.01, f"总额应为 4,131,260，实际 {grand_total:,.2f}"
    return 12


checks = run_self_checks()
print()
print(f"✓ {checks} 条自检全部通过")
print()
print("⚠️ 请人工确认报告【4】之外的这两项：")
print("   类别「超白」（第18行）和「M2」（第17行）各只有 1 条，")
print("   它们极可能是【字段内容填错了位置】，不是真的类别。")
print("   程序没有资格替你改，所以原样保留 —— 请人工确认后回源数据修正。")
