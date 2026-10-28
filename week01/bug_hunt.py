"""
bug_hunt.py —— 埋了三个 bug 的汇总工具（Day 10 调试练习专用）

规则（这几条本身就是今天的教材）：
  1. **不要通读全文件找 bug。** 那是外行做法。先看报错，报错会告诉你是哪一行。
  2. 读 traceback 的顺序：**最后一行 → 往上找自己的文件名和行号 → 看那一行和它调用的那行**。
  3. 修一个跑一次。三个一起改，你会不知道是哪个起的作用。
  4. 每修好一个，在 debug_notes.md 记一条（今天要交 3 条）。

**这里有 3 个 bug，都不在数据里，全在函数体里。** 性质不同，这很重要：
  · 其中 2 个会抛异常 —— 程序当场停下。这其实是好事：它在主动告诉你它错了。
  · 还有 1 个【完全不报错】，程序跑完了、格式很漂亮、数字是错的。
    找出它唯一的线索，就是最后那行「对得上吗」。

我不标位置——**定位本身就是今天的练习内容。**

预期正确输出（我独立算过：100×85.5=8550，30×1200=36000，500×12.8=6400，合计 50950）：

  逐项：
    超白玻璃 x 100 = 8,550.00
    EVA胶膜 x 30 = 36,000.00
    铝边框 x 500 = 6,400.00
  按类别：
    玻璃: 8,550.00（1 条）
    胶膜: 36,000.00（1 条）
    边框: 6,400.00（1 条）
    金额最高类别: 胶膜
    总计: 50,950.00
    对得上吗: True
"""

ROWS = [
    {"品名": "超白玻璃", "类别": "玻璃", "数量": 100, "单价": 85.5},
    {"品名": "EVA胶膜", "类别": "胶膜", "数量": 30, "单价": 1200.0},
    {"品名": "铝边框", "类别": "边框", "数量": 500, "单价": 12.8},
]

# ★ 这个期望值是我【手算】出来的，没有用任何表达式。
#   它在这里的唯一作用，就是把那个「不报错的 bug」逼出来 ——
#   如果 EXPECTED_TOTAL 也用 100*85.5+30*1200+500*12.8 算，它和 total_amount()
#   永远相等，这个检查就等于自证、毫无意义。（这是我上一版犯的错，留作反面教材）
EXPECTED_TOTAL = 50950.0

def total_amount(rows):
    """把所有行的「数量 × 单价」累加起来。"""
    total = 0
    for r in rows:
        total += r["数量"] * r["单价"]
    return total

def group_by_category(rows):
    """按类别汇总金额。返回 {类别: {"金额": x, "条数": n}}"""
    result = {}
    for r in rows:
        cat = r["类别"]
        amount = r["数量"] * r["单价"]
        if cat not in result:
            result[cat] = {"金额": 0.0, "条数": 0}
        result[cat]["金额"] += amount
        result[cat]["条数"] += 1
    return result


def top_category(groups):
    """返回金额最高的类别名。"""
    best = None
    best_amount = 0
    for cat, stat in groups.items():
        if stat["金额"] > best_amount:
            best_amount = stat["金额"]
            best = cat
    return best


def report(rows):
    print("逐项：")
    for r in rows:
        # 注意这一行的引号嵌套（外层双、内层单）是合法的，别往那儿找。
        line = f"  {r['品名']} x {r['数量']}"

        amount = r["数量"] * r["单价"]

        print(line + " = " + f"{amount:,.2f}")

    groups = group_by_category(rows)
    print("按类别：")
    for cat, stat in groups.items():
        print(f"  {cat}: {stat['金额']:,.2f}（{stat['条数']} 条）")

    print(f"  金额最高类别: {top_category(groups)}")
    total = total_amount(rows)
    print(f"  总计: {total:,.2f}")
    print(f"  对得上吗: {abs(total - EXPECTED_TOTAL) < 0.01}")


if __name__ == "__main__":
    report(ROWS)
