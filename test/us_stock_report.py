#!/usr/bin/env python3
"""
每日美股大型科技股早报推送 — 小红书精美排版
覆盖：指数、科技巨头、半导体、存储、光通信、SaaS、互联网、中概股、油气、贵金属
"""

import requests
import re
import time
from datetime import datetime

# ============== 配置 ==============
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=09d6c34e-5f20-4387-a820-9b746f6acc12"
SINA_API = "https://hq.sinajs.cn/list={}"
HEADERS = {"Referer": "https://finance.sina.com.cn"}
BATCH_SIZE = 10

# ============== 股票列表 ==============

INDICES = {
    "int_sp500": "标普500",
    "gb_ixic":   "纳斯达克",
    "gb_dji":    "道琼斯",
}

SECTORS = [
    ("💎 大型科技股", [
        ("gb_aapl", "苹果", "AAPL"),     ("gb_msft", "微软", "MSFT"),
        ("gb_googl", "谷歌", "GOOGL"),    ("gb_amzn", "亚马逊", "AMZN"),
        ("gb_meta", "Meta", "META"),      ("gb_nvda", "英伟达", "NVDA"),
        ("gb_tsla", "特斯拉", "TSLA"),    ("gb_orcl", "甲骨文", "ORCL"),
    ]),
    ("🔬 半导体芯片", [
        ("gb_avgo", "博通", "AVGO"),      ("gb_amd", "AMD", "AMD"),
        ("gb_intc", "英特尔", "INTC"),    ("gb_qcom", "高通", "QCOM"),
        ("gb_stm", "意法半导体", "STM"),  ("gb_lrcx", "泛林", "LRCX"),
        ("gb_klac", "科磊", "KLAC"),      ("gb_tsm", "台积电", "TSM"),
    ]),
    ("💾 存储概念", [
        ("gb_wdc", "西部数据", "WDC"),    ("gb_stx", "希捷", "STX"),
        ("gb_mu", "美光", "MU"),          ("gb_amat", "应用材料", "AMAT"),
    ]),
    ("📡 光通信", [
        ("gb_lite", "Lumentum", "LITE"),  ("gb_aaoi", "应用光电", "AAOI"),
        ("gb_glw", "康宁", "GLW"),
    ]),
    ("☁️ 云计算 & SaaS", [
        ("gb_crm", "Salesforce", "CRM"),  ("gb_adbe", "Adobe", "ADBE"),
        ("gb_now", "ServiceNow", "NOW"),  ("gb_snow", "Snowflake", "SNOW"),
        ("gb_crwd", "CrowdStrike", "CRWD"), ("gb_pltr", "Palantir", "PLTR"),
    ]),
    ("🌐 互联网 & 平台", [
        ("gb_nflx", "奈飞", "NFLX"),      ("gb_uber", "Uber", "UBER"),
        ("gb_abnb", "Airbnb", "ABNB"),    ("gb_shop", "Shopify", "SHOP"),
        ("gb_spot", "Spotify", "SPOT"),   ("gb_snap", "Snap", "SNAP"),
    ]),
    ("🐉 中概股", [
        ("gb_baba", "阿里巴巴", "BABA"),  ("gb_pdd", "拼多多", "PDD"),
        ("gb_ntes", "网易", "NTES"),      ("gb_jd", "京东", "JD"),
        ("gb_futu", "富途", "FUTU"),      ("gb_tcom", "携程", "TCOM"),
        ("gb_bidu", "百度", "BIDU"),      ("gb_li", "理想汽车", "LI"),
        ("gb_bili", "哔哩哔哩", "BILI"),  ("gb_nio", "蔚来", "NIO"),
        ("gb_xpev", "小鹏", "XPEV"),
    ]),
]

OIL_GAS = [
    ("gb_xom", "埃克森美孚", "XOM"),    ("gb_cvx", "雪佛龙", "CVX"),
    ("gb_bp", "英国石油", "BP"),         ("gb_cop", "康菲石油", "COP"),
]

