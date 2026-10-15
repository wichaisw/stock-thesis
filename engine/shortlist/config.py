import logging
from datetime import date
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator
from pydantic.fields import FieldInfo

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

log = logging.getLogger("shortlist")

CdcState = Literal["bear-far", "bear-approaching", "just-crossed", "bull"]
STATE_LABELS = {
    "bear-far": "bear-far (ยังห่างจุด cross)",
    "bear-approaching": "bear-approaching (ใกล้ cross)",
    "just-crossed": "just-crossed (เพิ่ง cross)",
    "bull": "bull (cross มานานแล้ว)",
}
SECTION_TITLES = {
    "liquidity": "Liquidity",
    "quality": "Quality gate",
    "fair_value": "Fair value",
    "cdc": "CDC",
    "risk_reward": "Risk / reward",
    "candidates": "Candidates",
}
FairValueMethod = Literal["pe_median", "pe_minus_1sd", "pbv_median", "dividend_yield_median", "peer_pe", "justified_pbv"]


class Strict(BaseModel):
    # unknown keys are almost always typos in a hand-edited file
    model_config = ConfigDict(extra="forbid")


def editable(title: str, description: str, unit: str, **limits) -> Any:
    """A field shown on the web settings page; unit tells the page how to display it."""
    return Field(title=title, description=description, json_schema_extra={"editable": True, "unit": unit}, **limits)


class Liquidity(Strict):
    window_days: int = editable(
        "จำนวนวันที่ใช้เฉลี่ย traded value",
        "จำนวนวันทำการล่าสุดที่ใช้หามูลค่าซื้อขายเฉลี่ยต่อวัน เพิ่มค่าจะได้ค่าเฉลี่ยที่นิ่งขึ้น วันที่มีข่าวแล้วซื้อขายผิดปกติมีผลน้อยลง "
        "แต่ตามไม่ทันเมื่อสภาพคล่องเปลี่ยน ลดค่าจะไวต่อช่วงสั้นๆ ที่ซื้อขายคึกคัก",
        "days", ge=1, le=250,
    )
    min_avg_traded_value: float = editable(
        "มูลค่าซื้อขายเฉลี่ยขั้นต่ำ",
        "หุ้นที่มูลค่าซื้อขายเฉลี่ยต่ำกว่านี้ถูกตัดออกก่อนดึงงบ ลดค่าจะได้หุ้นเข้ามาประเมินมากขึ้น แต่หุ้นสภาพคล่องต่ำมักใช้เวลานานกว่าจะ "
        "re-rate ทำให้เงินแช่นานขึ้น และ batch ช้าลงเพราะต้องดึงงบหลายตัวขึ้น เพิ่มค่าจะเหลือหุ้นที่มีแรงซื้อขายมาก",
        "million_baht", ge=0, le=1_000_000_000,
    )


