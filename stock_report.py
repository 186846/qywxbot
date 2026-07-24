"""
美股早报模块 — 数据抓取 + 日报生成
从新浪财经实时抓取美股行情，生成简洁文本式早报
"""
import asyncio
import re
import time
from datetime import datetime

import requests

# ============== 配置 ==============
SINA_API = "https://hq.sinajs.cn/list={}"
HEADERS = {"Referer": "https://finance.sina.com.cn"}
BATCH_SIZE = 10

# ============== 股票列表 ==============
INDICES = {
    "gb_dji":    "道指",
    "gb_ixic":   "纳指",
    "int_sp500": "标普500",
}

# 费城半导体指数
PHLX_SEMI = "gb_sox"

SECTORS = [
    ("▫️美股科技七巨头", [
        ("gb_aapl", "苹果"),     ("gb_msft", "微软"),
        ("gb_googl", "谷歌"),    ("gb_amzn", "亚马逊"),
        ("gb_meta", "Meta"),      ("gb_nvda", "英伟达"),
        ("gb_tsla", "特斯拉"),
    ]),
    ("▫️半导体&存储", [
        ("gb_avgo", "博通"),      ("gb_amd", "超威"),
        ("gb_intc", "英特尔"),    ("gb_qcom", "高通"),
        ("gb_lrcx", "泛林"),      ("gb_klac", "科磊"),
        ("gb_tsm", "台积电"),     ("gb_wdc", "西部数据"),
        ("gb_mu", "美光"),        ("gb_amat", "应用材料"),
        ("gb_arm", "ARM"),
    ]),
    ("▫️光通信", [
        ("gb_aaoi", "应用光电"),  ("gb_lite", "Lumentum"),
        ("gb_glw", "康宁"),
    ]),
    ("▫️油气能源", [
        ("gb_xom", "埃克森美孚"), ("gb_cvx", "雪佛龙"),
        ("gb_bp", "英国石油"),    ("gb_cop", "康菲石油"),
        ("gb_oxy", "西方石油"),   ("gb_tot", "道达尔"),
        ("gb_shel", "壳牌"),
    ]),
    ("▫️中概股", [
        ("gb_baba", "阿里巴巴"),  ("gb_pdd", "拼多多"),
        ("gb_ntes", "网易"),      ("gb_jd", "京东"),
        ("gb_bidu", "百度"),      ("gb_li", "理想汽车"),
        ("gb_bili", "哔哩哔哩"),  ("gb_nio", "蔚来"),
        ("gb_xpev", "小鹏"),      ("gb_tcom", "携程"),
        ("gb_beig", "百济神州"),  ("gb_dada", "叮咚买菜"),
    ]),
]

# 大宗商品 — ETF 兜底
COMMODITIES_ETF = [
    ("gb_gld", "黄金ETF(替代)"), ("gb_slv", "白银ETF(替代)"),
    ("gb_uso", "原油ETF(替代)"),
]

# 大宗商品 — 期货（优先使用）
COMMODITY_FUTURES = {
    "hf_GC":  "COMEX黄金",
    "hf_SI":  "COMEX白银",
    "hf_CL":  "WTI原油",
    "hf_SC":  "布伦特原油",
}


# ============== 数据解析 ==============
def _parse_gb(fields):
    """解析美股个字段"""
    if len(fields) < 3 or not fields[1]:
        return None
    try:
        return {"price": float(fields[1]), "change_pct": float(fields[2])}
    except (ValueError, IndexError):
        return None


def _parse_int(fields):
    """解析指数字段，含变化点数"""
    if len(fields) < 4 or not fields[1]:
        return None
    try:
        change_amt = float(fields[2]) if len(fields) > 2 and fields[2] else 0
        return {
            "price": float(fields[1]),
            "change_pct": float(fields[3]),
            "change_amt": change_amt,
        }
    except (ValueError, IndexError):
        return None


def _parse_hf(fields):
    """解析期货字段 (hf_ 前缀)"""
    if len(fields) < 4 or not fields[1]:
        return None
    try:
        # 期货: 0=名称, 1=现价, 2=昨收(或结算价), 3=开盘...
        price = float(fields[1])
        settle = float(fields[2]) if len(fields) > 2 and fields[2] else 0
        change_pct = ((price - settle) / settle * 100) if settle else 0
        return {"price": price, "change_pct": change_pct}
    except (ValueError, IndexError):
        return None


