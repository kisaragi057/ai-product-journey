"""
day_counter.py —— 我的第一个 Python 程序

运行方式（在项目目录下）：
    .venv/bin/python day_counter.py

这个程序会告诉你：今天是 AI 学习计划的第几天、第几周、还剩多少天。
它用到的语法点，正好是课程表 Day 1 到 Day 5 的全部内容：
    变量、字符串格式化(f-string)、导入模块、字典、条件判断、列表、循环。

【重要】按 vibe coding 的纪律：下面每一行你都要能解释。
       看不懂的地方，把那一行贴给我，我讲到你懂为止。
"""

# ── 第 1 部分：导入模块 ────────────────────────────────
# import 的意思是"把别人写好的工具箱拿过来用"。
# datetime 是 Python 自带的处理日期时间的工具箱，不用额外安装。
from datetime import date

# ── 第 2 部分：定义变量 ────────────────────────────────
# 变量就是给一个值起个名字，之后可以用名字来引用它。
# date(2026, 10, 19) 创建了一个"日期对象"，三个参数分别是 年、月、日。
PLAN_START = date(2026, 10, 19)   # 计划的第 1 天
TOTAL_DAYS = 84                    # 计划总共 84 天

# 这是一个"列表"(list)：用方括号装起来的一串东西，用逗号分隔。
# 这里装的是 7 个字符串，代表星期一到星期日。
# 列表的编号从 0 开始，所以 WEEKDAY_NAMES[0] 是 "周一"。
WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# ── 第 3 部分：定义一个函数 ────────────────────────────
# def 是 "define"(定义) 的缩写。函数就是把一段逻辑打包起来，起个名字，之后可以反复调用。
# 括号里的 today 叫"参数"：调用它时传进来的值，在函数内部用这个名字来引用。
def describe_day(today):
    """输入一个日期，返回一个装着当天信息的字典。"""

    # 两个日期相减会得到一个 timedelta(时间差)对象，.days 取出相差的天数。
    # 因为 Day 1 就是开始日那天，所以要 +1。
    day_number = (today - PLAN_START).days + 1

    # .weekday() 返回 0-6 的数字（0=周一），正好可以拿来当列表的下标。
    weekday_name = WEEKDAY_NAMES[today.weekday()]

    # 整数除法 // 只保留整数部分。除以 7 再向上取整得到"第几周"。
    # 这里用 (day_number - 1) // 7 + 1 是一个常用技巧，避免 7 的倍数算错。
    week_number = (day_number - 1) // 7 + 1

    # 这是一个"字典"(dict)：用花括号装起来的"键值对"集合。
    # 键(key)在冒号左边，值(value)在右边。之后可以用 describe["day"] 取值。
    # 字典极其重要：所有 API 返回的 JSON 数据，本质上就是它。
    describe = {
        "day": day_number,
        "weekday": weekday_name,
        "week": week_number,
        "left": TOTAL_DAYS - day_number,
    }
    return describe   # return 的意思是"把结果交出去"，函数到此结束


# ── 第 4 部分：主程序 ──────────────────────────────────
# 下面这两行是 Python 的标准写法，现在只需记住它的意思：
# "只有直接运行这个文件时才执行下面的代码，被别人 import 时不执行"。
if __name__ == "__main__":

    # date.today() 是一个函数调用，返回今天的日期。
    today = date.today()

    # 调用上面定义的函数，把 today 传进去，结果存进 info 这个变量。
    info = describe_day(today)

    # ── 条件判断：if / elif / else ──
    # 根据第几天，决定说什么话。elif 是 "else if"(否则如果) 的缩写。
    if info["day"] < 1:
        message = "计划还没开始，开课日是 2026 年 10 月 19 日。"
    elif info["day"] > TOTAL_DAYS:
        message = "恭喜！84 天计划已经全部完成了。"
    else:
        # f-string：在引号前面加一个 f，就能在字符串里用 {} 直接插入变量的值。
        # 这是 Python 里最常用的字符串格式化方式，务必掌握。
        message = f"还剩 {info['left']} 天。今天也要写点能跑的东西。"

    # ── 输出到屏幕 ──
    # print() 把括号里的东西打印到屏幕上。
    # "\n" 是换行符。"=" * 46 表示把 = 这个字符重复 46 次，用来画分隔线。
    print("=" * 46)
    print(f"  AI 独立开发者计划 · 进度")
    print("=" * 46)
    print(f"  今天日期  : {today}")
    print(f"  星期      : {info['weekday']}")
    print(f"  第几天    : Day {info['day']} / {TOTAL_DAYS}")
    print(f"  第几周    : 第 {info['week']} 周")
    print("-" * 46)
    print(f"  {message}")
    print("=" * 46)

    # ── 循环：for ──
    # 用一个小进度条直观显示进度。range(10) 生成 0 到 9 共 10 个数字。
    # 下面这行是"列表推导式"，现在看不懂没关系，第 1 周会专门讲。
    # 它的意思是：算出进度百分比，然后决定 10 个格子里有几个填 "█"，其余填 "░"。
    percent = info["day"] / TOTAL_DAYS
    filled = int(percent * 10)
    bar = "█" * filled + "░" * (10 - filled)
    print(f"  进度      : [{bar}] {percent:.1%}")
    print()

    # ── 交互：input() ──
    # input() 会停下来等你在键盘上输入，你输入的内容作为字符串返回。
    name = input("  你叫什么名字？（输入后按回车）：")

    # 字符串.strip() 会去掉首尾的空格，避免用户不小心多打了空格。
    name = name.strip()

    # if/else 的另一种用法：写成一行，叫"三元表达式"。
    # 意思是：如果 name 不是空的，就用 name；否则用 "同学"。
    display_name = name if name else "同学"

    print(f"\n  好的，{display_name}。今天的学习任务在课程表里，19:30 我会提醒你。\n")
