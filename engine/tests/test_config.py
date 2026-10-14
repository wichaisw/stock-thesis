import pytest
import yaml
from pydantic import ValidationError

from shortlist.config import DEFAULT_PATH, load_config


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
