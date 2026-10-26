"""
day06_cleaner_v2.py —— 脏数据清洗与汇总工具【重构版】

这是 Day 8 练习 A 的脚手架。

重构的定义：**改结构，不改行为。**
所以本文件的唯一验收标准是：
    跑出来的汇总数字和五类报告，必须与 day06_cleaner.py 逐字一致。

对照物：week01/day06_cleaner.py（平铺版，已提交为安全锚点 8e06973）
做法建议：VS Code 里同时打开两个文件，把平铺版里的对应代码
         "搬" 进下面这些函数体。**不要重新发明，只是搬家。**

════════ 已完成的样板 ════════
  split_lines()        ← 我写完了，你照着这个形状写后面五个
  以及下面 6 个纯工具函数（原样搬过来的，不用动）

════════ 你要填的五个 ════════
  classify_lines()         平铺版「第 1 步」的循环搬进来
  clean_row()              平铺版「第 2 步」的循环体搬进来
  validate_and_recompute() 平铺版「第 3 步」前半段搬进来
  summarize_by_category()  平铺版「第 3 步」分组那段搬进来
  render_report()          平铺版所有 print 那段搬进来

填完后运行：.venv/bin/python week01/day06_cleaner_v2.py
看到「✓ 12 条断言全部通过」且表格数字和原来一致，练习 A 就完成。
"""

# ══════════════════════════════════════════════════════════
# 常量（不用动）
# ══════════════════════════════════════════════════════════

FILE_PATH = "week01/day06_dirty.txt"
EXPECTED_FIELDS = 7
HEADER = "申报日期,商品名称,类别,数量,单位,单价,金额"

FULLWIDTH_DIGITS = {
    "０": "0", "１": "1", "２": "2", "３": "3", "４": "4",
    "５": "5", "６": "6", "７": "7", "８": "8", "９": "9",
}

UNIT_MAP = {
    "平方米": "平方米", "㎡": "平方米", "m2": "平方米", "M2": "平方米",
    "卷": "卷", "根": "根", "个": "个", "支": "支", "kg": "kg", "KG": "kg",
}

NAME_ALIAS = {
    "eva胶膜": "EVA胶膜", "超白压延玻璃": "超白压延玻璃", "镀膜玻璃": "镀膜玻璃",
    "光伏玻璃": "光伏玻璃", "铝边框": "铝边框", "背板": "背板", "接线盒": "接线盒",
    "硅胶": "硅胶", "镀磁": "镀磁", "焊带": "焊带", "玻璃": "玻璃",
}


# ══════════════════════════════════════════════════════════
# 纯工具函数（从平铺版原样搬来，不用动）
# ══════════════════════════════════════════════════════════

def normalize_key(text: str) -> str:
    """把文本变成【用来查表匹配】的形式：去空格 + 转小写。只用于认身份，不用于展示。"""
    return text.replace(" ", "").lower()


def to_halfwidth(text: str) -> str:
    """只做全角数字替换，不动其他。用于日期这种不是纯数字的字段。"""
    result = text
    for full, half in FULLWIDTH_DIGITS.items():
        result = result.replace(full, half)
    return result


def to_number(text: str) -> float | None:
    """文本转数字。处理的脏活：引号、千分位逗号、全角数字。
    转换失败返回 None —— 由调用方决定怎么处理，函数自己不做主张。"""
    cleaned = text.strip().strip('"')
    cleaned = cleaned.replace(",", "")
    for full, half in FULLWIDTH_DIGITS.items():
        cleaned = cleaned.replace(full, half)
    try:
        return float(cleaned)
    except ValueError:
        return None


def display_width(text: str) -> int:
    """字符串在终端占几列。中文/全角算 2 列，ASCII 算 1 列。"""
    width = 0
    for ch in text:
        width += 2 if ord(ch) > 0x2E80 else 1
    return width


def pad_right(text: str, width: int) -> str:
    """左对齐：按显示宽度补空格到 width 列。"""
    return text + " " * max(0, width - display_width(text))


def is_header_line(line: str) -> bool:
    """这一行是不是表头（包括出现在文件中间的重复表头）。"""
    return line.strip() == HEADER


# ══════════════════════════════════════════════════════════
# ★ 样板：split_lines —— 你要照着这个形状写后面五个
# ══════════════════════════════════════════════════════════

