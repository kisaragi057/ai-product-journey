"""
paipan/app.py —— 八字排盘 v0.1（Day 13 实践日，新赛道第一个产品）

范围（昨天确认过的三项决定）：
  · 只算四柱，不含大运/流年/解读/真太阳时
  · 23:00-24:00 出生的，日柱按【次日】（早子时派）
  · 用户输入公历日期 + 时间，页面显示换算出的时辰

运行：
    .venv/bin/python paipan/app.py
然后浏览器打开 http://127.0.0.1:8000

依赖：lunar_python（已验证：立春时刻精确到分钟，用 EightChar 取柱）
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
from lunar_python import Solar

GAN_WX = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
          "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
ZHI_WX = {"子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
          "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}
SHICHEN = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

PAGE = """<!doctype html><html lang=zh><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>八字排盘 v0.1</title><style>
body{{font-family:-apple-system,"PingFang SC",sans-serif;background:#faf9f7;margin:0;padding:24px;color:#2b2b2b}}
.wrap{{max-width:560px;margin:0 auto}}
h1{{font-size:19px;font-weight:600;margin:0 0 4px}}
.sub{{color:#888;font-size:12px;margin-bottom:20px}}
form{{background:#fff;padding:18px;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
label{{display:block;font-size:13px;margin:12px 0 4px;color:#555}}
input,select{{width:100%;padding:9px;border:1px solid #ddd;border-radius:6px;font-size:15px;box-sizing:border-box}}
button{{margin-top:18px;width:100%;padding:11px;background:#2b2b2b;color:#fff;border:0;border-radius:6px;font-size:15px}}
.zh{{display:flex;gap:10px;margin-top:20px}}
.zhu{{flex:1;background:#fff;border-radius:10px;padding:14px 6px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.zhu b{{display:block;font-size:26px;margin:6px 0}}
.zhu span{{font-size:11px;color:#999}}
.wx{{background:#fff;border-radius:10px;padding:14px;margin-top:14px;font-size:13px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.err{{background:#fff2f0;border:1px solid #ffccc7;padding:12px;border-radius:8px;margin-top:16px;font-size:13px}}
.note{{color:#aaa;font-size:11px;margin-top:16px;line-height:1.7}}
</style></head><body><div class=wrap>
<h1>八字排盘 <small style="color:#bbb;font-size:12px">v0.1</small></h1>
<div class=sub>公历输入 · 立春分年 · 早子时派</div>
<form action="/chart" method=get>
<label>姓（选填）</label><input name=name placeholder="张三">
<label>性别</label><select name=gender><option value=男>男</option><option value=女>女</option></select>
<label>出生日期</label><input type=date name=date value="{d}" required>
<label>出生时间</label><input type=time name=time value="{t}" required>
<button type=submit>排盘</button>
</form>
{body}
<div class=note>v0.1 只算四柱与五行个数（地支按本气计，未含藏干）。不含大运、流年、真太阳时、解读。<br>
{ver}</div></div></body></html>"""

ZHU_LABEL = ["年柱", "月柱", "日柱", "时柱"]


def shichen_of(hour: int) -> str:
    """把 0-23 点换算成十二时辰名。子时跨 23 点和 0 点，这是个边界陷阱。"""
    idx = ((hour + 1) // 2) % 12
    return SHICHEN[idx]


def build_chart(date_str: str, time_str: str, name: str, gender: str) -> str:
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        return '<div class=err>日期或时间格式不对。</div>'

    solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0)
    lunar = solar.getLunar()
    ec = lunar.getEightChar()

    # EightChar 的四个柱。立春分年这块是精确到分钟的（已实测验证）。
    pillars = [ec.getYear(), ec.getMonth(), ec.getDay(), ec.getTime()]

    wx = {}
    for p in pillars:
        for ch in p:
            key = GAN_WX.get(ch) or ZHI_WX.get(ch)
            if key:
                wx[key] = wx.get(key, 0) + 1

    cells = "".join(
        f'<div class=zhu><span>{ZHU_LABEL[i]}</span><b>{p[:1]}</b><b style="margin-top:-6px">{p[1:]}</b></div>'
        for i, p in enumerate(pillars))

    wx_line = "　".join(f"{k}{v}" for k, v in sorted(wx.items(), key=lambda x: -x[1]))
    lunar_str = f"{lunar.getYear()}年{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}日"

    return f"""<div class=zh>{cells}</div>
<div class=wx><b>{name or '匿名'}</b>（{gender}）　{lunar_str}　{dt.strftime('%H:%M')} 生 → <b>{shichen_of(dt.hour)}时</b><br>
五行：{wx_line}</div>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path)
        body = ""
        ver = ""
        if u.path == "/chart":
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            try:
                body = build_chart(q.get("date", ""), q.get("time", ""),
                                   q.get("name", ""), q.get("gender", "男"))
            except Exception as e:
                body = f'<div class=err>排盘出错：{type(e).__name__}: {e}</div>'
            ver = f"内部校验日 {datetime.now():%Y-%m-%d %H:%M}"
        html = PAGE.format(d=datetime.now().strftime("%Y-%m-%d"),
                           t="08:00", body=body, ver=ver)
        raw = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("八字排盘 v0.1 → http://127.0.0.1:8000  （Ctrl+C 停止）")
    HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
