from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

CdcState = Literal["bear-far", "bear-approaching", "just-crossed", "bull"]
FairValueMethod = Literal["pe_median", "pe_minus_1sd", "pbv_median", "dividend_yield_median", "peer_pe"]


class Strict(BaseModel):
    # unknown keys are almost always typos in a hand-edited file
    model_config = ConfigDict(extra="forbid")


class Liquidity(Strict):
    window_days: int
    min_avg_traded_value: float


class Quality(Strict):
    min_quarters: int
    min_roe: float
    max_de: float
    ocf_window: int
    ocf_min_positive: int
    no_loss_window: int
    financial_sectors: list[str]


class FairValue(Strict):
    enabled: list[FairValueMethod]
    lookback_quarters: int
    min_history_points: int
    min_peers: int
    max_pe: float


class Cdc(Strict):
    ap_length: int
    fast_length: int
    slow_length: int
    speed_window: int
    approaching_eta_days: float
    just_crossed_days: int
    min_days: int


class RiskReward(Strict):
    swing_low_days: int
    stop_buffer: float
    min_rrr: float
    min_hold_months: float
    max_hold_months: float


class Candidates(Strict):
    min_median_mos: float
    accepted_states: list[CdcState]


class IndexReview(Strict):
    date: date
    label: str


class Catalyst(Strict):
    horizon_months: int
    quarter_deadline_days: int
    annual_deadline_days: int
    index_reviews: list[IndexReview]
    default_hints: list[str]
    hints: dict[str, list[str]]


class Batch(Strict):
    markets: list[str]
    price_period: str
    price_chunk_size: int
    chunk_delay_seconds: float
    stale_run_minutes: int


class Config(Strict):
    liquidity: Liquidity
    quality: Quality
    fair_value: FairValue
    cdc: Cdc
    risk_reward: RiskReward
    candidates: Candidates
    catalyst: Catalyst
    batch: Batch


def load_config(path: Path = DEFAULT_PATH) -> Config:
    return Config.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
