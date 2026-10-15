from shortlist.config import load_config
from shortlist.core import candidates, fair_value

CFG = load_config().candidates


def gate(peer: float | None, jpbv: float | None) -> dict:
    items = [{"method": m, "fair_value": 10.0 if v is not None else None, "mos": v, "reason": None if v is not None else "คำนวณไม่ได้"}
             for m, v in (("peer_pe", peer), ("justified_pbv", jpbv))]
    return fair_value.gate(items, ["peer_pe", "justified_pbv"])


def ev(symbol: str, state: str | None = "bear-approaching", eta: float | None = 5, mos: float | None = 0.15,
       quality_ok: bool = True, liquid: bool = True, jpbv: float | None = None, median: float = 0.15) -> dict:
    """`mos` is peer PE's MoS; Justified PBV is not computable unless `jpbv` is given."""
    return {
        "symbol": symbol,
        "liquidity": {"passed": liquid, "reason": "traded value ต่ำ"},
        "quality": {"passed": quality_ok, "checks": [{"passed": quality_ok or False, "reason": "D/E 2.30"}]},
        "fair_value": {"summary": {"median_mos": median}, "gate": gate(mos, jpbv)},
        "cdc": {"state": state, "eta_days": eta, "reason": "ข้อมูลราคาไม่พอ" if state is None else None},
    }


def symbols(evs: list[dict], cfg=CFG) -> list[str]:
    return [e["symbol"] for e in candidates.rank(evs, cfg)]


def test_passing_everything_is_candidate():
    assert symbols([ev("A")]) == ["A"]


def test_good_fundamentals_bad_timing_is_excluded():
    e = ev("A", state="bear-far", eta=None)
    assert symbols([e]) == []
    assert "bear-far" in candidates.inclusion(e, CFG)["reasons"][0]


def test_accepting_all_states_turns_cdc_into_sort_only():
    cfg = CFG.model_copy(update={"accepted_states": ["bear-far", "bear-approaching", "just-crossed", "bull"]})
    evs = [ev("FAR", state="bear-far", eta=None), ev("BULL", state="bull", eta=None, mos=0.3),
           ev("NEAR", eta=3), ev("CROSS", state="just-crossed", eta=None)]
    assert symbols(evs, cfg) == ["CROSS", "NEAR", "BULL", "FAR"]


def test_sorted_by_just_crossed_then_eta_then_mos():
    evs = [ev("B", eta=12), ev("A", eta=4), ev("C", state="just-crossed", eta=None), ev("D", eta=4, mos=0.4)]
    assert symbols(evs) == ["C", "D", "A", "B"]


def test_failing_gates_are_excluded_with_reasons():
    low_mos = ev("A", mos=0.05)
    bad_quality = ev("B", quality_ok=False)
    illiquid = ev("C", liquid=False)
    assert symbols([low_mos, bad_quality, illiquid]) == []
    assert candidates.inclusion(low_mos, CFG)["reasons"] == ["MoS ของ Peer PE 5.0% ต่ำกว่าเกณฑ์ 10%"]
    assert "D/E 2.30" in candidates.inclusion(bad_quality, CFG)["reasons"][0]
    assert "liquidity" in candidates.inclusion(illiquid, CFG)["reasons"][0]


def test_no_manual_event_does_not_exclude():
    e = ev("A") | {"events": []}
    assert symbols([e]) == ["A"]


def test_both_gate_methods_above_threshold():
    assert symbols([ev("A", mos=0.15, jpbv=0.22)]) == ["A"]


def test_one_gate_method_below_threshold_names_it():
    e = ev("A", mos=0.25, jpbv=0.04)
    assert symbols([e]) == []
    assert candidates.inclusion(e, CFG)["reasons"] == ["MoS ของ Justified PBV 4.0% ต่ำกว่าเกณฑ์ 10%"]


def test_one_computable_gate_method_is_enough():
    assert symbols([ev("A", mos=0.12, jpbv=None)]) == ["A"]


def test_no_computable_gate_method_is_excluded_even_with_high_median():
    e = ev("A", mos=None, jpbv=None, median=0.40)
    assert symbols([e]) == []
    assert "ไม่มี gate method ที่คำนวณได้" in candidates.inclusion(e, CFG)["reasons"][0]


def test_median_is_no_longer_a_gate():
    assert symbols([ev("A", mos=0.12, jpbv=0.2, median=-0.05)]) == ["A"]


def test_equal_eta_sorts_by_gate_mos_not_median():
    a = ev("A", mos=0.12, median=0.50)
    b = ev("B", mos=0.30, median=0.20)
    assert symbols([a, b]) == ["B", "A"]
