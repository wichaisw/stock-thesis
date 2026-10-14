import numpy as np
import pandas as pd

from shortlist.config import load_config
from shortlist.core import quality

CFG = load_config()


def quarters(n: int = 12, **overrides) -> pd.DataFrame:
    """A healthy company; overrides replace the latest values of a column."""
    df = pd.DataFrame(
        {
            "eps": [1.0] * n,
            "net_profit": [1e9] * n,
            "net_profit_yoy": [0.05] * n,
            "roe": [0.14] * n,
            "de": [0.8] * n,
            "ocf": [5e8] * n,
            "npm": [0.10] * n,
            "bvps": [10.0] * n,
            "dividend_yield": [0.03] * n,
            "close": [15.0] * n,
        },
        index=[f"q{i}" for i in range(n)],
    )
    for col, latest in overrides.items():
        df.iloc[-len(latest) :, df.columns.get_loc(col)] = latest
    return df


def check(result: dict, name: str) -> dict:
    return next(c for c in result["checks"] if c["name"] == name)


def test_low_liquidity_fails_with_value_and_threshold():
    prices = pd.DataFrame({"close": [10.0] * 20, "volume": [400_000.0] * 20})
    r = quality.liquidity(prices, CFG.liquidity)
    assert not r["passed"]
    assert r["value"] == 4_000_000
    assert "4.0" in r["reason"] and "10" in r["reason"]


def test_too_few_quarters_fails():
    r = quality.evaluate(quarters(5), "Commerce", CFG.quality)
    assert not r["passed"]
    assert "ประวัติงบไม่พอ" in check(r, "min_quarters")["reason"]


def test_healthy_company_passes():
    r = quality.evaluate(quarters(), "Commerce", CFG.quality)
    assert r["passed"]
    assert all(c["passed"] for c in r["checks"])


def test_high_de_fails_with_value():
    r = quality.evaluate(quarters(de=[2.3]), "Commerce", CFG.quality)
    assert not r["passed"]
    de = check(r, "de")
    assert de["passed"] is False and de["value"] == 2.3


def test_missing_ocf_counts_as_not_positive():
    r = quality.evaluate(quarters(ocf=[np.nan]), "Commerce", CFG.quality)
    assert check(r, "ocf")["value"] == 3

    r = quality.evaluate(quarters(ocf=[-1.0, np.nan]), "Commerce", CFG.quality)
    assert check(r, "ocf")["passed"] is False
    assert not r["passed"]


def test_loss_quarter_fails():
    r = quality.evaluate(quarters(net_profit=[-1e8, 1e9]), "Commerce", CFG.quality)
    assert check(r, "no_loss")["passed"] is False


def test_bank_skips_de():
    r = quality.evaluate(quarters(de=[5.8], ocf=[-1.0, -1.0]), "Banking", CFG.quality)
    assert r["passed"]
    de = check(r, "de")
    assert de["passed"] is None and "หุ้นการเงิน" in de["reason"]


def test_profit_turning_positive_flags_inflection():
    r = quality.evaluate(quarters(net_profit_yoy=[-0.12, 0.08]), "Commerce", CFG.quality)
    assert r["inflection"]["flag"]


def test_rising_margin_flags_inflection():
    r = quality.evaluate(quarters(npm=[0.08, 0.09, 0.10]), "Commerce", CFG.quality)
    assert r["inflection"]["flag"]


def test_no_inflection_still_passes():
    r = quality.evaluate(quarters(), "Commerce", CFG.quality)
    assert r["passed"]
    assert not r["inflection"]["flag"]
