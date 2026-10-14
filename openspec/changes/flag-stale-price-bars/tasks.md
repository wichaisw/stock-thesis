# Tasks

## 1. Engine

- [ ] 1.1 ติด `stale_price` ให้ทุก evaluation ใน `shortlist/batch.py` หลังคำนวณ `price_date` ของ run (D1, D2) และต่อท้าย log candidates ด้วยจำนวนหุ้นที่ราคาไม่อัปเดต (D5) พร้อม test ใน `tests/test_batch.py` ตาม 3 scenario ของ requirement "ตรวจหุ้นที่ราคาไม่อัปเดต" ตรวจด้วย `uv run pytest tests/test_batch.py`
- [ ] 1.2 ให้ `db.latest_successful_run` คืน `stale_count` และ `stale_date` (D3) รวมกรณี run เก่าที่ไม่มี `stale_price` ได้ 0 พร้อม test ใน `tests/test_db.py` ตรวจด้วย `uv run pytest` ทั้งชุดผ่าน

## 2. Web

- [ ] 2.1 เพิ่ม field แบบ optional ใน `web/lib/engine.ts` (D4) แล้วแสดงบรรทัดเตือน "ราคา N/M ตัวเป็นวันที่ …" ใต้วันที่ราคาและ Tag "ราคาไม่อัปเดต" ในคอลัมน์ป้ายของ `app/page.tsx` และข้างวันที่ราคาใน `app/stocks/[symbol]/page.tsx` ตรวจด้วย `bun run lint` และเปิด browser ดูว่า run ที่ไม่มี field ไม่พังและไม่มีบรรทัดเตือน
- [ ] 2.2 ใน `lib/llm-export.ts` ต่อท้ายบรรทัด Last close ด้วยข้อความว่าราคาเก่ากว่าหุ้นตัวอื่นใน run เมื่อ `stale_price` พร้อม test ใน `llm-export.test.ts` ตรวจด้วย `bun test lib/llm-export.test.ts` และ `bun run lint`

## 3. Integration

- [ ] 3.1 รัน batch ใหม่ ตรวจว่าจำนวนหุ้นที่ราคาไม่อัปเดตใน log, บรรทัดเตือนบนหน้า candidate list และจำนวนจาก DB ตรงกัน และ spot-check หุ้นที่ติดป้าย 2 ตัวกับหุ้นที่ไม่ติด 1 ตัว ว่าวันที่และราคาปิดล่าสุดตรงกับ TradingView/SET (หุ้นที่ติดป้ายต้องมีแท่งที่ engine ไม่มี)

## Workflow follow-up

- archive หลัง `simplify-risk-reward` เพราะ delta ของ "ข้อมูลที่แสดงใน candidate list" เขียนต่อจากเวอร์ชันของ change นั้น
