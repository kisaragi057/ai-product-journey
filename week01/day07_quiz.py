rows = [
    {"类别": "边框", "金额": 80000},
    {"类别": "玻璃", "金额": 60000},
    {"类别": "胶膜", "金额": 30000},
    {"类别": "玻璃", "金额": 90000},
]
totals = {}
for r in rows:
    totals[r["类别"]] = totals.get(r["类别"], 0) + r["金额"]

big = [k for k, v in totals.items() if v > 40000]

for name in sorted(big, key=lambda k: totals[k], reverse=True):
    print(f"{name}: {totals[name]:,}")
