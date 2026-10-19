# Tasks

change นี้ไม่เปลี่ยนการประเมินหุ้นใน batch จึงไม่ต้องรัน batch หรือ spot-check กับ SET/TradingView ใช้ cache ของ backtest ที่มีอยู่ (ห้ามใช้ `--refresh` จนกว่าจะผ่าน 2.3 เพราะ regression ต้องใช้ cache เดิม)

## 1. CDC แยกจาก quality และ fair value

- [x] 1.1 เพิ่ม test ใน `engine/tests/test_batch.py` ตาม D5: `evaluate_stock` สองครั้งต่างกันแค่ `cfg.cdc` (fast/slow lengths) จน CDC state ต่างกัน แล้ว `quality` และ `fair_value` (รวม `gate`) เท่ากันทุกค่า และอีก test ต่างกันแค่ `cfg.fair_value.cost_of_equity` แล้ว `cdc` เท่ากันทุกค่า ตรวจด้วย `uv run pytest tests/test_batch.py` ผ่าน และยืนยันว่า test จับได้จริงโดยลองส่ง CDC state เข้า `fair_value.evaluate` ชั่วคราวให้ test fail แล้วเอาออก

## 2. Backtest: variant

- [x] 2.1 ใน `shortlist/backtest.py` เพิ่มรายการ variant คงที่ตาม D1/D2 (MoS 15/20/25%, Option A, Option B, quality ทุกเกณฑ์ผ่าน, quality ทุกเกณฑ์ผ่าน + D/E ≤ 2.0) ให้ `evaluate_date` ติด flag ต่อ variant และ `groups` สร้างกลุ่มจาก flag เหล่านั้น ตรวจด้วย `uv run pytest tests/test_backtest.py` ที่มี test ครบทุก scenario ของ requirement "variant ของ candidate rule" (Option A ติดลบ −5%, Option A ตัวเดียว 11%, Option B ตัวเดียว, Option B −20%, quality OCF ข้อเดียว, D/E 1.8)
- [x] 2.2 เพิ่มตาราง variant แยกสองช่วงตาม D3/D4 ใน `report` (excess, CI, t, จำนวนวันที่, candidate เฉลี่ยต่อวันที่, วันที่ที่ไม่มี candidate, ผลต่างจับคู่กับ candidate พร้อม CI, คอลัมน์ผ่านเกณฑ์) และเพิ่มข้อจำกัด "ความคงที่ข้ามช่วงไม่ใช่ out-of-sample" กับ "เปรียบเทียบหลาย variant" ใน `LIMITATIONS` ตรวจด้วย test ใน `tests/test_backtest.py` ที่ครอบ scenario ของ "ตาราง variant แยกสองช่วงเวลา", "ผลต่างจับคู่ของ variant" และ "เกณฑ์ตัดสิน variant ที่ตั้งไว้ล่วงหน้า" (ชนะช่วงเดียว, CI คร่อม 0, candidate น้อยเกินไป, ผ่าน, วันที่ไม่มี candidate)
- [x] 2.3 รัน backtest ด้วย cache เดิม (`uv run --project engine python .agents/skills/fair-value-backtest/backtest.py`) ตรวจว่าทุกแถวของกลุ่มเดิมในทุกตารางเท่ากับไฟล์ `docs/backtests/fair-value-2026-10-15.md` ใน git HEAD (diff เฉพาะส่วนที่เพิ่ม, commit/วันที่รัน) และ poison check ผ่าน ถ้าแถวเดิมเปลี่ยน หยุดและหาสาเหตุก่อน
- [x] 2.4 แก้ `.agents/skills/fair-value-backtest/SKILL.md` เพิ่มแถว variant และวิธีอ่านตาราง variant (เกณฑ์ D4, ผลต่างจับคู่, ไม่ใช่ out-of-sample, ผลไม่ใช่เหตุให้เปลี่ยน default เอง) ตรวจด้วยการอ่านเทียบกับคอลัมน์จริงในไฟล์ผลจาก 2.3

## 3. รายงานผล

- [x] 3.1 สรุปผล variant ใน `engine/README.md` (ตัวไหนผ่านเกณฑ์ D4, จำนวน candidate เทียบ rule ปัจจุบัน, ข้อจำกัด) และรายงานผู้ใช้พร้อมคำแนะนำว่าควรเปิด change เปลี่ยน default หรือไม่ ตรวจด้วยตัวเลขใน README ตรงกับไฟล์ผลจาก 2.3 และ `engine/config.yaml` ไม่เปลี่ยน (`git diff --quiet engine/config.yaml`)

## Workflow follow-up

- archive change นี้หลังผู้ใช้อ่านผล 3.1
- ถ้ามี variant ผ่านเกณฑ์และผู้ใช้ต้องการใช้ เปิด change แยกเพื่อเปลี่ยน default
- forward out-of-sample จาก `candidate_history` ราว ม.ค. 2027 (change แยก)
