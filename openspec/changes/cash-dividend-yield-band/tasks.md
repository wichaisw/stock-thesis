# Tasks

## 1. Dividend yield 12 เดือนใน adapter yfinance

- [ ] 1.1 เพิ่มคอลัมน์ `dividend_yield_ttm` และ `dps_ttm` ในผลของ `fetch_market_caps` จาก `Dividends` ÷ `Close` ที่ปรับ split แล้วทั้งคู่ (design D1) โดยใช้ request ประวัติราคาเดิม ตรวจด้วย `uv run pytest` ที่มี test ของ scenario ใน spec `market-data`: จ่ายปีละสองครั้ง, ไตรมาสที่ไม่มี XD, ปันผลเป็นหุ้น, แตกพาร์หลัง XD และไม่มีปันผลเงินสด
- [ ] 1.2 เทียบ dividend yield 12 เดือนที่คำนวณได้กับ `trading-stat` ของ SET ณ สิ้นปี 2022–2025 ของ PTT, AOT, DITTO, DOHOME, KLINIQ และหุ้นที่แตกพาร์ในกรอบ 5 ปีอย่างน้อย 1 ตัว (เช่น SCAP) ผ่านเมื่อต่างไม่เกิน 0.2 จุด % แล้วบันทึกตารางผลและจุดที่ไม่ตรงใน `engine/README.md`

## 2. Dividend yield band

- [ ] 2.1 เพิ่ม config `fair_value.min_dividend_yield` (default 0.005) ใน `engine/config.yaml` และ `config.py` (design D2) ตรวจด้วย test ว่าโหลด default ได้และค่าผิดประเภท error พร้อมชื่อ field
- [ ] 2.2 เปลี่ยน dividend yield band ใน `core/fair_value` ให้ใช้ `dividend_yield_ttm` และ `dps_ttm` แทน `dividend_yield` และ `close` ของ thaifin (design D3) ตรวจด้วย `uv run pytest` ที่มี test ของ scenario ใน spec `fair-value-panel`: จ่ายสม่ำเสมอ, ช่วงที่จ่ายปันผลเป็นหุ้น, จ่ายปันผลเป็นหุ้นทุกปี และหยุดจ่ายปันผล และแก้ test เดิมของ yield band ให้ใช้ข้อมูลชุดใหม่
- [ ] 2.3 แก้ tooltip ของ dividend yield band ใน `web/app/stocks/[symbol]/page.tsx` ให้บอกว่าใช้ปันผลเงินสด 12 เดือนและไม่นับปันผลเป็นหุ้น ตรวจด้วย `bun run lint` และชี้ที่เกณฑ์นี้ในหน้ารายละเอียดหุ้น

## 3. ตรวจกับข้อมูลจริง

- [ ] 3.1 รัน batch ใหม่แล้วเทียบ candidate list กับ run 11 (ก่อนเปลี่ยน) บันทึกหุ้นที่เข้าหรือออกจาก list และ fair value ของ dividend yield band ของ PTT, DITTO, DOHOME, KLINIQ ก่อนและหลังใน `engine/README.md` ตรวจว่า DITTO ไม่สูงเกินจริงอีก (fair value ของเกณฑ์นี้ไม่เกิน 2 เท่าของราคา) และ DOHOME เป็น N/A พร้อมเหตุผล
- [ ] 3.2 รัน skill `stock-sanity-check` กับ run ใหม่ ตรวจว่าไม่มี dividend yield band ที่ fair value สูงกว่าราคาเกิน 3 เท่า ถ้ามีให้ตรวจที่มาของหุ้นนั้นกับ SET แล้วบันทึกผลใน `engine/README.md` และตรวจว่าเกณฑ์ 0.5% ไม่ตัดหุ้นที่จ่ายปันผลเงินสดจริงทิ้ง

## Workflow follow-up

- Archive `value-stock-shortlist` ก่อนเริ่ม apply change นี้ เพื่อให้ spec `market-data` และ `fair-value-panel` อยู่ใน `openspec/specs/`
- Archive change นี้หลังทุก task เสร็จ
