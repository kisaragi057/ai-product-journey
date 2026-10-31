"""
api_demo.py —— Day 12 产出：调用一个真实公开 API

数据源：https://open.er-api.com（免密钥、可商用、每日更新）
选它的原因：汇率是你手上真实要用的东西——越南报关单金额是 VND，
            报价和记账常用 USD，第 3 周做数据处理时一定绕不开换算。

今天练的四件事：
  ① HTTP GET 请求 + 状态码 + 超时
  ② 响应 JSON 解析成字典，再逐层剥（Day 5 的技能）
  ③ 网络这类边界怎么兜（Day 9 的四类边界里第 ③ 类）
  ④ ★ HTTP 200 ≠ 业务成功 —— 这是今天最值钱的一课

运行（在哪个目录跑都行，因为用了 pathlib）：
    .venv/bin/python week01/api_demo.py
"""

from pathlib import Path
import json
import requests

API_BASE = "https://open.er-api.com/v6/latest/"
TIMEOUT_SECONDS = 10


def fetch_rates(base: str = "USD") -> dict:
    """向汇率 API 请求以 base 为基准的全部汇率。

    参数:
        base: 基准货币代码，例如 "USD"、"CNY"

    返回:
        dict，形如 {"CNY": 6.68, "VND": 25792.4, ...}

    失败时:
        抛 ValueError（带明确原因），不返回空字典 ——
        空字典会让下游算出 0 这种「看起来正常的错数字」。

    ★ 这个函数我已经写完，请你逐行读懂，尤其是三处注释。
    """
    url = API_BASE + base

    try:
        # 【要点 1】timeout 必须给！不给的话服务器不响应，你的程序会【永远卡在那里】。
        # 这是新手最常见的挂死原因，而且现象是「程序没反应」而不是「报错」，很难查。
        resp = requests.get(url, timeout=TIMEOUT_SECONDS)
    except requests.ConnectionError:
        raise ValueError(f"连不上 {url}（网络断了 / 域名解析不了 / 公司墙）") from None
    except requests.Timeout:
        raise ValueError(f"请求超过 {TIMEOUT_SECONDS} 秒没响应") from None

    # 【要点 2】状态码检查。4xx = 你的错，5xx = 服务器的错。
    # 不检查的话，404 的 HTML 错误页会被当 JSON 去解析，报错信息会非常迷惑。
    resp.raise_for_status()

    data = resp.json()          # 把响应体的 JSON 文本解析成 Python 字典

    # 【要点 3 ★ 今天的重点】HTTP 200 不代表业务成功。
    # 这个 API 失败时也返回 200，只是在 body 里放 {"result": "error", ...}。
    # 如果你只看状态码，就会拿着一个没有 "rates" 的字典继续往下跑。
    if data.get("result") != "success":
        raise ValueError(f"API 返回业务失败：{data.get('error_type') or data}")

    return data["rates"]


# ══════════════════════════════════════════════════════════
# ↓ 下面两个函数留给你填。契约已定好。
# ══════════════════════════════════════════════════════════

def convert(amount: float, from_code: str, to_code: str, rates: dict) -> float:
    converted = amount * rates[to_code]
    return converted
    """把 amount 从 from_code 换算成 to_code。

    参数:
        amount:    金额，例如 12500.50
        from_code: 源货币，例如 "USD"
        to_code:   目标货币，例如 "VND"
        rates:     fetch_rates 返回的字典（基准货币就是 from_code 时才有意义）

    返回:
        float，换算后的金额

    你要处理的一件事:
        如果 to_code 不在 rates 里（比如手滑写了 "VND " 或 "rmb"），
        直接 rates[to_code] 会抛 KeyError。
        → 这里【不要】用 try 兜住，让它抛。为什么？
          想 Day 9 那条分界：**程序写错了要让它响，数据不干净才跳过+报告**。
          币种代码是你在代码里写死的，写错就是 bug，应该当场炸出来。

    提示：用 `if to_code not in rates:` 主动 raise ValueError 并带上可用的币种线索，
         这样报错信息比裸 KeyError 更好读。自己判断要不要这么做，写完说清理由。
    """
    raise NotImplementedError("convert 还没写")


def main() -> None:
    """跑一次完整的：请求 → 解析 → 换算 → 打印。"""
    rates = fetch_rates("USD")          # 以美元为基准

    # 三个真实场景的换算（你的工作里都会遇到）
    cases = [
        (12500.50, "USD", "VND", "越南报关单：FOB 价 1.25 万美元"),
        (12500.50, "USD", "CNY", "记账：折算成人民币成本"),
        (1000.00, "USD", "EUR", "欧洲客户报价"),
    ]

    print(f"以 USD 为基准，共取到 {len(rates)} 个币种")
    print("-" * 62)

    for amount, frm, to, note in cases:
        print(f"{note}：{amount:,.2f} {frm} → ", end="")
        converted = convert(amount, frm, to, rates)
        # TODO 你写：调用 convert，打印出
        #   "越南报关单：FOB 价 1.25 万美元    12,500.50 USD → 322,478,710.00 VND"
        # 格式说明符用 {值:,.2f}（千分位 + 两位小数）
        print(f"{converted:,.2f} {to}")
        raise NotImplementedError("main 里的换算和打印还没写")
    


if __name__ == "__main__":
    main()
