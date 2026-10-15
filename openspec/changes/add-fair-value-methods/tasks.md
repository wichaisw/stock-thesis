# Tasks

## 1. ตรวจ field ใหม่ก่อนเขียน code

- [x] 1.1 ใช้ skill `data-crosscheck` เทียบ `cash`, `total_debt`, `ebit_dattm` ของ thaifin กับงบบน SET (และ EV/EBITDA บน TradingView) ของชุดหุ้นที่ใช้ตรวจเดิมใน `engine/README.md` อย่างน้อย 2 ไตรมาส ยืนยันว่า `total_debt` เป็นหนี้ที่มีภาระดอกเบี้ย และ `ebit_dattm` เป็น TTM หรือรายไตรมาส (D1) บันทึกผลใน `engine/README.md` ตรวจด้วยตารางผลใน README ถ้าไม่ตรง ข้ามกลุ่ม 3 และเอา EV/EBITDA ออกจาก spec delta ก่อนทำต่อ (ผล: ไม่ตรง `ebit_dattm` ว่างทุกไตรมาส และ `total_debt` คือหนี้สินรวม จึงตัด EV/EBITDA ออกจาก change)

## 2. Engine: Justified PBV

- [x] 2.1 เพิ่ม `cost_of_equity` (default 0.10) และ `terminal_growth` (default 0.03) แบบ editable percent ใน `FairValue` พร้อม validator g < r ใน `shortlist/config.py` และ `config.yaml` และเพิ่ม `justified_pbv` ใน `FairValueMethod` และ `enabled` default (D7) ตรวจด้วย `uv run pytest tests/test_config.py` ซึ่งมี test ว่า g = r ถูกปฏิเสธ
- [x] 2.2 เพิ่มเกณฑ์ `justified_pbv` ใน `core/fair_value.py` โดยใช้ `quality.roe_ttm` และส่วนผู้ถือหุ้นล่าสุด ÷ จำนวนหุ้นล่าสุด (D4) พร้อม test ตาม scenario ของ requirement "Justified PBV" (ROE 17% → 20.00 บาท, ROE ≤ g → N/A, หุ้นการเงินคำนวณได้) ตรวจด้วย `uv run pytest tests/test_fair_value.py`

## 3. Engine: นับมุมมองในสรุป

- [x] 3.1 แก้ `summarize` ให้นับ PE median และ PE − 1SD เป็นมุมมองเดียวตามค่าเฉลี่ย MoS (D5) โดย min/median/max MoS คิดจากทุกรายการเหมือนเดิม แก้ `test_summary_counts_undervalued` และเพิ่ม test ตาม 3 scenario ของ requirement "สรุปของ panel" ตรวจด้วย `uv run pytest tests/test_fair_value.py`

## 4. Web

- [x] 4.1 เพิ่มคำอธิบายของ `justified_pbv` ใน `FAIR_VALUE_HELP` (`app/stocks/[symbol]/page.tsx`) และ `METHOD_NOTES_EN` (`lib/llm-export.ts`) โดยระบุ r และ g เพิ่ม test ใน `lib/llm-export.test.ts` ว่าข้อความอธิบายเกณฑ์ใหม่ ตรวจด้วย `bun test lib/llm-export.test.ts` และ `bun run lint`
- [x] 4.2 เปิดหน้า settings ใน browser ตรวจว่าเลือก/ปิดเกณฑ์ Justified PBV ได้ มีช่อง cost of equity และ growth และตั้ง g ≥ r แล้วบันทึกไม่ได้

## 5. Integration

- [x] 5.1 บันทึก candidate list และ median MoS ของ run ล่าสุดไว้เทียบ แล้วรัน batch ใหม่ ตรวจว่า run สำเร็จ และสรุปแสดง "x/5 undervalued" เมื่อเปิดครบ 6 เกณฑ์ ตรวจด้วย skill `stock-sanity-check` (ไม่มี MoS ต่ำกว่า −100% หรือ fair value สูงผิดปกติจากเกณฑ์ใหม่)
- [x] 5.2 spot-check อย่างน้อย 3 หุ้น (รวมหุ้นธนาคาร 1 ตัว) คำนวณ Justified PBV ด้วยมือจากงบบน SET ให้ตรงกับหน้ารายละเอียดภายใน 1% และอธิบายหุ้นที่เข้าหรือหลุดจาก candidate list เทียบกับ 5.1 บันทึกใน `engine/README.md`

## Workflow follow-up

- ทำ `simplify-risk-reward` ข้อ 4.1 ก่อนรัน batch ของข้อ 5.1
- batch ของข้อ 5.1 รวมงบจาก yfinance ของ `prefer-yfinance-statements` แล้ว (ผู้ใช้เลือก 15 ต.ค. 2026) ใช้ batch นี้เป็นของข้อ 3.1 ของ change นั้นด้วยได้
- ตอน archive ตรวจ Purpose ของ `openspec/specs/fair-value-panel/spec.md` ว่ายังถูก (พูดถึง "เกณฑ์ valuation" โดยรวม ไม่ต้องแก้)
- EV/EBITDA band ต้องหาแหล่งงบที่มี EBITDA และหนี้ที่มีภาระดอกเบี้ยย้อนหลัง 5 ปีก่อน แยกเป็น change ใหม่