COMMODITIES = [
    ("gb_gld", "黄金ETF", "GLD"),   ("gb_slv", "白银ETF", "SLV"),
    ("gb_uso", "原油ETF", "USO"),
]

# ============== 数据获取 (保持不变) ==============

def parse_gb(fields):
    if len(fields) < 3 or not fields[1]:
        return None
    try:
        return {"price": float(fields[1]), "change_pct": float(fields[2])}
    except (ValueError, IndexError):
        return None

def parse_int(fields):
    if len(fields) < 4 or not fields[1]:
        return None
    try:
        return {"price": float(fields[1]), "change_pct": float(fields[3])}
    except (ValueError, IndexError):
        return None

def fetch_batch(codes):
    url = SINA_API.format(",".join(codes))
    result = {}
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.encoding = "gbk"
            text = resp.text
            for code in codes:
                m = re.search(rf'var hq_str_{code}="([^"]*)"', text)
                if not m or not m.group(1).strip():
                    continue
                fields = m.group(1).split(",")
                parsed = parse_gb(fields) if code.startswith("gb_") else parse_int(fields)
                if parsed:
                    result[code] = parsed
            if result:
                return result
        except Exception:
            pass
        time.sleep(1)
    return result

def fetch_all():
    all_codes = list(INDICES.keys())
    for _, stocks in SECTORS:
        for code, _, _ in stocks:
            all_codes.append(code)
    for code, _, _ in OIL_GAS:
        all_codes.append(code)
    for code, _, _ in COMMODITIES:
        all_codes.append(code)

    data = {}
    total_batches = (len(all_codes) - 1) // BATCH_SIZE + 1
    for i in range(0, len(all_codes), BATCH_SIZE):
        batch = all_codes[i:i + BATCH_SIZE]
        n = i // BATCH_SIZE + 1
        print(f"  [{n}/{total_batches}] {len(batch)} items...")
        data.update(fetch_batch(batch))
    return data

# ============== 小红书风格消息生成 ==============

def stock_icon(pct):
    """根据涨跌返回不同 emoji"""
    if pct > 2:
        return "🚀"
    elif pct > 0.5:
        return "📈"
    elif pct > 0:
        return "🔺"
    elif pct < -2:
        return "💧"
    elif pct < -0.5:
        return "📉"
    elif pct < 0:
        return "🔻"
    else:
        return "➖"


def fmt_stock_xhs(data, ticker, show_price=True):
    """小红书格式:   📈 $AAPL  327.74  +0.11%"""
    if not data:
        return f"⚪ `${ticker}` ┄┄ N/A"
    pct = data["change_pct"]
    icon = stock_icon(pct)
    if show_price:
        return f"{icon} `${ticker}`  {data['price']:.2f}  {pct:+.2f}%"
    else:
        return f"{icon} `${ticker}`  {pct:+.2f}%"


def build_progress_bar(pct, total_up, total_valid):
    """制作可视化涨跌比例条"""
    ratio = total_up / total_valid if total_valid > 0 else 0.5
    bar_len = 10
    filled = round(ratio * bar_len)
    # 根据多头比例选颜色
    if ratio >= 0.7:
        bar = "🟩" * filled + "⬜" * (bar_len - filled)
    elif ratio >= 0.4:
        bar = "🟨" * filled + "⬜" * (bar_len - filled)
    else:
        bar = "🟥" * filled + "⬜" * (bar_len - filled)
    return f"{total_up}↑/{total_valid - total_up}↓  {bar}"


