# Tasks

## 1. ตรวจ field ใหม่ก่อนเขียน code

- [ ] 1.1 ใช้ skill `data-crosscheck` เทียบ `cash`, `total_debt`, `ebit_dattm` ของ thaifin กับงบบน SET (และ EV/EBITDA บน TradingView) ของชุดหุ้นที่ใช้ตรวจเดิมใน `engine/README.md` อย่างน้อย 2 ไตรมาส ยืนยันว่า `total_debt` เป็นหนี้ที่มีภาระดอกเบี้ย และ `ebit_dattm` เป็น TTM หรือรายไตรมาส (D1) บันทึกผลใน `engine/README.md` ตรวจด้วยตารางผลใน README ถ้าไม่ตรง ข้ามกลุ่ม 3 และเอา EV/EBITDA ออกจาก spec delta ก่อนทำต่อ

## 2. Engine: Justified PBV

- [ ] 2.1 เพิ่ม `cost_of_equity` (default 0.10) และ `terminal_growth` (default 0.03) แบบ editable percent ใน `FairValue` พร้อม validator g < r ใน `shortlist/config.py` และ `config.yaml` และเพิ่ม `justified_pbv` ใน `FairValueMethod` และ `enabled` default (D7) ตรวจด้วย `uv run pytest tests/test_config.py` ซึ่งมี test ว่า g = r ถูกปฏิเสธ
- [ ] 2.2 เพิ่มเกณฑ์ `justified_pbv` ใน `core/fair_value.py` โดยใช้ `quality.roe_ttm` และส่วนผู้ถือหุ้นล่าสุด ÷ จำนวนหุ้นล่าสุด (D4) พร้อม test ตาม scenario ของ requirement "Justified PBV" (ROE 17% → 20.00 บาท, ROE ≤ g → N/A, หุ้นการเงินคำนวณได้) ตรวจด้วย `uv run pytest tests/test_fair_value.py`

## 3. Engine: EV/EBITDA band

- [ ] 3.1 เพิ่ม `cash`, `total_debt`, `ebitda_ttm` ใน `QUARTERLY_COLUMNS` และ `FIELD_MAP` ของ `thaifin_source.py` (D2, รวม 4 ไตรมาสเองถ้า 1.1 พบว่าเป็นรายไตรมาส) และค่าใน `tests/fakes.healthy_quarters` ตรวจด้วย `uv run pytest tests/test_sources.py tests/test_db.py`
- [ ] 3.2 เพิ่ม `max_ev_ebitda` (default 50) ใน `FairValue`/`config.yaml` และ `ev_ebitda_median` ใน `FairValueMethod` และ `enabled` default (D6) ตรวจด้วย `uv run pytest tests/test_config.py`
- [ ] 3.3 เพิ่ม parameter `is_financial` ให้ `fair_value.evaluate` และส่งจาก `batch.py` ด้วย `info.sector in cfg.quality.financial_sectors` (D3) แล้วเพิ่มเกณฑ์ `ev_ebitda_median` พร้อม test ตาม scenario ของ requirement "EV/EBITDA band" และ "EV/EBITDA band ที่คำนวณไม่ได้" (10.00 บาท, ตัดค่า 180 เท่า, Banking → N/A, หนี้สุทธิเกินมูลค่ากิจการ → N/A) ตรวจด้วย `uv run pytest`

## 4. Engine: นับมุมมองในสรุป

- [ ] 4.1 แก้ `summarize` ให้นับ PE median และ PE − 1SD เป็นมุมมองเดียวตามค่าเฉลี่ย MoS (D5) โดย min/median/max MoS คิดจากทุกรายการเหมือนเดิม แก้ `test_summary_counts_undervalued` และเพิ่ม test ตาม 3 scenario ของ requirement "สรุปของ panel" ตรวจด้วย `uv run pytest tests/test_fair_value.py`

## 5. Web

- [ ] 5.1 เพิ่มคำอธิบายของ `ev_ebitda_median` และ `justified_pbv` ใน `FAIR_VALUE_HELP` (`app/stocks/[symbol]/page.tsx`) และ `METHOD_NOTES_EN` (`lib/llm-export.ts`) โดยระบุ r, g และว่า EV/EBITDA ไม่ใช้กับหุ้นการเงิน เพิ่ม test ใน `lib/llm-export.test.ts` ว่าข้อความอธิบายเกณฑ์ใหม่ ตรวจด้วย `bun test lib/llm-export.test.ts` และ `bun run lint`
- [ ] 5.2 เปิดหน้า settings ใน browser ตรวจว่าเลือก/ปิด 2 เกณฑ์ใหม่ได้ มีช่อง cost of equity, growth และ EV/EBITDA สูงสุด และตั้ง g ≥ r แล้วบันทึกไม่ได้

## 6. Integration

- [ ] 6.1 บันทึก candidate list และ median MoS ของ run ล่าสุดไว้เทียบ แล้วรัน batch ใหม่ ตรวจว่า run สำเร็จ หุ้นการเงินมี EV/EBITDA เป็น N/A และสรุปแสดง "x/6 undervalued" เมื่อเปิดครบ 7 เกณฑ์ ตรวจด้วย skill `stock-sanity-check` (ไม่มี MoS ต่ำกว่า −100% หรือ fair value สูงผิดปกติจากเกณฑ์ใหม่)
- [ ] 6.2 spot-check อย่างน้อย 3 หุ้น (หุ้นหนี้สุทธิสูง, หุ้นเงินสดสุทธิ, หุ้นธนาคาร) คำนวณ EV/EBITDA band และ Justified PBV ด้วยมือจากงบบน SET และราคาบน TradingView ให้ตรงกับหน้ารายละเอียดภายใน 1% และอธิบายหุ้นที่เข้าหรือหลุดจาก candidate list เทียบกับ 6.1 บันทึกใน `engine/README.md`

## Workflow follow-up

- ทำ `simplify-risk-reward` ข้อ 4.1 ก่อนรัน batch ของข้อ 6.1
- ตอน archive ตรวจ Purpose ของ `openspec/specs/fair-value-panel/spec.md` ว่ายังถูก (พูดถึง "เกณฑ์ valuation" โดยรวม ไม่ต้องแก้)