class Quality(Strict):
    min_quarters: int = editable(
        "จำนวนไตรมาสที่มีงบขั้นต่ำ",
        "หุ้นที่มีงบน้อยกว่านี้ไม่ผ่าน gate เพราะดูความสม่ำเสมอไม่ได้ เพิ่มค่าจะตัดหุ้นที่เพิ่ง IPO ออกและเหลือหุ้นที่มีประวัติยาว "
        "ลดค่าจะได้หุ้นใหม่เพิ่ม แต่ band ย้อนหลังของหุ้นเหล่านั้นมีข้อมูลน้อย",
        "quarters", ge=4, le=40,
    )
    min_roe: float = editable(
        "ROE TTM ขั้นต่ำ",
        "กำไรสุทธิ 4 ไตรมาสล่าสุด ÷ ส่วนผู้ถือหุ้น หุ้นที่ต่ำกว่านี้ไม่ผ่าน gate เพิ่มค่าจะเหลือหุ้นที่ทำกำไรจากทุนได้ดีกว่าแต่ candidates น้อยลง "
        "ลดค่าจะได้หุ้นเพิ่ม รวมถึงหุ้นที่กำลังฟื้นแต่ ROE ยังต่ำ",
        "percent", ge=0, le=1,
    )
    max_de: float = editable(
        "D/E สูงสุด",
        "หนี้สินต่อส่วนผู้ถือหุ้นของไตรมาสล่าสุด ไม่ใช้กับหุ้นการเงิน ลดค่าจะเหลือหุ้นที่หนี้น้อยและเสี่ยงน้อยกว่า "
        "เพิ่มค่าจะรับหุ้นที่กู้มาก ซึ่งเสี่ยงเมื่อดอกเบี้ยขึ้นหรือกำไรตก",
        "times", ge=0, le=20,
    )
    ocf_window: int = editable(
        "จำนวนไตรมาสที่ดู OCF",
        "จำนวนไตรมาสล่าสุดที่ใช้นับว่า OCF (เงินสดจากการดำเนินงาน) เป็นบวกกี่ไตรมาส ไม่ใช้กับหุ้นการเงิน "
        "ใช้คู่กับจำนวนไตรมาสที่ OCF ต้องเป็นบวก",
        "quarters", ge=1, le=20,
    )
    ocf_min_positive: int = editable(
        "จำนวนไตรมาสที่ OCF ต้องเป็นบวก",
        "ในไตรมาสที่ดู OCF ต้องเป็นบวกอย่างน้อยเท่านี้ เพิ่มค่าจะเหลือหุ้นที่กำไรเป็นเงินสดจริงสม่ำเสมอ ลดค่าจะรับหุ้นที่มีกำไรแต่เงินสดไม่เข้า "
        "เช่น ลูกหนี้หรือสต็อกพอก ต้องไม่เกินจำนวนไตรมาสที่ดู OCF",
        "quarters", ge=0, le=20,
    )
    no_loss_window: int = editable(
        "จำนวนไตรมาสที่ห้ามขาดทุน",
        "หุ้นที่ขาดทุนแม้ไตรมาสเดียวในช่วงนี้ไม่ผ่าน gate เพิ่มค่าจะเหลือหุ้นที่กำไรสม่ำเสมอนานกว่า ลดค่าจะได้หุ้นที่เพิ่งพ้นช่วงขาดทุนมาด้วย",
        "quarters", ge=1, le=20,
    )
    max_failed_checks: int = editable(
        "จำนวนเกณฑ์ที่ไม่ผ่านได้สูงสุด",
        "ROE, D/E, OCF และไม่ขาดทุน ไม่ผ่านรวมกันได้ไม่เกินเท่านี้ (liquidity และจำนวนไตรมาสต้องผ่านเสมอ เกณฑ์ที่ข้ามไม่นับ) "
        "เพิ่มค่าจะได้ candidates มากขึ้นแต่รวมหุ้นที่พื้นฐานอ่อนกว่า 0 คือต้องผ่านทุกเกณฑ์",
        "checks", ge=0, le=4,
    )
    financial_sectors: list[str]

    # cross-field checks read the earlier field from info.data so the error lands on this field
    @field_validator("ocf_min_positive")
    @classmethod
    def _ocf_within_window(cls, v: int, info: ValidationInfo) -> int:
        window = info.data.get("ocf_window")
        if window is not None and v > window:
            raise ValueError(f"ต้องไม่เกินจำนวนไตรมาสที่ดู OCF ({window})")
        return v


