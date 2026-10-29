# Tasks

change นี้ไม่เปลี่ยนการประเมินหุ้นใน batch จึงไม่ต้องรัน batch หรือ spot-check กับ SET/TradingView ใช้ cache ของ backtest ที่มีอยู่ (ห้ามใช้ `--refresh` จนกว่าจะผ่าน 1.4 เพราะ regression ต้องใช้ cache เดิม)

## 1. Backtest: ตาราง candidate นอกธนาคาร

- [x] 1.1 ใน `engine/shortlist/backtest.py` เพิ่ม `sector` ในแถวของ `evaluate_date` ตาม D5 ตรวจด้วย test ใน `engine/tests/test_backtest.py` ว่าแถวมี sector ของหุ้น และ `uv run pytest tests/test_backtest.py` ผ่านทุก test เดิม
- [x] 1.2 เพิ่มฟังก์ชันตาราง candidate ใน Banking / นอก Banking ตาม D1–D4 (สองช่วงจาก `periods` และแถวทั้งช่วง แต่ละแถวมี excess, CI, t, จำนวนวันที่, หุ้นเฉลี่ยต่อวันที่ ใช้ baseline เดิม และเกณฑ์ "edge นอกธนาคาร: มี/ไม่มี" พร้อมเหตุผล) แล้วเรียกจาก `metrics` ตรวจด้วย test ใน `tests/test_backtest.py` ที่ครอบทุก scenario ของ requirement "วัด candidate นอกธนาคาร" และ "เกณฑ์ edge นอกธนาคารที่ตั้งไว้ล่วงหน้า" (ธนาคารนับแถว Banking, Finance & Securities นับนอก Banking, baseline รวมธนาคาร, มี, CI คร่อม 0, ช่วงหนึ่งติดลบ, ช่วงไม่มี candidate)
- [x] 1.3 เพิ่มส่วน `## candidate นอกธนาคาร` ใน `report` พร้อมคำอธิบายเกณฑ์และข้อเปิดเผยว่าเกณฑ์ตั้งหลังเห็นผลรอบแรก (D4) และเพิ่มข้อจำกัดเรื่อง sector ปัจจุบันใน `LIMITATIONS` ตรวจด้วย test ที่สร้าง report จากแถวสังเคราะห์แล้วมีหัวข้อ คอลัมน์ และคำตัดสินครบ
- [x] 1.4 รัน backtest ด้วย cache เดิม (`uv run --project engine python .agents/skills/fair-value-backtest/backtest.py`) ตรวจว่าทุกแถวของตารางเดิมเท่ากับ `docs/backtests/fair-value-2026-10-19.md` (diff มีเฉพาะส่วนที่เพิ่ม, commit และวันที่รัน) poison check ผ่าน และตัวเลขนอก Banking ใกล้กับที่ได้ใน scratchpad (+1.0% ทั้งช่วง) ถ้าแถวเดิมเปลี่ยน หยุดและหาสาเหตุก่อน
- [x] 1.5 แก้ `.agents/skills/fair-value-backtest/SKILL.md` เพิ่มวิธีอ่านตาราง candidate นอกธนาคาร (เกณฑ์ D4, baseline รวมธนาคาร, ไม่ใช่ out-of-sample, ผลไม่ใช่เหตุให้เปลี่ยน rule เอง) ตรวจด้วยการอ่านเทียบกับคอลัมน์จริงในไฟล์ผลจาก 1.4

## 2. รายงานผล

- [x] 2.1 รายงานผู้ใช้: คำตัดสิน edge นอกธนาคาร ตัวเลขสองช่วงและทั้งช่วง และความหมายต่อ candidate list ตรวจด้วยตัวเลขที่รายงานตรงกับไฟล์ผลจาก 1.4 และ `engine/config.yaml` ไม่เปลี่ยน (`git diff --quiet engine/config.yaml`)

## Workflow follow-up

- archive change นี้หลังผู้ใช้อ่านผล 2.1
- ถ้าผลเป็น "ไม่มี" และผู้ใช้ต้องการปรับ rule เปิด change แยก
- forward out-of-sample จาก `candidate_history` ราว ม.ค. 2027 (change แยก)
