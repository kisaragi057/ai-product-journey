"""
day01_四个疑问.py —— 把 Day 1 那四个看不懂的点，用可运行的代码讲清楚

运行方式（在项目根目录下）：
    .venv/bin/python week01/day01_四个疑问.py

建议：先自己预测每一段的输出，再运行验证。预测错了的地方，就是你还不懂的地方。
"""

from datetime import date

LINE = "=" * 60


# ══════════════════════════════════════════════════════════
# 疑问 1：if __name__ == "__main__": 到底在判断什么？
# ══════════════════════════════════════════════════════════
#
# 你的回答：「判断是否是主程序，直接运行才执行，被 import 时不执行」—— 完全正确。
#
# 补上机制：__name__ 是 Python 自动塞进每个文件里的一个内置变量，你不用定义它。
#   - 你直接运行  python xxx.py     → Python 把 __name__ 设成字符串 "__main__"
#   - 别人写      import xxx        → Python 把 __name__ 设成字符串 "xxx"（模块名）
# 所以那句 if 其实就是在问：「我是被直接运行的，还是被别人导入的？」

print(LINE)
print("疑问 1：__name__ 是什么")
print(LINE)
print(f"  现在这个文件是被直接运行的，所以 __name__ = {__name__!r}")
print(f"  它等于 '__main__' 吗？  {__name__ == '__main__'}")
print()
print("  对比一下：我们导入 datetime 模块，看看它的 __name__ 是什么")
import datetime as _dt_module
print(f"  datetime 模块的 __name__ = {_dt_module.__name__!r}")
print("  ↑ 它是被 import 进来的，所以 __name__ 是模块名，不是 '__main__'")
print()
print("  【为什么重要】第 3 周你会写很多模块，里面有函数给别人 import。")
print("  如果没有这个 if 保护，别人一 import 你的文件，里面的 input() 就会弹出来")
print("  等他输入，程序直接卡死。这个 if 就是防止这件事的。")
print()


# ══════════════════════════════════════════════════════════
# 疑问 2：bar = "█" * filled + "░" * (10 - filled)
# ══════════════════════════════════════════════════════════
#
# 你的回答：「实心方块是学习天数/总天数，空心方块是 1-前面的比例」
# 意思对了一半，但机制说错了。真正的关键是两个：
#   (1) 字符串可以用 * 数字 来「重复」—— 这是你没提到的核心
#   (2) filled 是一个 0~10 的整数（格子个数），不是比例
#
# 我们把计算过程一步步打印出来看。

print(LINE)
print("疑问 2：进度条是怎么画出来的")
print(LINE)

TOTAL_DAYS = 84

# 我们挑几个不同的天数来看，这样规律最明显
for test_day in [1, 8, 42, 84]:
    # 第 1 步：算比例。结果是一个 0 到 1 之间的小数。
    percent = test_day / TOTAL_DAYS

    # 第 2 步：把小数放大 10 倍，然后 int() 砍掉小数部分，得到 0~10 的整数。
    # int() 不是四舍五入，是直接「砍掉」小数，所以 0.99 也会变成 0。
    filled = int(percent * 10)

    # 第 3 步：剩下几个空格子。
    empty = 10 - filled

    # 第 4 步：字符串乘法 —— 这是真正的关键。
    # "█" * 3 的意思是「把 █ 这个字符重复 3 次」，得到 "███"。
    solid_part = "█" * filled
    hollow_part = "░" * empty

    # 第 5 步：两个字符串用 + 拼接（字符串的 + 是「接起来」，不是数学加法）。
    bar = solid_part + hollow_part

    print(f"  Day {test_day:>2} : percent={percent:.4f}  →  percent*10={percent*10:.2f}"
          f"  →  filled=int(...)={filled}  →  empty={empty}")
    print(f"           \"{bar}\"   ← \"{solid_part}\" + \"{hollow_part}\"")
    print()

print("  【纠正】filled 不是比例，它是「实心格子的个数」，一个 0 到 10 的整数。")
print("  【核心】\"█\" * filled 是字符串重复运算，不是乘法算数值。")
print("  【验证】下面直接看字符串乘法：")
print(f'           "█" * 0   = {"█" * 0!r}      ← 重复 0 次，得到空字符串')
print(f'           "█" * 1   = {"█" * 1!r}')
print(f'           "█" * 5   = {"█" * 5!r}')
print(f'           "ab" * 3  = {"ab" * 3!r}   ← 整个字符串重复，不是单个字符')
print(f'           "█" * 3 + "░" * 2  = {"█" * 3 + "░" * 2!r}   ← 这就是进度条的原理')
print(f'           "=" * 60  = 就是本文件里那些分隔线的来历')
print()


# ══════════════════════════════════════════════════════════
# 疑问 3：describe["day"] 这种方括号取值是怎么回事？
# ══════════════════════════════════════════════════════════
#
# 你的回答：「方括号取值是调用参数」—— 这个是错的，而且是必须马上纠正的错误。
#
# 记住这个区分，Python 里三种括号各司其职：
#   圆括号 ( )  →  调用函数、传参数
#   方括号 [ ]  →  从「容器」里取东西（字典按键取，列表按位置取）
#   花括号 { }  →  定义字典/集合

