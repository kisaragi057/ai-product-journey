"""
paipan/api.py —— 八字排盘接口 v0.2（Day 17：把功能变成接口）

先说清「接口」是什么，用你自己的产品讲：
  · app.py 是给【人】看的：浏览器打开，填表，看四个卡片。
  · api.py 是给【程序】用的：它不画图、不排版，只把结果按约定好的格式吐出来。
    未来的小程序前端、你同事的脚本、大模型的工具调用，走的都是这个。
  · endpoint（端点）= 一个地址；route（路由）= 「这个地址接到这段代码」这条规则。
    下面 @app.get("/chart") 就是在写一条路由：有人 GET /chart，就跑下面这个函数。

★ 今天最重要的一条规矩：接口不许自己重算八字。
  它只调用 core.py。同一份事实只允许一个来源（错题 #53）。
  所以文件末尾那条 assert 不是装饰——它在检查「接口吐的」和「直接问 core 的」是否一字不差。

运行：
    .venv/bin/python paipan/api.py
然后：
    浏览器打开  http://127.0.0.1:8001/docs     ← FastAPI 最好用的地方，接口文档自动生成

终端测试（三条可直接复制粘贴——注意 URL 里的中文必须编码，见下方说明）：

    # ① 正常排盘。-G 配 --data-urlencode 会把参数自动百分号编码，最省心：
    curl -sG "http://127.0.0.1:8001/chart" --data-urlencode "date=2000-10-15" --data-urlencode "time=23:30" --data-urlencode "gender=男"

    # ② 契约检查：故意不给 gender，应返回 422 + "Field required"
    curl -s "http://127.0.0.1:8001/chart?date=2000-10-15"

    # ③ 请求体走 UTF-8，中文不用编码：
    curl -s -X POST "http://127.0.0.1:8001/chart" -H "Content-Type: application/json" -d '{"date":"2000-10-15","time":"23:30","gender":"女","name":"张三"}'

★ 为什么不能直接写 curl "...&gender=男"：HTTP 请求行只允许 ASCII（RFC 3986），
  中文必须百分号编码（男 = %E7%94%B7）。写成裸中文会被 uvicorn 在【协议层】拒掉，
  返回 400「Invalid HTTP request received.」——请求根本没进 FastAPI，跟你写的代码无关。
  浏览器和前端框架会自动编码，所以用户看不见；但脚本和大模型工具调用会踩。

端口用 8001，因为 8000 是 app.py（网页版）的。两个服务可以同时跑，端口不能撞。
"""

from datetime import datetime

import uvicorn
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core import (GAN_WX, ZI_SECT, build_ec, compute_pillars, count_wx,
                  is_yang, lunar_date_str, shichen_of)

app = FastAPI(title="八字排盘 API", version="0.2",
              description="只算四柱、五行（本气 + 藏干两个口径）。不含大运、流年、真太阳时、解读。")

TIME_FMT = "%H:%M"

# ── 性别的规则只写一遍，GET 和 POST 都从这里取 ──
# 为什么不给默认值：大运顺行还是逆行由性别决定，猜一个可能把整个盘的大运方向弄反。
# 为什么不在两处各写一遍正则：今天刚踩过的坑——默认值写两处，改一处忘一处，
# 于是 GET 收到空串、POST 收到「男」，同一个人两个答案（错题 #53）。
GENDER_PATTERN = r"^(男|女)$"
GENDER_DESC = "性别。必填：大运顺逆取决于它，不猜默认值。合法值：男 / 女"


def parse_when(date_str: str, time_str: str | None):
    """把输入的日期/时间文本变成 datetime。返回 (dt, 时辰是否未知)。

    业务错误一律抛 ValueError，由路由翻成 400 —— 不用 500，那是「服务器炸了」的意思，
    而这里是「你给的东西我看不懂」，两回事。
    """
    if not date_str:
        raise ValueError("date 不能为空")
    if not time_str:                                  # 空串或没给 → 时辰未知
        dt = datetime.strptime(f"{date_str} 12:00", "%Y-%m-%d %H:%M")
        return dt, False
    try:
        dt = datetime.strptime(f"{date_str} {time_str.strip()}", f"%Y-%m-%d {TIME_FMT}")
    except ValueError:
        raise ValueError(f"日期或时间格式不对：date={date_str!r} time={time_str!r}"
                         "（应为 YYYY-MM-DD 和 HH:MM）")
    return dt, True