# ============== 数据获取 ==============
def _fetch_batch(codes: list[str]) -> dict:
    """批量抓取，带重试"""
    url = SINA_API.format(",".join(codes))
    for _ in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.encoding = "gbk"
            text = resp.text
            result = {}
            for code in codes:
                m = re.search(rf'var hq_str_{code}="([^"]*)"', text)
                if not m or not m.group(1).strip():
                    continue
                fields = m.group(1).split(",")
                if code.startswith("hf_"):
                    parsed = _parse_hf(fields)
                elif code.startswith("int_"):
                    parsed = _parse_int(fields)
                else:
                    parsed = _parse_gb(fields)
                if parsed:
                    result[code] = parsed
            if result:
                return result
        except Exception:
            pass
        time.sleep(1)
    return {}


def _fetch_all() -> dict:
    """抓取全部数据（股票+期货+ETF兜底）"""
    all_codes = list(INDICES.keys())
    all_codes.append(PHLX_SEMI)
    for _, stocks in SECTORS:
        for code, _ in stocks:
            all_codes.append(code)

    data = _do_fetch(all_codes)

    # 期货
    futures_codes = list(COMMODITY_FUTURES.keys())
    futures_data = _do_fetch(futures_codes)
    # 用 ETF 兜底期货缺失项
    if not futures_data:
        etf_codes = [c for c, _ in COMMODITIES_ETF]
        futures_data = _do_fetch(etf_codes)
        # 映射 ETF 名
        for code, name in COMMODITIES_ETF:
            if code in futures_data:
                futures_data[code] = {**futures_data[code], "_label": name}
    data.update(futures_data)

    return data


def _do_fetch(codes: list[str]) -> dict:
    data = {}
    total_batches = (len(codes) - 1) // BATCH_SIZE + 1
    for i in range(0, len(codes), BATCH_SIZE):
        batch = codes[i : i + BATCH_SIZE]
        n = i // BATCH_SIZE + 1
        print(f"  [{n}/{total_batches}] fetching {len(batch)} items...")
        data.update(_fetch_batch(batch))
    return data


# ============== 格式化辅助 ==============
def _arrow(pct: float) -> str:
    return "➕" if pct > 0 else "➖"


def _sector_mood(up_count: int, down_count: int, up_stocks=None, down_stocks=None) -> str:
    """根据涨跌分布生成板块情绪标签"""
    total = up_count + down_count
    if total == 0:
        return ""
    ratio = up_count / total

    # 全跌
    if up_count == 0:
        # 平均跌幅 > 4% = 崩盘级别
        if down_stocks:
            avg = sum(abs(p) for _, p in down_stocks) / len(down_stocks)
            if avg >= 4:
                return "全线崩盘"
            if avg >= 2:
                return "普跌"
        return "全线下跌"
    # 全涨
    if down_count == 0:
        if up_stocks:
            avg = sum(p for _, p in up_stocks) / len(up_stocks)
            if avg >= 3:
                return "逆势大涨"
        return "全线飘红"
    # 混合
    if ratio <= 0.3:
        return "普跌"
    if ratio >= 0.7:
        return "普涨"
    return "分化行情"


def _fmt_dir(stocks: list[tuple[str, float]], is_up: bool) -> str:
    """
    单方向格式化：同量级用 、 归组，不同量级用 ｜ 分隔。
    stocks: [(name, pct), ...]  全部同方向（涨或跌）
    """
    if not stocks:
        return ""

    sorted_s = sorted(stocks, key=lambda x: -abs(x[1]))
    thresholds = [10, 5, 3, 2, 1]

    groups = []  # [(names, threshold), ...]
    remaining = sorted_s.copy()
    for t in thresholds:
        g = [s for s in remaining if abs(s[1]) >= t]
        if g:
            groups.append(([s[0] for s in g], t))
            remaining = [s for s in remaining if abs(s[1]) < t]
    if remaining:
        groups.append(([s[0] for s in remaining], 0))  # 0 = 不足 1%

    parts = []
    for names, t in groups:
        n = "、".join(names)
        if t > 0:
            if is_up:
                parts.append(f"{n} ➕＞{t}%")
            else:
                parts.append(f"{n} 跌幅＞{t}%")
        else:
            if is_up:
                # <1% 涨幅：逐个显示精确值
                for s in remaining:
                    parts.append(f"{s[0]} ➕{abs(s[1]):.2f}%")
            else:
                parts.append(f"{n} 小幅下跌（跌幅＜1%）")

    return " ｜ ".join(parts)