class FairValue(Strict):
    enabled: list[FairValueMethod] = editable(
        "เกณฑ์ fair value ที่ใช้",
        "เกณฑ์ที่นำมาคำนวณ fair value และ margin of safety Peer PE และ Justified PBV เป็น gate method ที่ตัดสิน candidate และ target "
        "ปิดตัวหนึ่งได้แต่ rule จะต่างจากที่ backtest ทดสอบ และต้องเปิด gate method ไว้อย่างน้อยหนึ่งตัว ต้องเลือกอย่างน้อยหนึ่งเกณฑ์",
        "choice", min_length=1,
    )
    lookback_quarters: int = editable(
        "กรอบย้อนหลังของ band",
        "จำนวนไตรมาสย้อนหลังที่ใช้หา median ของ PE, PBV และ dividend yield เพิ่มค่าจะได้ band ที่นิ่งขึ้นแต่รวมช่วงที่ธุรกิจอาจต่างจากปัจจุบัน "
        "ลดค่าจะสะท้อน valuation ช่วงหลังมากขึ้น แต่รอบตลาดช่วงสั้นๆ บิด band ได้ง่าย",
        "quarters", ge=4, le=40,
    )
    min_history_points: int = editable(
        "จำนวนไตรมาสขั้นต่ำของ band",
        "band ที่มีข้อมูลน้อยกว่านี้แสดงเป็น N/A เพิ่มค่าจะได้ band ที่เชื่อถือได้มากขึ้นแต่เกณฑ์ที่คำนวณได้น้อยลง "
        "ลดค่าจะได้ fair value ครบขึ้นจากข้อมูลไม่กี่จุด",
        "quarters", ge=2, le=40,
    )
    min_peers: int = editable(
        "จำนวน peer ขั้นต่ำ",
        "peer PE ต้องมีหุ้นใน sector เดียวกันที่ผ่าน liquidity อย่างน้อยเท่านี้ ไม่งั้นเป็น N/A ลดค่าจะได้ peer PE ใน sector เล็กๆ "
        "แต่ median จากไม่กี่ตัวโดนหุ้นตัวเดียวดึงได้ง่าย",
        "stocks", ge=1, le=50,
    )
    max_pe: float = editable(
        "PE สูงสุดที่นำไปคิด band",
        "PE ย้อนหลังที่สูงกว่านี้มักมาจากกำไร 4 ไตรมาสที่ใกล้ศูนย์ จึงตัดทิ้งก่อนคิด PE band เพิ่มค่าจะเก็บช่วงที่ราคาแพงมากไว้ "
        "ทำให้ fair value สูงขึ้น ลดค่าจะตัดทิ้งมากขึ้น ทำให้ fair value ต่ำลง",
        "times", gt=0, le=1000,
    )
    min_dividend_yield: float = editable(
        "Dividend yield ขั้นต่ำที่นับว่าจ่ายปันผล",
        "ไตรมาสที่ yield ปันผลเงินสด 12 เดือนต่ำกว่านี้ถือว่าไม่ได้จ่ายปันผล และไม่นำไปคิด dividend yield band เช่น ช่วงที่จ่ายปันผลเป็นหุ้นพร้อมเงินสดนิดเดียว "
        "เพิ่มค่าจะตัดช่วงที่จ่ายน้อยทิ้งมากขึ้น หุ้นปันผลต่ำจะเป็น N/A ลดค่าจะนับช่วงที่จ่ายน้อยด้วย ทำให้ median ต่ำลงและ fair value สูงเกินจริง",
        "percent", ge=0, le=0.1,
    )
    structure_change_threshold: float = editable(
        "เกณฑ์ป้ายโครงสร้างทุนเปลี่ยน",
        "ถ้าส่วนผู้ถือหุ้นเปลี่ยนเกินนี้ระหว่างไตรมาสที่ติดกัน (เช่น ควบรวม เพิ่มทุนก้อนใหญ่) จะติดป้ายเตือนว่า band ย้อนหลังอาจเทียบกับปัจจุบันไม่ได้ "
        "ไม่ได้ตัดหุ้นออก ลดค่าจะติดป้ายบ่อยขึ้น เพิ่มค่าจะเตือนเฉพาะเหตุการณ์ใหญ่",
        "percent", ge=0, le=5,
    )
    cost_of_equity: float = editable(
        "Cost of equity (r) ของ Justified PBV",
        "ผลตอบแทนที่ผู้ถือหุ้นต้องการ Justified PBV = (ROE − g) ÷ (r − g) ลดค่าจะทำให้ fair value สูงขึ้นมาก "
        "(r 10% → 9% ทำให้ fair value สูงขึ้นราว 17% เมื่อ ROE 17%) เพิ่มค่าจะทำให้ fair value ต่ำลง",
        "percent", gt=0, le=0.5,
    )
    terminal_growth: float = editable(
        "Growth ระยะยาว (g) ของ Justified PBV",
        "อัตราเติบโตระยะยาวของกำไร ต้องน้อยกว่า cost of equity หุ้นที่ ROE ไม่สูงกว่าค่านี้เป็น N/A "
        "เพิ่มค่าจะทำให้ fair value ของหุ้น ROE สูงกว่า r สูงขึ้น และของหุ้น ROE ต่ำกว่า r ต่ำลง",
        "percent", ge=0, le=0.2,
    )

    @field_validator("terminal_growth")
    @classmethod
    def _growth_below_cost_of_equity(cls, v: float, info: ValidationInfo) -> float:
        r = info.data.get("cost_of_equity")
        if r is not None and v >= r:
            raise ValueError(f"g ต้องน้อยกว่า cost of equity ({r:.1%})")
        return v