def split_lines(path: str) -> list[str]:
    """读取文本文件，返回一个列表，每个元素是一行原始文本。

    参数:
        path: 文件路径，相对项目根目录。
              例如 "week01/day06_dirty.txt"

    返回:
        list[str]，**含空行和表头**，本函数不做任何过滤或清洗。

    设计说明（这段比代码重要，读它）:
        为什么这里不顺手把空行去掉？
        —— 因为「一个函数只做一件事」。过滤是 classify_lines 的职责。
           现在混进来，将来想改过滤规则就得在「读文件」的代码里找，
           而且这个函数再也不能用于「我要看原始行数」的场合。

        为什么不做 encoding 参数？
        —— 因为现在没有第二种编码的需求。加了就是白加（YAGNI 原则：
           不为想象中的需求提前写代码）。等你真遇到乱码再加。

        为什么路径是参数而不是直接用全局的 FILE_PATH？
        —— 因为这样才能换文件复用、才能单独测试。这是第 5 节「不碰外面
           的世界」的第一次实际应用：数据从参数进，从 return 出。
    """
    with open(path, encoding="utf-8") as f:
        return f.read().split("\n")


# ══════════════════════════════════════════════════════════
# ↓↓↓ 下面是留给你的五个。契约已定好，你只填函数体 ↓↓↓
# ══════════════════════════════════════════════════════════

def classify_lines(lines: list[str], header: str, expected_fields: int):
    """把行分成四类。

    参数:
        lines:           split_lines() 的返回值
        header:          表头文本，用来识别表头行
        expected_fields: 正确的字段个数（这里是 7）

    返回:
        四个值（Python 会自动打包成元组，调用方用 a, b, c, d = ... 拆开）
        good_rows:    list[dict]，每项 {"行号": int, "字段": list[str]}
        noise_rows:   list[tuple]，每项 (行号, 原因)
        repair_log:   list[tuple]，每项 (行号, 原因, 细节)
        bad_rows:     list[tuple]，每项 (行号, 原因, 原文)

    要处理的四件事（平铺版第 1 步的循环里都有，照着搬）:
        1. 空行 → 进 noise
        2. 表头行（含出现在中间的重复表头）→ 进 noise
        3. 按逗号切分；若正好多切出一段且最后两段是 "xxx,yyy" 这种
           带引号的千分位 → 拼回去，并往 repair_log 记一条
        4. 拼完字段数还是不对 → 进 bad_rows

    ⚠️ 注意：header 和 expected_fields 是参数，别在函数里直接写全局的
       HEADER / EXPECTED_FIELDS。用了参数，这个函数才可复用、可单独测。
    """
    raise NotImplementedError("classify_lines 还没写 —— 平铺版第 1 步的循环搬过来")


def clean_row(parts: list[str], line_num: int) -> dict:
    """把一行已经拆好的字段清洗成一条规范记录。

    参数:
        parts:    七个字符串，顺序对应 日期/品名/类别/数量/单位/单价/金额
        line_num: 原始行号，用于报告里定位

    返回:
        dict，键为：行号 日期 品名 类别 数量 单位 单价 原金额
        其中 数量/单价/原金额 是 float 或 None（用 to_number 转）

    要做的六件事（平铺版第 2 步里都有）:
        1. 每个字段 strip 去首尾空格；原本带空格的 → 记进 repair_log
        2. 日期：全角转半角、斜杠换连字符；变了就记一笔
        3. 品名：用 normalize_key + NAME_ALIAS 归一；查不到就原样保留，**别猜**
        4. 类别：只去空格，**不做别名归并**（超白/M2 是语义错误不是写法差异）
        5. 单位：查 UNIT_MAP；不在表里就保留原值并记一笔「单位未知」
        6. 数值：to_number 转换；失败记一笔

    ⚠️ 关于 repair_log —— 这里必须用【返回值】传出来，不能像平铺版那样
       往全局列表 append。原因有两个：
         ① 第 5.4 节那个「偷改全局可变对象」的坑，正是这个写法；
         ② 下面的主流程已经写死了 `record, row_repairs = clean_row(...)`，
            所以你必须返回两个值，没有第二条路 —— 这是刻意设计的，
            让主流程的契约逼你写出干净版本。
       顺带体会一件事：**定好接口契约，能替团队挡住坏写法。**
       这就是为什么正式项目里函数签名比函数体更早被讨论。
    """
    raise NotImplementedError("clean_row 还没写 —— 平铺版第 2 步的循环体搬过来")


