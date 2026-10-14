import pandas as pd

from shortlist.config import Liquidity, Quality
from shortlist.core import num


def liquidity(prices: pd.DataFrame, cfg: Liquidity) -> dict:
    recent = prices.tail(cfg.window_days)
    avg = (recent["close"] * recent["volume"]).mean()
    passed = bool(avg >= cfg.min_avg_traded_value)
    return {
        "passed": passed,
        "value": num(avg, 0),
        "threshold": cfg.min_avg_traded_value,
        "reason": f"traded value เฉลี่ย {cfg.window_days} วัน {avg / 1e6:,.1f} ลบ./วัน "
        f"({'ผ่าน' if passed else 'ต่ำกว่า'}เกณฑ์ ≥ {cfg.min_avg_traded_value / 1e6:,.0f} ลบ./วัน)",
    }


def _check(name: str, passed: bool | None, value: object, threshold: str, reason: str) -> dict:
    # passed=None means the check was skipped and does not count against the stock
    return {"name": name, "passed": passed, "value": value, "threshold": threshold, "reason": reason}


def evaluate(quarterly: pd.DataFrame, sector: str, cfg: Quality) -> dict:
    reported = quarterly[quarterly["eps"].notna()]
    n = len(reported)
    checks = [
        _check(
            "min_quarters",
            n >= cfg.min_quarters,
            n,
            f"≥ {cfg.min_quarters} ไตรมาส",
            f"มีงบ {n} ไตรมาส" + ("" if n >= cfg.min_quarters else " ประวัติงบไม่พอ"),
        )
    ]
    if n < cfg.min_quarters:
        return {"passed": False, "checks": checks, "inflection": inflection(reported)}

    last = reported.iloc[-1]
    is_financial = sector in cfg.financial_sectors

    roe = roe_ttm(reported)
    checks.append(
        _check(
            "roe",
            roe is not None and roe >= cfg.min_roe,
            roe,
            f"ROE TTM ≥ {cfg.min_roe:.0%}",
            "ข้อมูล ROE ไม่ครบ (ต้องมีกำไรสุทธิและส่วนผู้ถือหุ้นครบ 4 ไตรมาส)"
            if roe is None
            else f"ROE TTM {roe:.1%}",
        )
    )

    if is_financial:
        skip = "ข้ามเพราะเป็นหุ้นการเงิน"
        checks.append(_check("de", None, num(last["de"], 2), f"≤ {cfg.max_de}", skip))
        checks.append(_check("ocf", None, None, f"> 0 อย่างน้อย {cfg.ocf_min_positive}/{cfg.ocf_window}", skip))
    else:
        de = num(last["de"], 2)
        checks.append(
            _check(
                "de",
                de is not None and de <= cfg.max_de,
                de,
                f"≤ {cfg.max_de}",
                "ไม่มีค่า D/E ไตรมาสล่าสุด" if de is None else f"D/E {de:.2f}",
            )
        )
        # a missing OCF counts as not positive: never guess a value
        positive = int((reported["ocf"].tail(cfg.ocf_window) > 0).sum())
        checks.append(
            _check(
                "ocf",
                positive >= cfg.ocf_min_positive,
                positive,
                f"> 0 อย่างน้อย {cfg.ocf_min_positive}/{cfg.ocf_window} ไตรมาส",
                f"OCF เป็นบวก {positive}/{cfg.ocf_window} ไตรมาสล่าสุด",
            )
        )

    profitable = int((reported["net_profit"].tail(cfg.no_loss_window) >= 0).sum())
    checks.append(
        _check(
            "no_loss",
            profitable == cfg.no_loss_window,
            profitable,
            f"ไม่ขาดทุน {cfg.no_loss_window}/{cfg.no_loss_window} ไตรมาส",
            f"มีกำไร {profitable}/{cfg.no_loss_window} ไตรมาสล่าสุด",
        )
    )

    return {
        # min_quarters already passed above; skipped checks (None) do not count as failed
        "passed": sum(c["passed"] is False for c in checks) <= cfg.max_failed_checks,
        "checks": checks,
        "inflection": inflection(reported),
    }


def roe_ttm(reported: pd.DataFrame) -> float | None:
    """Net profit of the last 4 quarters over their average equity.

    thaifin's own ROE annualizes a single quarter, so one unusual quarter could pass the gate.
    """
    last4 = reported.tail(4)
    if len(last4) < 4 or last4[["net_profit", "equity"]].isna().any().any():
        return None
    equity = last4["equity"].mean()
    return num(last4["net_profit"].sum() / equity, 4) if equity > 0 else None


def inflection(reported: pd.DataFrame) -> dict:
    yoy = reported["net_profit_yoy"].tail(2).tolist()
    if len(yoy) == 2 and yoy[1] > 0 and not yoy[0] > 0:
        return {"flag": True, "reason": f"กำไรสุทธิ YoY พลิกจาก {yoy[0]:+.0%} เป็น {yoy[1]:+.0%}"}
    npm = reported["npm"].tail(3).tolist()
    if len(npm) == 3 and npm[0] < npm[1] < npm[2]:
        return {"flag": True, "reason": f"net margin เพิ่มขึ้น 2 ไตรมาสติด ({npm[0]:.1%} → {npm[1]:.1%} → {npm[2]:.1%})"}
    return {"flag": False, "reason": None}
