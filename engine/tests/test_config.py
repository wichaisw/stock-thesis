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


def test_max_hold_cannot_be_below_min_hold():
    assert error_locs({"risk_reward.min_hold_months": 3, "risk_reward.max_hold_months": 1}) == {"risk_reward.max_hold_months"}


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