print(LINE)
print("疑问 3：方括号不是调用参数（这是必须纠正的一点）")
print(LINE)

# ── 字典：用「键」取值 ──
# describe 是一个字典，里面有几对「键: 值」
describe = {"day": 1, "weekday": "周一", "week": 1}

print("  【字典 dict】用花括号 {} 定义，存的是「键 → 值」的对应关系")
print(f"    describe = {describe}")
print(f'    describe["day"]     = {describe["day"]!r}   ← 取出键为 "day" 的那个值')
print(f'    describe["weekday"] = {describe["weekday"]!r}   ← 取出键为 "weekday" 的值')
print("    方括号里放的是「键名」（一个字符串），不是位置编号")
print()

# ── 列表：用「位置」取值 ──
weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

print("  【列表 list】用方括号 [] 定义，存的是一串有顺序的东西")
print(f"    weekday_names = {weekday_names}")
print(f"    weekday_names[0] = {weekday_names[0]!r}   ← 第 0 个（编号从 0 开始，不是 1）")
print(f"    weekday_names[2] = {weekday_names[2]!r}   ← 第 2 个")
print(f"    weekday_names[-1] = {weekday_names[-1]!r}   ← 负数表示从后往前数，-1 是最后一个")
print("    方括号里放的是「位置编号」（一个整数）")
print()

# ── 圆括号：这才是调用 ──
print("  【圆括号 ()】这个才是「调用」")
print(f"    date.today()      = {date.today()}   ← 调用 date 的 today 方法")
print(f'    print("你好")      ← 调用 print 函数，括号里放的是「参数」')
print(f"    len(weekday_names) = {len(weekday_names)}   ← 调用 len 函数，参数是那个列表")
print()

print("  ┌─────────────────────────────────────────────┐")
print("  │  ( )  圆括号  →  调用函数、传参数            │")
print("  │  [ ]  方括号  →  从容器里取东西              │")
print("  │               字典：按「键名」取             │")
print("  │               列表：按「位置」取             │")
print("  │  { }  花括号  →  定义字典 / 集合             │")
print("  └─────────────────────────────────────────────┘")
print()
print("  【为什么这个区分很要命】所有 API 返回的 JSON 数据都是字典。")
print("  第 8 周你调大模型接口，拿到的东西长这样：")
fake_api_response = {
    "choices": [{"message": {"content": "你好，我是AI"}}],
    "usage": {"total_tokens": 42},
}
print(f"    {fake_api_response}")
print('    要取出回答内容，你得写 response["choices"][0]["message"]["content"]')
print(f'    实际取出来是：{fake_api_response["choices"][0]["message"]["content"]!r}')
print("    方括号套方括号，一层层往里剥。分不清方括号和圆括号，这行代码你根本读不懂。")
print()


# ══════════════════════════════════════════════════════════
# 疑问 4：(day_number - 1) // 7 + 1  为什么不直接写 day_number // 7
# ══════════════════════════════════════════════════════════
#
# 你的回答：「为了整除并向上取整周数，避免周数为7产生错误」—— 完全正确！
#
# 补上精确的说法和验证：
#   // 是「向下取整除法」（floor），它总是往小的方向砍。
#   但我们想要的是「向上取整」（ceil）：第 1 天就该算第 1 周，不是第 0 周。
#   (n - 1) // 7 + 1 就是把向下取整转成向上取整的标准技巧。
#   你说的「周数为7产生错误」，精确地说是：每逢 7 的倍数会被多算一周。

print(LINE)
print("疑问 4：两种写法的对比验证")
print(LINE)

print("  天数    错误写法 n//7    正确写法 (n-1)//7+1    应该是第几周")
print("  " + "-" * 58)
for n in [1, 6, 7, 8, 13, 14, 15, 21, 22, 83, 84]:
    wrong = n // 7
    right = (n - 1) // 7 + 1
    expected = (n + 6) // 7          # 另一种等价的向上取整写法
    mark = "  ✗ 错了" if wrong != right else "  ✓ 碰巧对"
    print(f"  Day {n:<3}      {wrong:<14}{right:<20}{expected}{mark}")

print()
print("  【看第 7 天】错误写法给出 1，但第 7 天应该是第 1 周的最后一天，")
print("              正确写法给出 1 ✓。错误写法在第 7、14、21... 天都会多算一周。")
print("  【看第 1 天】错误写法给出 0 —— 第 0 周，根本不存在。")
print()
print("  【// 和 / 的区别】这个务必记住：")
print(f"    7 / 2  = {7 / 2}    ← 普通除法，结果是浮点数（小数）")
print(f"    7 // 2 = {7 // 2}       ← 整除，砍掉小数部分，结果是整数")
print(f"    7 % 2  = {7 % 2}       ← 取余数，7 除以 2 商 3 余 1")
print(f"    -7 // 2 = {-7 // 2}      ← 注意！负数是向下取整，不是向零取整")
print()

print(LINE)
print("总结：你答对了 1 和 4，第 2 题意思对但机制说错了，第 3 题需要纠正。")
print("把上面这些亲手跑一遍，然后合上文件，自己复述一次第 3 题的三种括号区别。")
print("能复述出来，Day 1 就真正过关了。")
print(LINE)
