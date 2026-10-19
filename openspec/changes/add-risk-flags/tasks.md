# Tasks

batch ที่ต้องรันใน task 4.1 ให้รันนอกช่วง 17:00–18:30 (Yahoo จำกัด rate หลังตลาดปิด) และ backtest ใน 2.2 ใช้ cache เดิม ไม่ใช้ `--refresh`

## 1. Engine: ป้ายทั้งสอง

- [x] 1.1 เพิ่ม section `flags` (`profit_jump_ratio` 1.5, `earnings_due_days` 14) ใน `shortlist/config.py` แบบไม่ editable พร้อมคำอธิบายภาษาไทย และใน `config.yaml` (D1) ตรวจด้วย `uv run pytest tests/test_config.py` ที่มี test ว่าค่า default โหลดได้, ratio ≤ 1 หรือจำนวนวัน ≤ 0 ถูกปฏิเสธ และ `flags.*` ไม่อยู่ใน `editable_fields()`
- [x] 1.2 เพิ่มฟังก์ชัน `quality.profit_jump(reported, ratio)` ตาม D2 (signature ของ `quality.evaluate` ไม่เปลี่ยน) ตรวจด้วย `uv run pytest tests/test_quality.py` ที่ครอบทุก scenario ของ "ป้ายกำไรกระโดด" (1.6 เท่าติด, 1.2 เท่าไม่ติด, ปีก่อนขาดทุน, ไม่ครบ 8 ไตรมาส, ไตรมาสล่าสุดที่งบไม่ครบไม่ถูกนับ) และผลของ `quality.evaluate` เท่าเดิมทุกค่า
- [x] 1.3 (ป้ายแหล่งข้อมูลไม่ตรงกัน ตัดออกตาม D3) เทียบกำไรสุทธิของ thaifin กับ yfinance ของ candidate จริงก่อนใช้ป้าย ผล: ต่างมากสุด 0.13% ผู้ใช้เลือกตัดป้าย บันทึกผลใน `engine/README.md` และคืน `sources/preferred.py` กับ `tests/test_sources.py` เป็นเดิม ตรวจด้วย `git diff --quiet engine/shortlist/sources/preferred.py engine/tests/test_sources.py` และ `rg source_mismatch engine web/lib web/app` ไม่เจอ
- [x] 1.4 แยกกฎกำหนดส่งงบของไตรมาสหนึ่งออกจาก `statement_deadlines` เป็นฟังก์ชันที่ใช้ร่วมกัน แล้วเพิ่มฟังก์ชันงบใกล้ออกตาม D4 ใน `core/catalyst.py` ตรวจด้วย `uv run pytest tests/test_catalyst.py` ที่ครอบทุก scenario ของ "ป้ายงบใกล้ออก" (5 พ.ย. ติด, ส่งก่อนกำหนดไม่ติด, 15 ต.ค. ไม่ติด, 20 พ.ย. ไม่ติด) และ test เดิมของ event calendar ผ่านโดยไม่แก้
- [x] 1.5 `batch.evaluate_stock` ใส่ `ev["quality"]["profit_jump"]` (เรียก `quality.profit_jump` ด้วย `cfg.flags.profit_jump_ratio`) และ `batch` ใส่ `ev["earnings_due"]` หลังจัดลำดับแล้ว เพราะต้องใช้วันที่ราคาของ run (หุ้นที่ไม่มีงบไม่มี key นี้) ตรวจด้วย `uv run pytest` ทั้งชุด รวม test ใน `tests/test_batch.py` ว่าหุ้นที่ติดทั้งสองป้ายได้ `inclusion` และ `sort_key` เท่ากับตอนไม่ติด และป้ายงบใกล้ออกอ่านวันที่ราคาของ run แล้วเพิ่มคำอธิบายป้ายใน `engine/README.md` ส่วนค่าเกณฑ์ ตรวจด้วย `rg -n "flags\." engine/README.md`

## 2. Backtest

- [x] 2.1 เพิ่ม `profit_jump` ในแถวของ `evaluate_date` โดยเรียก `quality.profit_jump` ตัวเดียวกับ batch และตาราง "ป้ายกำไรกระโดด" ใน `metrics`/`report` ตาม D5 พร้อมข้อจำกัดว่าใช้กำไรของ thaifin อย่างเดียว ตรวจด้วย `uv run pytest tests/test_backtest.py` ที่ครอบทุก scenario ของ "วัดป้ายกำไรกระโดด" (มีข้อมูล, ไม่มีข้อมูล, วันที่ไม่มีหุ้นติดป้าย) และ test เดิมทุกตัวผ่าน
- [x] 2.2 รัน backtest ด้วย cache เดิม ตรวจว่าทุกแถวของกลุ่มเดิมเท่ากับ `docs/backtests/fair-value-2026-10-19.md` ใน git HEAD และ poison check ผ่าน แล้วเพิ่มวิธีอ่านตารางใน skill `fair-value-backtest` และสรุปผลใน `engine/README.md` ระบุใน README ว่าผลวัดเฉพาะหุ้นที่ liquidity ≥ 10 ลบ./วัน และงบ ≥ 12 ไตรมาส (design Risks) ตรวจด้วยตัวเลขใน README ตรงกับไฟล์ผล และ `git diff engine/config.yaml` เพิ่มแค่ section `flags`

## 3. Web

- [x] 3.1 เพิ่ม type optional ของ `quality.profit_jump` และ `earnings_due` ใน `web/lib/engine.ts` และป้ายใน `app/candidate-table.tsx` ตาม D6 (title = เหตุผล) ตรวจด้วย `bun run lint` และเปิด candidate list ใน browser ว่าป้ายแสดงพร้อม tooltip และหน้า `/history` ของวันที่ก่อน change นี้ไม่พัง
- [x] 3.2 หน้ารายละเอียด `app/stocks/[symbol]/page.tsx` แสดงทั้งสองป้ายพร้อมเหตุผล (ใกล้ป้าย inflection) ตรวจด้วย `bun run lint` และเปิดใน browser หุ้นที่ติดป้ายกำไรกระโดด (เห็นกำไรทั้งสองช่วงและอัตราส่วน) และหุ้นที่ไม่ติดป้ายใดเลย

## 4. Integration

- [x] 4.1 ก่อนรัน batch ให้ snapshot evaluations ของ run ล่าสุดไปที่ `engine/.cache/joint-batch/` (DB เก็บแค่ run ล่าสุด) แล้วรัน batch และรายงานจำนวนและสัดส่วน candidate และหุ้นที่ผ่าน quality ที่ติดแต่ละป้าย ถ้าป้ายใดติดเกินครึ่งของ candidate ให้หยุดและรายงานผู้ใช้ candidate list ต้องเท่ากับ snapshot เมื่อ price_date เท่ากัน (ป้ายไม่เปลี่ยน list ถ้า price_date ต่างให้รันซ้ำหลังตลาดปิดวันเดียวกับ snapshot) spot-check เทียบ SET อย่างน้อย 2 หุ้นที่ติดป้ายกำไรกระโดด (กำไร TTM ทั้งสองช่วง) บันทึกผลใน `engine/README.md`

## Workflow follow-up

- archive หลังผู้ใช้อ่านผล 2.2 และ 4.1
- ใส่ป้ายใหม่ในข้อความ copy ให้ LLM เป็น change เล็กแยก
- ดูผลป้ายงบใกล้ออกจาก `candidate_history` เมื่อมีข้อมูลพอ
- เทียบกำไรสุทธิและส่วนผู้ถือหุ้นกับ SET (แหล่งที่เป็นอิสระ) เป็น change แยก