def build_message():
    today = datetime.now().strftime("%m/%d")
    now_str = datetime.now().strftime("%H:%M")

    weekday = datetime.now().weekday()
    weekdays_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    day_cn = weekdays_cn[weekday]

    if weekday >= 5:
        return (
            f"## ✨ {today} 隔夜美股早报 ✨\n\n"
            f"> 🌙 周末休市中，好好休息，下周再战！\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {now_str} | 仅供参考 · 不构成投资建议\n"
            f"#美股 #投资 #理财 #财经早报"
        )

    # 获取数据
    print("[1/2] Fetching all market data...")
    data = fetch_all()

    # === 大盘风向标 ===
    idx_items = []
    idx_pcts = []
    for code, name in INDICES.items():
        d = data.get(code)
        if d:
            pct = d["change_pct"]
            icon = "🟢" if pct > 0 else "🔴" if pct < 0 else "⚪"
            idx_pcts.append(pct)
            idx_items.append(f"  {icon} **{name}**  {pct:+.2f}%")

    # 大盘情绪
    up_count = sum(1 for p in idx_pcts if p > 0)
    if up_count == 3:
        mood_line = "三大指数全面飘红，多头氛围浓厚 🔥"
        mood_emoji = "🟢"
    elif up_count >= 2:
        mood_line = "三大指数多数收涨，市场情绪偏暖 ☀️"
        mood_emoji = "🟡"
    elif up_count == 0:
        mood_line = "三大指数全线收跌，避险情绪升温 🌧️"
        mood_emoji = "🔴"
    else:
        mood_line = "三大指数涨跌分化，结构性行情延续 🔄"
        mood_emoji = "🟠"

    # === 各板块 ===
    sector_blocks = []

    for sector_label, stocks in SECTORS:
        sector_data = {code: data.get(code) for code, _, _ in stocks}
        valid = []
        for code, name, ticker in stocks:
            d = sector_data.get(code)
            if d:
                valid.append((code, d, name, ticker))
        if not valid:
            continue

        up_count = sum(1 for v in valid if v[1]["change_pct"] > 0)
        down_count = sum(1 for v in valid if v[1]["change_pct"] < 0)

        # 板块表现条
        bar = build_progress_bar(up_count, up_count, len(valid))

        # 找到涨跌两极
        sorted_all = sorted(valid, key=lambda x: -x[1]["change_pct"])
        top3 = sorted_all[:3]
        bottom3 = sorted_all[-3:]

        block_parts = []

        # 板块标题行
        block_parts.append(f"{sector_label}  {bar}")

        # 明细行 — 紧凑排列，每行展示涨跌两极
        # 前3涨
        up_lines = []
        for _, d, name, ticker in top3:
            pct = d["change_pct"]
            if pct > 0:
                icon = stock_icon(pct)
                up_lines.append(f"{icon} {name} `{ticker}` {pct:+.2f}%")

        # 后3跌
        down_lines = []
        for _, d, name, ticker in reversed(bottom3):
            pct = d["change_pct"]
            if pct < 0:
                icon = stock_icon(pct)
                down_lines.append(f"{icon} {name} `{ticker}` {pct:+.2f}%")

        if up_lines:
            block_parts.append(f"  ▸ 领涨  " + "  ".join(up_lines))
        if down_lines:
            block_parts.append(f"  ▸ 领跌  " + "  ".join(down_lines))

        # 完整列表（紧凑格式）
        all_lines = []
        for _, d, name, ticker in sorted_all:
            icon = stock_icon(d["change_pct"])
            all_lines.append(f"{icon} {name}(`{ticker}`){d['change_pct']:+.2f}%")

        # 按涨跌分组展示
        up_stocks = [l for l in all_lines if l[0] in "🚀📈🔺"]
        down_stocks = [l for l in all_lines if l[0] in "💧📉🔻"]
        flat_stocks = [l for l in all_lines if l[0] == "➖"]

        if up_stocks:
            block_parts.append("  " + " ｜ ".join(up_stocks))
        if down_stocks:
            block_parts.append("  " + " ｜ ".join(down_stocks))
        if flat_stocks:
            block_parts.append("  " + " ｜ ".join(flat_stocks))

        sector_blocks.append("\n".join(block_parts))

    # === 油气 ===
    oil_data = {code: data.get(code) for code, _, _ in OIL_GAS}
    if any(oil_data.values()):
        oil_items = []
        for code, name, ticker in OIL_GAS:
            d = oil_data.get(code)
            if d:
                oil_items.append(fmt_stock_xhs(d, ticker))
        if oil_items:
            oil_block = "⛽ **油气板块**\n" + "\n".join(f"  {x}" for x in oil_items)
            sector_blocks.append(oil_block)

    # === 贵金属 ===
    comm_data = {code: data.get(code) for code, _, _ in COMMODITIES}
    if any(comm_data.values()):
        comm_items = []
        for code, name, ticker in COMMODITIES:
            d = comm_data.get(code)
            if d:
                comm_items.append(fmt_stock_xhs(d, ticker))
        if comm_items:
            comm_block = "🥇 **贵金属 & 大宗商品**\n" + "\n".join(f"  {x}" for x in comm_items)
            sector_blocks.append(comm_block)

    # === 全市场情绪条 ===
    all_sector_data = []
    for _, stocks in SECTORS:
        for code, _, _ in stocks:
            d = data.get(code)
            if d:
                all_sector_data.append(d)
    total_all = len(all_sector_data)
    total_up = sum(1 for d in all_sector_data if d["change_pct"] > 0)
    total_down = sum(1 for d in all_sector_data if d["change_pct"] < 0)

    if total_all > 0:
        up_ratio = total_up / total_all
        if up_ratio >= 0.6:
            market_bar = f"全市场 {total_up}↑ {total_down}↓  多头占优 ✨"
        elif up_ratio >= 0.4:
            market_bar = f"全市场 {total_up}↑ {total_down}↓  多空博弈 ⚖️"
        else:
            market_bar = f"全市场 {total_up}↑ {total_down}↓  空头施压 🌧️"
    else:
        market_bar = ""

    # === 组装消息 ===
    separator = "━━━━━━━━━━━━━━━━━━━━"

    lines = []

    # 标题区域
    lines.append(f"✨ **隔夜美股复盘** | {today} {day_cn} ✨")
    lines.append("")
    lines.append(f"> ☀️ 早安理财人！今日美股复盘已送达～")
    lines.append(f"> {mood_emoji}  {mood_line}")
    lines.append("")

    # 大盘风向标
    lines.append(f"📊 **大盘风向标**")
    lines.append("")
    for item in idx_items:
        lines.append(item)
    lines.append("")

    # 全市场快照
    if market_bar:
        lines.append(f"🎯 {market_bar}")
        lines.append("")

    lines.append(separator)
    lines.append("")

    # 热门板块
    lines.append("🔥 **热门板块速递**")
    lines.append("")

    for block in sector_blocks:
        lines.append(block)
        lines.append("")

    lines.append(separator)
    lines.append("")

    # 免责声明
    lines.append(f"> 🕐 更新时间：{now_str}（北京时间）")
    lines.append(f"> 📊 数据来源：新浪财经")
    lines.append(f"> ⚠️ 以上内容仅供参考，不构成投资建议")
    lines.append("")

    # 小红书香号标签
    lines.append("#美股 #财经早报 #投资 #理财 #美股复盘 #科技股 #每日打卡")

    return "\n".join(lines)


def send(msg):
    payload = {"msgtype": "markdown", "markdown": {"content": msg}}
    try:
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=15)
        r = resp.json()
        ok = r.get("errcode") == 0
        print(f"[{datetime.now()}] {'[OK]' if ok else '[FAIL] ' + str(r)}")
        return ok
    except Exception as e:
        print(f"[{datetime.now()}] [ERR] {e}")
        return False


def main():
    print(f"[{datetime.now()}] [START]")
    try:
        msg = build_message()
        ok = send(msg)
        if not ok:
            # fallback: 纯文本
            requests.post(WEBHOOK_URL, json={
                "msgtype": "text",
                "text": {"content": "US market recap push failed."}
            }, timeout=10)
        print(f"[{datetime.now()}] [DONE]")
    except Exception as e:
        print(f"[{datetime.now()}] [FATAL] {e}")
        requests.post(WEBHOOK_URL, json={
            "msgtype": "text",
            "text": {"content": f"Push error: {e}"}
        }, timeout=10)


if __name__ == "__main__":
    main()
