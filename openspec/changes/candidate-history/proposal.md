# Proposal

## Why

DB เก็บ evaluations ของ run ล่าสุดเท่านั้น (`db.save_run` ลบของ run ก่อนหน้า) พอ batch รันวันใหม่ candidate list ของเมื่อวานจึงหายไป ดูย้อนไม่ได้ว่าหุ้นตัวไหนเข้า list วันไหน ETA, MoS หรือ RRR ตอนนั้นเป็นเท่าไร ซึ่งเป็นข้อมูลที่ต้องใช้ตอนทบทวนว่าเข้าซื้อตามสัญญาณแล้วได้ผลอย่างไร

## What Changes

- ทุก run ที่สำเร็จเก็บ candidate ของ run นั้น (เฉพาะหุ้นที่มี `candidate_rank`) ลงตารางประวัติแยกจาก evaluations หนึ่งชุดต่อวันที่ราคาปิด (`price_date`) run ที่สำเร็จทีหลังของวันที่ราคาเดียวกันแทนชุดเดิม run ที่ failed ไม่เขียน
- เก็บถาวร ไม่ลบอัตโนมัติ
- หน้าใหม่ "ประวัติ candidate" เลือกวันที่แล้วเห็นตาราง candidate ของวันนั้นด้วยคอลัมน์เดียวกับหน้า candidates ชื่อหุ้นเป็นข้อความธรรมดา ไม่ลิงก์ไปหน้ารายละเอียด (หน้ารายละเอียดแสดงข้อมูลวันนี้ ไม่ใช่ของวันนั้น)
- หน้า candidates มีลิงก์ไปหน้าประวัติ
- ตอนสร้างตาราง ใส่ candidate ของ run ล่าสุดที่สำเร็จไว้เป็นวันแรก

นอกขอบเขต:
- ข้อมูลหน้ารายละเอียดของวันนั้น (กราฟราคา, งบ, fair value panel แบบเต็ม, CDC รายวัน)
- เกณฑ์ (settings) ที่ใช้ตอนนั้น ประวัติจึงบอกไม่ได้ว่า list ต่างกันเพราะตลาดหรือเพราะเปลี่ยนเกณฑ์
- หุ้นที่ไม่ใช่ candidate และผลตอบแทนหลังวันนั้น (ทำใน `thesis-tracking` หรือ backtest)
- เติมประวัติย้อนหลังจาก snapshot ใน `engine/.cache/joint-batch/`

## Capabilities

### New Capabilities
- `candidate-history`: เก็บ candidate ต่อวันที่ราคาปิดและหน้าดูย้อนหลัง

### Modified Capabilities
- (ไม่มี)

## Impact

- **Code:** `engine/shortlist/db.py` (ตาราง `candidate_history`, เขียนใน transaction ของ `save_run`, query), `engine/shortlist/api.py` (2 endpoint), `web/app/page.tsx` (แยกตาราง candidate เป็น component ใช้ร่วม และลิงก์), หน้าใหม่ `web/app/history/page.tsx`, `web/lib/engine.ts` และ test
- **ผลต่อผู้ใช้:** มีหน้าประวัติเพิ่ม ไม่เปลี่ยนวิธีประเมินหุ้นหรือ candidate list ขนาด DB โตราว 20–35 MB ต่อปี
- **ความสัมพันธ์กับ change อื่น:** ถูกบล็อกโดย joint batch ของ 15 ต.ค. (runs C/A/B/D ต้องใช้ code ของวันนี้) apply หลังจากนั้น `gate-on-proven-methods` จะเปลี่ยนรูป evaluation (เพิ่ม `fair_value.gate` และคอลัมน์ MoS gate) แถวประวัติเก่าจึงต้องแสดงได้แม้ไม่มี field ใหม่ ไม่บล็อก change อื่น