def validate_and_recompute(records: list[dict]):
    """业务校验 + 金额重算。

    返回三个值：
        usable:          list[dict]，每项多了一个 "金额" 键（重算后的值）
        business_bad:    list[tuple]，每项 (行号, 原因, 品名)
        amount_mismatch: list[tuple]，每项 (行号, 品名, 原值, 重算值, 差额)

    规则（和平铺版一致）:
        数量是 None        → business_bad，原因 "数量缺失"
        数量 <= 0          → business_bad，原因 f"数量非法（{值}）"
        单价是 None        → business_bad，原因 "单价无法解析"
        其余               → 金额 = 数量 × 单价；
                             若原金额存在且 abs(重算 - 原值) > 0.01 → 记进 mismatch
                             （为什么不用 == ？因为浮点精度，第 6 天验过）
    """
    raise NotImplementedError("validate_and_recompute 还没写")


def summarize_by_category(usable: list[dict]) -> tuple[dict, float]:
    """按「类别」分组累加。

    返回:
        by_cat:     dict，形如 {"玻璃": {"金额": 2454000.0, "条数": 4}, ...}
        grand_total: float，所有类别金额之和

    提示：核心还是 Day 4 那行 by_cat[k] = by_cat.get(k, 0) + v 的变体，
         只是这里值是个字典，要分别累加 金额 和 条数。
    """
    raise NotImplementedError("summarize_by_category 还没写")


def render_report(cleaned_count: int, usable: list[dict], by_cat: dict,
                  grand_total: float, noise_rows, repair_log, bad_rows,
                  business_bad, amount_mismatch) -> None:
    """打印汇总表 + 五类报告。只做事，不返回东西（所以标注是 -> None）。

    ⚠️ 看到参数列表这么长，你的第一反应应该是什么？
       —— 这是**设计上的坏味道**，说明有九样东西要凑齐才能打印。
       更好的做法是把这些结果收进一个「报告对象」再传。但那要 class，
       Day 8 只要求读懂，所以今天先这样，你在 NOTES 里记一笔这个观察。
       能感觉到「参数太多 = 信号」，比写出能跑的代码更重要。

    要求：输出必须与平铺版逐字一致（列宽、千分位、百分比小数位、分隔线长度）。
    """
    raise NotImplementedError("render_report 还没写")


# ══════════════════════════════════════════════════════════
# 验收断言 —— 期望值全部独立算过，这是重构的硬标准
# （平铺版里它们是裸在文件末尾的；现在收进函数，符合第 5 节规矩）
# ══════════════════════════════════════════════════════════

def run_self_checks(usable: list[dict], business_bad, amount_mismatch,
                    by_cat: dict, grand_total: float) -> int:
    """跑 12 条断言。全过返回条数；任何一条不符立刻 AssertionError 停下。"""
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


# ══════════════════════════════════════════════════════════
# 主流程 —— 重构的全部意义就在这六行
# 对比 day06_cleaner.py 的两百行平铺，这里一眼能读完整个程序在干什么。
# 你不用写这段，它已经写好了，正好告诉你每个函数的输入输出怎么接。
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    lines = split_lines(FILE_PATH)
    print(f"split_lines 完成：读到 {len(lines)} 行原始文本")

    good_rows, noise_rows, repair_log, bad_rows = classify_lines(
        lines, HEADER, EXPECTED_FIELDS)

    cleaned = []
    for row in good_rows:
        record, row_repairs = clean_row(row["字段"], row["行号"])
        cleaned.append(record)
        repair_log.extend(row_repairs)

    usable, business_bad, amount_mismatch = validate_and_recompute(cleaned)
    by_cat, grand_total = summarize_by_category(usable)

    render_report(len(cleaned), usable, by_cat, grand_total, noise_rows,
                  repair_log, bad_rows, business_bad, amount_mismatch)

    passed = run_self_checks(usable, business_bad, amount_mismatch, by_cat, grand_total)
    print(f"\n✓ {passed} 条断言全部通过 —— 重构没有改变行为")
