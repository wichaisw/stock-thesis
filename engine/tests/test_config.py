import pytest
import yaml
from pydantic import ValidationError

from shortlist.config import DEFAULT_PATH, Config, editable_fields, load_config


def test_loads_defaults():
    cfg = load_config()
    assert cfg.liquidity.min_avg_traded_value == 10_000_000
    assert cfg.quality.min_quarters == 12
    assert cfg.cdc.approaching_eta_days == 20
    assert cfg.candidates.accepted_states == ["bear-approaching", "just-crossed"]


def test_wrong_type_names_field(tmp_path):
    raw = yaml.safe_load(DEFAULT_PATH.read_text(encoding="utf-8"))
    raw["quality"]["min_roe"] = "high"
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")

    with pytest.raises(ValidationError, match=r"quality\.min_roe"):
        load_config(path)


def test_every_editable_field_is_documented():
    fields = editable_fields()
    assert fields
    for section, name, field in fields:
        assert field.title and field.description, f"{section}.{name}"
        assert field.json_schema_extra["unit"], f"{section}.{name}"


def test_formula_and_reference_fields_are_not_editable():
    keys = {f"{section}.{name}" for section, name, _ in editable_fields()}
    assert not {"cdc.source", "cdc.ap_length", "cdc.fast_length", "cdc.slow_length", "quality.financial_sectors"} & keys
    assert not {k for k in keys if k.startswith(("catalyst.", "batch."))}


def error_locs(changes: dict[str, object]) -> set[str]:
    raw = yaml.safe_load(DEFAULT_PATH.read_text(encoding="utf-8"))
    for key, value in changes.items():
        section, name = key.split(".")
        raw[section][name] = value
    with pytest.raises(ValidationError) as e:
        Config.model_validate(raw)
    return {".".join(map(str, err["loc"])) for err in e.value.errors()}


def test_ocf_positive_cannot_exceed_window():
    assert error_locs({"quality.ocf_window": 4, "quality.ocf_min_positive": 5}) == {"quality.ocf_min_positive"}


def test_max_failed_checks_is_0_to_4():
    assert load_config().quality.max_failed_checks == 2
    assert error_locs({"quality.max_failed_checks": 5}) == {"quality.max_failed_checks"}


@pytest.mark.parametrize("key", ["fair_value.enabled", "candidates.accepted_states"])
def test_choice_lists_need_at_least_one(key):
    assert error_locs({key: []}) == {key}


def test_overrides_replace_defaults(tmp_path):
    path = tmp_path / "config.yaml"
    raw = yaml.safe_load(DEFAULT_PATH.read_text(encoding="utf-8"))
    raw["quality"]["max_de"] = 2.0
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")

    cfg = load_config(path, {"quality.min_roe": 0.08})
    assert cfg.quality.min_roe == 0.08
    assert cfg.quality.max_de == 2.0  # untouched fields keep the YAML default


def test_unknown_or_locked_override_is_skipped(caplog):
    cfg = load_config(overrides={"quality.gone": 1, "cdc.fast_length": 5})
    assert cfg.cdc.fast_length == 12
    assert "quality.gone" in caplog.text and "cdc.fast_length" in caplog.text


def test_min_dividend_yield_default_and_type():
    assert load_config().fair_value.min_dividend_yield == 0.005
    assert error_locs({"fair_value.min_dividend_yield": "low"}) == {"fair_value.min_dividend_yield"}


def test_batch_limits_default_and_reject_wrong_type():
    b = load_config().batch
    assert b.max_consecutive_network_errors == 5
    assert b.max_run_minutes == 20
    assert error_locs({"batch.max_consecutive_network_errors": "many"}) == {"batch.max_consecutive_network_errors"}
    assert error_locs({"batch.max_run_minutes": "long"}) == {"batch.max_run_minutes"}


def test_justified_pbv_defaults():
    cfg = load_config().fair_value
    assert (cfg.cost_of_equity, cfg.terminal_growth) == (0.10, 0.03)
    assert "justified_pbv" in cfg.enabled


@pytest.mark.parametrize("g", [0.10, 0.12])
def test_growth_must_be_below_cost_of_equity(g):
    assert error_locs({"fair_value.cost_of_equity": 0.10, "fair_value.terminal_growth": g}) == {"fair_value.terminal_growth"}


def test_gate_defaults_and_old_median_override_is_skipped(caplog):
    cfg = load_config(overrides={"candidates.min_median_mos": 0.15})
    assert cfg.candidates.gate_methods == ["peer_pe", "justified_pbv"]
    assert cfg.candidates.min_gate_mos == 0.10
    assert "candidates.min_median_mos" in caplog.text


def test_gate_methods_are_not_editable():
    keys = {f"{section}.{name}" for section, name, _ in editable_fields()}
    assert "candidates.gate_methods" not in keys
    assert "candidates.min_gate_mos" in keys


def test_disabling_every_gate_method_is_rejected():
    others = ["pe_median", "pe_minus_1sd", "pbv_median", "dividend_yield_median"]
    assert error_locs({"fair_value.enabled": others}) == {""}  # model-level; the API maps it to fair_value.enabled
    load_config(overrides={"fair_value.enabled": [*others, "peer_pe"]})  # one gate method left is fine