class Cdc(Strict):
    # the formula must match the TradingView indicator, so it is edited in config.yaml only
    source: Literal["close", "ohlc4"]
    ap_length: int
    fast_length: int
    slow_length: int
    speed_window: int = editable(
        "จำนวนวันที่ใช้วัดความเร็ว gap",
        "ความเร็วที่ gap ระหว่าง Fast กับ Slow EMA แคบลงคิดจากจำนวนวันทำการนี้ แล้วใช้หา ETA ถึงจุด cross ลดค่าจะไวต่อราคาช่วงล่าสุดแต่ ETA แกว่ง "
        "เพิ่มค่าจะได้ ETA นิ่งขึ้นแต่ตามไม่ทันเมื่อราคาเร่ง",
        "days", ge=1, le=20,
    )
    approaching_eta_days: float = editable(
        "ETA ของ bear-approaching",
        "หุ้นที่ Fast EMA ยังอยู่ใต้ Slow EMA และคาดว่าจะ cross ภายในจำนวนวันทำการนี้นับเป็น bear-approaching เพิ่มค่าจะได้ candidates มากขึ้น "
        "แต่รอ cross นานขึ้น ทำให้เงินแช่นาน ลดค่าจะเหลือหุ้นที่ใกล้ cross จริง",
        "days", ge=1, le=120,
    )
    just_crossed_days: int = editable(
        "จำนวนวันของ just-crossed",
        "หุ้นที่ Fast EMA ข้ามขึ้นเหนือ Slow EMA ภายในจำนวนวันทำการนี้นับเป็น just-crossed เกินนั้นเป็น bull เพิ่มค่าจะรับหุ้นที่ cross มานานขึ้น "
        "ซึ่งราคาอาจวิ่งไปแล้ว ลดค่าจะเหลือหุ้นที่เพิ่ง cross",
        "days", ge=1, le=60,
    )
    min_days: int = editable(
        "จำนวนวันราคาขั้นต่ำของ CDC",
        "หุ้นที่มีราคาน้อยกว่านี้ไม่คำนวณ CDC เพราะ EMA ยังไม่นิ่งและอาจไม่ตรงกับ TradingView ลดค่าจะได้หุ้นที่เพิ่งเข้าตลาดเพิ่ม "
        "แต่ค่า CDC คลาดเคลื่อนมากขึ้น",
        "days", ge=30, le=240,
    )


class RiskReward(Strict):
    swing_low_days: int = editable(
        "จำนวนวันของ swing low",
        "stop คือค่าที่ต่ำกว่าระหว่างราคาต่ำสุดในจำนวนวันทำการนี้ กับ Slow EMA หัก buffer เพิ่มค่าจะได้ stop ลึกขึ้น RRR ต่ำลงแต่โดน stop ยากขึ้น "
        "ลดค่าจะได้ stop แคบ RRR สูงแต่โดน stop ง่าย",
        "days", ge=1, le=250,
    )
    stop_buffer: float = editable(
        "Stop buffer ใต้ Slow EMA",
        "stop อีกตัวเลือกคือ Slow EMA ลบด้วยสัดส่วนนี้ ระบบใช้ตัวที่ต่ำกว่าระหว่างนี้กับ swing low เพิ่มค่าจะได้ stop ลึกขึ้นและ RRR ต่ำลง "
        "ลดค่าจะได้ stop ชิดเส้น ซึ่งโดนราคาสะบัดออกง่าย",
        "percent", ge=0, le=0.5,
    )
    min_rrr: float = editable(
        "RRR ขั้นต่ำ",
        "หุ้นที่ (target − entry) ÷ (entry − stop) ต่ำกว่านี้ติดป้าย RRR ต่ำ แต่ยังอยู่ใน list เพิ่มค่าจะเตือนบ่อยขึ้น "
        "เหลือแต่หุ้นที่คุ้มความเสี่ยงชัดเจน ลดค่าจะเตือนน้อยลง",
        "times", ge=0, le=20,
    )
    max_upside: float = editable(
        "Upside สูงสุดก่อนติดป้ายเตือน",
        "หุ้นที่ (target − entry) ÷ entry สูงกว่านี้ติดป้าย upside สูงผิดปกติ เพราะ target อาจถูก band ในอดีตดึงสูงเกินจริง แต่ยังอยู่ใน list "
        "ลดค่าจะเตือนบ่อยขึ้น เพิ่มค่าจะเตือนเฉพาะ target ที่ห่างราคาหลายเท่า",
        "percent", gt=0, le=10,
    )


