# Proposal

## Why

fair value panel ตอนนี้มี 5 เกณฑ์ แต่ทุกเกณฑ์เป็น multiple ที่อิงอดีตหรือ peer และ 3 ใน 5 ใช้กำไร TTM ตัวเดียวกัน (PE median, PE − 1SD, peer PE) ผลคือ "4/5 undervalued" มีมุมมองที่เป็นอิสระต่อกันจริงแค่ 2–3 มุม และไม่มีเกณฑ์ไหนเห็นหนี้สุทธิ หรือให้ค่าที่ไม่ขึ้นกับราคาในอดีตเลย

ไม่เลือก DCF หรือ financial projection เพราะไม่มี consensus forecast ให้ใช้ ตัวเลขสมมติ (growth, WACC) เปลี่ยน 1% ทำให้ fair value แกว่ง 20–40% และ thesis ถือราว 1 ไตรมาสเดิมพันกับ multiple กลับสู่ band ไม่ใช่มูลค่าที่ใช้เวลาหลายปีกว่าจะเห็น

## What Changes

- เพิ่มเกณฑ์ **EV/EBITDA band**: median EV/EBITDA 5 ปี × EBITDA TTM − หนี้สุทธิล่าสุด ÷ จำนวนหุ้นล่าสุด เห็นหนี้ที่ PE มองไม่เห็น เป็น N/A สำหรับหุ้นการเงิน
- เพิ่มเกณฑ์ **Justified PBV**: (ROE − g) ÷ (r − g) × ส่วนผู้ถือหุ้นล่าสุด ÷ จำนวนหุ้น ไม่ขึ้นกับราคาในอดีต ค่า default r = 10%, g = 3% ปรับได้ใน config
- ทั้งสองเกณฑ์เปิดใช้เป็น default จึงมีผลกับ median MoS, candidate gate และ target ของ risk/reward ตั้งแต่ batch ถัดไป
- แหล่งงบเพิ่ม field เงินสด, หนี้ และ EBITDA TTM ซึ่งต้อง cross-check กับ SET/TradingView ก่อนใช้ ถ้าไม่ตรง ส่งเฉพาะ Justified PBV
- สรุป "x/y undervalued" นับ PE median กับ PE − 1SD เป็นมุมมองเดียว (PE band) ส่วน MoS ต่ำสุด, median, สูงสุด ยังคิดจากทุกเกณฑ์เหมือนเดิม
- คำอธิบายเกณฑ์ใหม่ใน tooltip ของ panel และในข้อความที่คัดลอกให้ LLM

นอกขอบเขต:
- DCF, forward PE หรือการประมาณการกำไรใดๆ
- Graham number และ FCF yield band
- การตั้ง r หรือ g แยกรายหุ้นหรือราย sector
- การเปลี่ยน candidate gate (ยังใช้ median MoS ≥ เกณฑ์เดิม)
- tooltip ⓘ ของ panel ที่แสดงไม่ขึ้น (แก้แยกเป็น fix เล็ก ไม่อยู่ใน change นี้)

ความสัมพันธ์กับ change อื่น:
- `simplify-risk-reward` ข้อ 4.1 (spot-check ป้าย upside สูงผิดปกติของ EA, TPCH, SRICHA) ควรทำก่อนรัน batch ของ change นี้ เพราะเกณฑ์ใหม่เปลี่ยน median fair value ซึ่งเป็น target ทำให้ผลเทียบกับที่คาดไว้ไม่ได้ code ไม่บล็อกกัน
- ไม่บล็อกและไม่ถูกบล็อกโดย `investor-type-flow` และ `flag-stale-price-bars` (คนละ requirement)

## Capabilities

### New Capabilities
- (ไม่มี)

### Modified Capabilities
- `fair-value-panel`: เพิ่มเกณฑ์ EV/EBITDA band และ Justified PBV ในรายการเกณฑ์ และเปลี่ยนการนับ undervalued ในสรุปให้นับ PE band เป็นมุมมองเดียว

## Impact

- **engine**: `shortlist/core/fair_value.py` (2 เกณฑ์ใหม่, การนับใน `summarize`), `shortlist/config.py` และ `config.yaml` (method ใหม่, `cost_of_equity`, `terminal_growth`, `max_ev_ebitda`), `shortlist/sources/__init__.py` และ `thaifin_source.py` (field `cash`, `total_debt`, `ebitda_ttm`), `shortlist/batch.py` (ส่งว่าเป็นหุ้นการเงินหรือไม่), tests `test_fair_value.py`, `test_sources.py`, `test_config.py`, `fakes.py`
- **web**: `app/stocks/[symbol]/page.tsx` (`FAIR_VALUE_HELP`), `lib/llm-export.ts` (`METHOD_NOTES_EN`) และ test
- **ข้อมูล**: ตาราง `financials_quarterly` มีคอลัมน์เพิ่ม (สร้างใหม่อัตโนมัติเมื่อคอลัมน์เปลี่ยน) และผลการตรวจ field ใหม่บันทึกใน `engine/README.md`
- **ผลต่อผู้ใช้**: candidate list อาจเปลี่ยนหลัง batch แรก เพราะ median MoS คิดจาก 7 เกณฑ์แทน 5
