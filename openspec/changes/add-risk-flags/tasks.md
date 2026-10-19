# Tasks

batch ที่ต้องรันใน task 4.1 ให้รันนอกช่วง 17:00–18:30 (Yahoo จำกัด rate หลังตลาดปิด) และ backtest ใน 2.2 ใช้ cache เดิม ไม่ใช้ `--refresh`

## 1. Engine: ป้ายทั้งสาม

- [ ] 1.1 เพิ่ม section `flags` (`profit_jump_ratio` 1.5, `source_mismatch` 0.15, `earnings_due_days` 14) ใน `shortlist/config.py` แบบไม่ editable พร้อมคำอธิบายภาษาไทย และใน `config.yaml` (D1) ตรวจด้วย `uv run pytest tests/test_config.py` ที่มี test ว่าค่า default โหลดได้, ratio ≤ 1 หรือ threshold ≤ 0 ถูกปฏิเสธ และ `flags.*` ไม่อยู่ใน `editable_fields()`
- [ ] 1.2 เพิ่ม `profit_jump` ใน `quality.evaluate` ตาม D2 คู่กับ `inflection` ตรวจด้วย `uv run pytest tests/test_quality.py` ที่ครอบทุก scenario ของ "ป้ายกำไรกระโดด" (1.6 เท่าติด, 1.2 เท่าไม่ติด, ปีก่อนขาดทุน, ไม่ครบ 8 ไตรมาส, ไตรมาสล่าสุดที่งบไม่ครบไม่ถูกนับ) และ `passed` ไม่เปลี่ยนเมื่อติดป้าย
- [ ] 1.3 `PreferredStatements` รับ threshold และเก็บ `mismatch` ตาม D3 ตรวจด้วย `uv run pytest tests/test_sources.py` ที่ครอบทุก scenario ของ "ป้ายแหล่งข้อมูลไม่ตรงกัน" (−20% ติด, 5% ไม่ติด, เทียบไตรมาสล่าสุดที่ทั้งสองมี, ดึงไม่ได้/สกุลอื่น/thaifin = 0 ไม่ติด) และค่าที่ overlay ได้เหมือนเดิม
- [ ] 1.4 แยกกฎกำหนดส่งงบของไตรมาสหนึ่งออกจาก `statement_deadlines` เป็นฟังก์ชันที่ใช้ร่วมกัน แล้วเพิ่มฟังก์ชันงบใกล้ออกตาม D4 ใน `core/catalyst.py` ตรวจด้วย `uv run pytest tests/test_catalyst.py` ที่ครอบทุก scenario ของ "ป้ายงบใกล้ออก" (5 พ.ย. ติด, ส่งก่อนกำหนดไม่ติด, 15 ต.ค. ไม่ติด, 20 พ.ย. ไม่ติด) และ test เดิมของ event calendar ผ่านโดยไม่แก้
- [ ] 1.5 `batch.evaluate_stock` ใส่ `ev["source_mismatch"]` และ `ev["earnings_due"]` (หุ้นที่ไม่มีงบไม่มีสอง key นี้) และสร้าง `PreferredStatements` ด้วย threshold จาก config ตรวจด้วย `uv run pytest` ทั้งชุด รวม test ใน `tests/test_batch.py` ว่าหุ้นที่ติดทั้งสามป้ายได้ `inclusion` และ `sort_key` เท่ากับตอนไม่ติด แล้วเพิ่มคำอธิบายป้ายทั้งสามใน `engine/README.md` ส่วนค่าเกณฑ์ ตรวจด้วย `rg -n "flags\." engine/README.md`

## 2. Backtest

- [ ] 2.1 เพิ่ม `profit_jump` ในแถวของ `evaluate_date` และตาราง "ป้ายกำไรกระโดด" ใน `metrics`/`report` ตาม D5 พร้อมข้อจำกัดว่าใช้กำไรของ thaifin อย่างเดียว ตรวจด้วย `uv run pytest tests/test_backtest.py` ที่ครอบทุก scenario ของ "วัดป้ายกำไรกระโดด" (มีข้อมูล, ไม่มีข้อมูล, วันที่ไม่มีหุ้นติดป้าย) และ test เดิมทุกตัวผ่าน
- [ ] 2.2 รัน backtest ด้วย cache เดิม ตรวจว่าทุกแถวของกลุ่มเดิมเท่ากับ `docs/backtests/fair-value-2026-10-19.md` ใน git HEAD และ poison check ผ่าน แล้วเพิ่มวิธีอ่านตารางใน skill `fair-value-backtest` และสรุปผลใน `engine/README.md` ตรวจด้วยตัวเลขใน README ตรงกับไฟล์ผล และ `git diff --quiet engine/config.yaml` ยกเว้น section `flags`

## 3. Web

- [ ] 3.1 เพิ่ม type optional ของ `quality.profit_jump`, `source_mismatch`, `earnings_due` ใน `web/lib/engine.ts` และป้ายใน `app/candidate-table.tsx` ตาม D6 (title = เหตุผล) ตรวจด้วย `bun run lint` และเปิด candidate list ใน browser ว่าป้ายแสดงพร้อม tooltip และหน้า `/history` ของวันที่ก่อน change นี้ไม่พัง
- [ ] 3.2 หน้ารายละเอียด `app/stocks/[symbol]/page.tsx` แสดงทั้งสามป้ายพร้อมเหตุผล (ใกล้ป้าย inflection) ตรวจด้วย `bun run lint` และเปิดใน browser หุ้นที่ติดป้ายแหล่งข้อมูลไม่ตรงกัน (เห็นไตรมาส ค่าทั้งสอง และ %) และหุ้นที่ไม่ติดป้ายใดเลย

## 4. Integration

- [ ] 4.1 รัน batch แล้วรายงานจำนวนและสัดส่วน candidate และหุ้นที่ผ่าน quality ที่ติดแต่ละป้าย ถ้าป้ายใดติดเกินครึ่งของ candidate ให้หยุดและรายงานผู้ใช้ candidate list ต้องเท่ากับ run ก่อนหน้าเมื่อราคาเท่ากัน (ป้ายไม่เปลี่ยน list) spot-check เทียบ SET อย่างน้อย 2 หุ้นที่ติดป้ายกำไรกระโดด (กำไร TTM ทั้งสองช่วง) และ 2 หุ้นที่ติดป้ายแหล่งข้อมูลไม่ตรงกัน (กำไรไตรมาสนั้นของ SET ตรงกับแหล่งไหน) บันทึกผลใน `engine/README.md`

## Workflow follow-up

- archive หลังผู้ใช้อ่านผล 2.2 และ 4.1
- ใส่ป้ายใหม่ในข้อความ copy ให้ LLM เป็น change เล็กแยก
- ดูผลป้ายแหล่งข้อมูลไม่ตรงกันและงบใกล้ออกจาก `candidate_history` เมื่อมีข้อมูลพอ