def _comm_line(name: str, d: dict, unit: str = "") -> str:
    """大宗商品单行格式化"""
    pct = d["change_pct"]
    a = _arrow(pct)
    price_str = f"{d['price']:.2f}"
    if unit:
        price_str += f"{unit}"
    return f"{name} {a}{abs(pct):.2f}%，报价 {price_str}"


# ============== 日报生成 ==============
def _build_report(data: dict) -> str:
    today = datetime.now().strftime("%m/%d")
    weekday_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    day_cn = weekday_cn[datetime.now().weekday()]
    now_str = datetime.now().strftime("%H:%M")

    if datetime.now().weekday() >= 5:
        return f"✨ 隔夜美股复盘 | {today} {day_cn}\n\n🌙 周末休市中，祝周末愉快！\n\n🕐 {now_str} · 仅供参考"

    lines: list[str] = []
    sep = "━━━━━━━━━━━━━━━━"

    # ── 标题 ──
    lines.append(f"✨ 隔夜美股复盘 | {today} {day_cn} ✨")
    lines.append("")

    # ── 大盘指数 ──
    idx_items = [(name, data[code]["change_pct"])
                 for code, name in INDICES.items() if data.get(code)]
    if idx_items:
        up = sum(1 for _, p in idx_items if p > 0)
        if up == len(idx_items):
            mood = "集体收涨"
        elif up == 0:
            mood = "集体收跌"
        else:
            mood = "涨跌分化"
        lines.append(f"▫️美股三大指数{mood}")
        for name, pct in idx_items:
            lines.append(f"{name} {_arrow(pct)}{abs(pct):.2f}%")
        lines.append("")

    # ── 费城半导体 ──
    sox = data.get(PHLX_SEMI)
    if sox:
        lines.append(f"▫️费城半导体指数 {_arrow(sox['change_pct'])}{abs(sox['change_pct']):.2f}%")
        lines.append("")

    # ── 各板块 ──
    for label, stocks in SECTORS:
        valid = [(name, d["change_pct"])
                 for code, name in stocks if (d := data.get(code))]
        if not valid:
            continue

        up_list = [(n, p) for n, p in valid if p > 0]
        down_list = [(n, p) for n, p in valid if p < 0]
        mood = _sector_mood(len(up_list), len(down_list), up_list, down_list)

        # 标题行带上情绪
        suffix = f" {mood}" if mood else ""
        lines.append(f"{label}{suffix}")

        if down_list:
            lines.append("🔻下跌票")
            lines.append(_fmt_dir(down_list, is_up=False))
        if up_list:
            lines.append("✅上涨票")
            lines.append(_fmt_dir(up_list, is_up=True))

        lines.append("")

    # ── 大宗商品 ──
    comm_items = []
    for code, name in COMMODITY_FUTURES.items():
        d = data.get(code)
        if d:
            label = d.get("_label", name)
            comm_items.append((label, d))
    if comm_items:
        lines.append("▫️大宗商品")
        for label, d in comm_items:
            lines.append(f"  {_comm_line(label, d)}")
        lines.append("")

    return "\n".join(lines)


# ============== 对外接口 ==============
async def generate_report() -> str:
    """异步生成完整美股早报"""
    print("[美股早报] 开始抓取数据...")
    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(None, _fetch_all)
    report = _build_report(data)
    print(f"[美股早报] 生成完成，共 {len(report)} 字")
    return report


async def generate_quick_report() -> str:
    """快速版：仅指数 + 科技七巨头"""
    codes = list(INDICES.keys()) + [PHLX_SEMI]
    for code, _ in SECTORS[0][1]:
        codes.append(code)
    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(None, _do_fetch, codes)
    report = _build_report(data)
    print(f"[美股早报-快速] 生成完成，共 {len(report)} 字")
    return report