def build_payload(date_str: str, time_str: str | None, name: str, gender: str) -> dict:
    """接口的唯一产出逻辑。所有 endpoint 都调它，保证三种调用方式给出同一个 JSON。"""
    dt, time_known = parse_when(date_str, time_str)
    pillars = compute_pillars(dt)                     # [年, 月, 日, 时]
    ec = build_ec(dt)

    if not time_known:
        pillars = pillars[:3]                         # 时辰未知 → 只有三柱

    a = count_wx(pillars, hidden=False)               # 口径 A：本气
    b = count_wx(pillars, hidden=True)                # 口径 B：含藏干
    day_gan = pillars[2][0]

    warnings = []
    if not time_known:
        # 昨天定的产品口径：不确定时辰就【说出来】，不要装作算得出
        nxt = compute_pillars(dt.replace(hour=23, minute=30))[2]
        warnings.append(
            f"时辰未知，日柱按当日排。若实际出生于 23:00-24:00，日柱应为「{nxt}」（早子时派）"
        )

    return {
        "input": {"date": dt.strftime("%Y-%m-%d"),
                  "time": None if not time_known else dt.strftime(TIME_FMT),
                  "time_known": time_known, "name": name or "匿名", "gender": gender},
        "pillars": {"year": pillars[0], "month": pillars[1],
                    "day": pillars[2], "hour": pillars[3] if time_known else None},
        "shichen": None if not time_known else shichen_of(dt.hour),
        "day_master": {"gan": day_gan, "wuxing": GAN_WX[day_gan],
                       "yinyang": "阳" if is_yang(day_gan) else "阴"},
        "wuxing_benqi": a, "wuxing_canggan": b,
        "totals": {"benqi": sum(a.values()), "canggan": sum(b.values())},
        "lunar_date": lunar_date_str(dt),
        "convention": {"zi_hour_school": "早子时派（23点后日柱进次日）", "sect": ZI_SECT,
                       "year_boundary": "立春（精确到分钟）"},
        "warnings": warnings,
    }


class ChartRequest(BaseModel):
    """请求体的契约。写在这里等于同时得到：校验 + 文档 + 类型提示，三件事一份代码。"""
    date: str = Field(description="公历日期，格式 YYYY-MM-DD", examples=["2000-10-15"])
    time: str | None = Field(default=None, description="公历时间 HH:MM；留空表示时辰未知")
    name: str = Field(default="", max_length=40, description="姓名，仅回显用")
    gender: str = Field(..., pattern=GENDER_PATTERN, description=GENDER_DESC)


def bad_request(msg: str):
    return JSONResponse(status_code=400, content={"error": msg})


@app.get("/health")
def health():
    """活着吗。上线以后运维、监控、你自己的脚本，第一个问的都是这里。"""
    return {"ok": True, "service": "paipan-api", "version": "0.2", "sect": ZI_SECT}


@app.get("/chart")
def chart_get(date: str, time: str | None = None, name: str = "",
              gender: str = Query(..., pattern=GENDER_PATTERN, description=GENDER_DESC)):
    """查询参数版：参数挂在 URL 后面。适合「一次性看看」「发给朋友自己改日期」。"""
    try:
        return build_payload(date, time, name, gender)
    except ValueError as e:
        return bad_request(str(e))


@app.get("/chart/{date_str}")
def chart_path(date_str: str, time: str | None = None,
               gender: str = Query(..., pattern=GENDER_PATTERN, description=GENDER_DESC)):
    """路径参数版：日期直接当地址的一部分。REST 风格，给「某个资源」用的写法。

    注意 date_str 里的横线它不解析，整段当一个字符串收下 —— 所以 YYYY-MM-DD 能用，
    但 2000/10/15 这种带斜杠的会被当成两层路径，直接 404。这是路径参数的边界，不是 bug。
    """
    try:
        return build_payload(date_str, time, "", gender)
    except ValueError as e:
        return bad_request(str(e))


@app.post("/chart")
def chart_post(req: ChartRequest):
    """请求体版：参数装在 JSON 里 POST 进来。字段多、含敏感信息、要给机器调用时用它。"""
    try:
        return build_payload(req.date, req.time, req.name, req.gender)
    except ValueError as e:
        return bad_request(str(e))


if __name__ == "__main__":
    # 起服务前先自查一遍：接口吐的东西必须等于直接问 core 的结果
    p = build_payload("2000-10-15", "23:30", "测试", "男")
    direct = compute_pillars(datetime(2000, 10, 15, 23, 30))
    assert [p["pillars"]["year"], p["pillars"]["month"], p["pillars"]["day"],
            p["pillars"]["hour"]] == direct, "接口和 core 分叉了！"
    assert p["totals"]["benqi"] == 8, "本气口径不是 8 个字"
    print("契约自查通过：接口 == core，本气 8 字")
    print("→ http://127.0.0.1:8001/docs  （Ctrl+C 停止）")
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")
