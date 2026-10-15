## 1. Engine

- [x] 1.1 เพิ่มตาราง `candidate_history` ใน `SCHEMA` และ seed ตาม D3 ใน `db.connect` ตรวจ: test ใน `tests/test_db.py` ว่า DB ที่มี run สำเร็จแต่ไม่มีตารางได้ candidate ของ run ล่าสุดเป็นวันแรก และเปิดซ้ำไม่ seed ซ้ำ
- [x] 1.2 `save_run` เขียนประวัติตาม D2 และเพิ่ม `history_dates`, `history` ใน db.py ตรวจ: test ครอบ scenario "run ใหม่ของวันที่ใหม่", "รันซ้ำวันที่ราคาเดียวกัน", "run ไม่สำเร็จ", "run ไม่มี candidate" และประวัติยังอยู่หลัง evaluations ของ run เก่าถูกลบ
- [x] 1.3 เพิ่ม endpoint ตาม D4 ใน api.py ตรวจ: test ใน `tests/test_api.py` ทั้งสอง endpoint และ 404 แล้ว `uv run pytest` ผ่านทั้งหมด

## 2. Web

- [x] 2.1 ย้าย `CandidateTable` เป็น `web/app/candidate-table.tsx` พร้อม `linkSymbols` และ optional chaining ตาม D5 หน้าแรกเหมือนเดิม ตรวจ: `bun run lint` ผ่าน และ browser check หน้าแรกแสดงตารางเหมือนก่อนแก้ (14 candidate, ลิงก์ชื่อหุ้นใช้ได้)
- [x] 2.2 หน้า `web/app/history/page.tsx` และลิงก์ "ประวัติ candidate" บนหน้าแรก ตรวจ: `bun run lint` ผ่าน และ browser check scenario ของ requirement หน้าประวัติ (ไม่ระบุวันที่ = วันล่าสุด, ชื่อหุ้นไม่เป็นลิงก์, `?date=` ที่ไม่มีแสดงข้อความ) รวมแถวที่ตัด field ใหม่ออกใน DB ทดลองแล้วแสดง "-"

## 3. ตรวจกับ batch จริง

- [x] 3.1 รัน batch สองรอบบน DB จริง (รอบที่สองวันที่ราคาเดียวกัน) ตรวจ: ประวัติของวันที่นั้นมีชุดของรอบหลัง จำนวนแถวตรงกับ candidate บนหน้าแรก และ ETA, MoS, RRR ของ 3 หุ้นบนหน้าประวัติตรงกับหน้าแรก