class Candidates(Strict):
    # not editable: changing which methods gate needs a backtest behind it (design D3)
    gate_methods: list[FairValueMethod] = Field(min_length=1)
    min_gate_mos: float = editable(
        "MoS ขั้นต่ำของ gate method",
        "ทุก gate method (Peer PE, Justified PBV) ที่คำนวณได้ต้องมี margin of safety อย่างน้อยเท่านี้จึงเข้า candidate list ค่านี้ไม่ใช่ median ของ panel "
        "เพิ่มค่าจะเหลือหุ้นที่ถูกชัดเจนแต่จำนวนน้อยลง ลดค่าจะได้หุ้นเพิ่ม รวมถึงหุ้นที่ราคาใกล้ fair value ซึ่ง upside น้อย",
        "percent", ge=-1, le=1,
    )
    accepted_states: list[CdcState] = editable(
        "CDC state ที่รับเข้า list",
        "หุ้นต้องอยู่ใน CDC state ที่เลือกจึงเข้า candidate list จาก backtest หุ้นที่เป็น bear-approaching cross จริงภายใน 20 วันบ่อยกว่า bear-far "
        "เกือบสองเท่า เพิ่ม state จะได้ candidates มากขึ้นแต่อาจรอนานขึ้น ต้องเลือกอย่างน้อยหนึ่ง state",
        "choice", min_length=1,
    )


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
    # a run stops as failed when the network is down or it runs too long (design D3 of batch-timeouts)
    max_consecutive_network_errors: int = Field(gt=0)
    max_run_minutes: float = Field(gt=0)


class Config(Strict):
    liquidity: Liquidity
    quality: Quality
    fair_value: FairValue
    cdc: Cdc
    risk_reward: RiskReward
    candidates: Candidates
    catalyst: Catalyst
    batch: Batch

    @model_validator(mode="after")
    def _a_gate_method_stays_enabled(self) -> "Config":
        # model-level, so the API maps this error to fair_value.enabled (design D4)
        if not set(self.fair_value.enabled) & set(self.candidates.gate_methods):
            raise ValueError("ต้องเปิดอย่างน้อยหนึ่งเกณฑ์ที่ใช้เป็น gate (Peer PE หรือ Justified PBV)")
        return self


def editable_fields() -> list[tuple[str, str, FieldInfo]]:
    """(section, name, field) of every field the settings page may change, in declaration order."""
    return [
        (section, name, field)
        for section, sf in Config.model_fields.items()
        for name, field in sf.annotation.model_fields.items()  # type: ignore[union-attr]
        if isinstance(field.json_schema_extra, dict) and field.json_schema_extra.get("editable")
    ]


def load_config(path: Path = DEFAULT_PATH, overrides: dict[str, Any] | None = None) -> Config:
    """YAML defaults with web-edited values (keys like "quality.min_roe") on top, validated as one config."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    allowed = {f"{section}.{name}" for section, name, _ in editable_fields()}
    for key, value in (overrides or {}).items():
        # a field renamed or no longer editable must not break the batch through extra="forbid"
        if key not in allowed:
            log.warning("ข้ามค่าที่แก้บนเว็บ %s เพราะไม่มีช่องนี้หรือแก้บนเว็บไม่ได้แล้ว", key)
            continue
        section, name = key.split(".")
        raw[section][name] = value
    return Config.model_validate(raw)
