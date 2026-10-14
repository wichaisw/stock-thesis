# Tasks

## 1. Spike: headless browser ผ่าน Incapsula ได้หรือไม่

- [x] 1.1 เพิ่ม `playwright` ใน `engine/pyproject.toml` ด้วย `uv add playwright` แล้ว `uv run playwright install chromium` และเขียน `engine/scripts/spike_investor_flow.py` ที่เปิดหน้า set.or.th แบบ headless แล้ว `fetch('/api/set/market/SET/investor-type')` จากในหน้า (design D1) ตรวจว่ารันแล้วได้ `asOfDate` และครบ 4 ประเภทตรงกับที่เห็นบนหน้า SET และบันทึกเวลาที่ใช้กับผลลง `engine/README.md` ถ้าโดน Incapsula บล็อกให้หยุด ไม่หาทางหลบ แล้วถามผู้ใช้ก่อนทำ task ถัดไป

## 2. Engine

- [x] 2.1 กำหนดรูปแบบกลาง `InvestorFlow` และ `Protocol` ของแหล่งข้อมูลใน `shortlist/sources/` และทำ adapter Playwright ที่แยกการแปลง JSON เป็น pure function (ตรวจครบ 4 ประเภท และผลรวมซื้อกับขายต่างจากยอดรวมไม่เกิน 1%) ตั้ง timeout 30 วินาที ตรวจด้วย `uv run pytest` ที่ใช้ fixture JSON จริงของวันที่ 14 ต.ค. 2026: ข้อมูลครบผ่าน, ขาดประเภทไม่ผ่านพร้อมชื่อประเภทที่ขาด, ผลรวมไม่ตรงไม่ผ่าน
- [x] 2.2 เพิ่มตาราง `investor_flow` และฟังก์ชัน upsert กับอ่านประวัติใน `shortlist/db.py` (design D2) ตรวจด้วย test บน DB ชั่วคราว: บันทึกวันเดียวกันสองครั้งเหลือแถวเดียวเป็นชุดล่าสุด, `save_run` ไม่ลบประวัติ, ข้อมูลที่ดึงก่อน 17:00 น. ของวันนั้นถูกระบุว่าระหว่างวัน และหลัง 17:00 น. ไม่ถูกระบุ
- [x] 2.3 เรียก `record_investor_flow` หลัง `save_run` ใน `batch.execute` แยก try/except และให้ `default_sources` คืน adapter ตัวที่สาม (design D3) ตรวจด้วย test ใน `tests/test_batch.py` ที่ใช้ source ปลอม: ดึงได้แล้วมีแถวในประวัติ, แหล่งข้อมูล error แล้ว run ยังสำเร็จและผลประเมินครบ, ข้อมูลไม่ผ่านการตรวจแล้วประวัติไม่เปลี่ยน และมีบรรทัดใน log ทุกกรณี จากนั้นรัน `uv run pytest` ให้ผ่านทั้งหมด
- [x] 2.4 เพิ่ม `GET /investor-flow` ใน `shortlist/api.py` (design D4) ตรวจด้วย test ใน `tests/test_api.py`: ใหม่สุดก่อน, `limit` ใช้ได้, มี `intraday` และเป็นรายการว่างเมื่อยังไม่มีข้อมูล
- [x] 2.5 เพิ่มใน `engine/README.md` และ `README.md` ที่ root ว่าต้องรัน `uv run playwright install chromium` หนึ่งครั้ง, ข้อมูลเริ่มสะสมจากวันแรกที่รัน, ข้อมูลระหว่างวันคืออะไร และแหล่งข้อมูลเป็น API ที่ SET ไม่ได้เปิดให้ใช้อย่างเป็นทางการ ตรวจว่าทำตาม README บนเครื่องนี้แล้ว batch เก็บข้อมูลได้
- [x] 2.6 ทำ adapter siamchart, ตาราง `investor_flow_net`, คำสั่ง `shortlist-backfill-flow` และ `GET /investor-flow/history` (design D5) ตรวจด้วย `uv run pytest`: แปลงและตัดเหลือ 1 ปี, ผลรวมไม่เป็นศูนย์แล้วไม่เก็บพร้อมวันที่, รันซ้ำไม่มีวันซ้ำ, history ไม่คืนวันที่มีใน `investor_flow` จากนั้นรันคำสั่งจริงแล้วบันทึกผลเทียบ SET ลง `engine/README.md`

## 3. หน้าเว็บ

- [x] 3.1 เพิ่ม type ใน `web/lib/engine.ts` และหน้า `web/app/investor-flow/page.tsx` ที่แสดงตารางรายวันใหม่สุดก่อน ซื้อ/ขาย/สุทธิเป็นล้านบาท ชื่อประเภทภาษาไทย สีของค่าสุทธิ ป้าย "ระหว่างวัน" และข้อความเมื่อยังไม่มีข้อมูล แล้วเพิ่มลิงก์บนหน้า candidates ข้างปุ่ม "ปรับเกณฑ์" ตรวจด้วย `bun run lint`, `bunx tsc --noEmit` และในเบราว์เซอร์ทั้งตอนยังไม่มีข้อมูลและหลังรัน batch โดยเทียบตัวเลขของต่างชาติกับหน้า SET ของวันเดียวกัน และที่ความกว้าง 375px ตารางเลื่อนในกรอบของตัวเองได้โดยหน้าไม่ล้น
- [x] 3.2 เพิ่ม `POST /investor-flow` ใน `shortlist/api.py` และปุ่ม "ดึงข้อมูลตอนนี้" บนหน้า `investor-flow` (design D4) ตรวจด้วย test ใน `tests/test_api.py`: สำเร็จแล้วมีแถว, source error ได้ 502 พร้อมเหตุผลและประวัติไม่เปลี่ยน และในเบราว์เซอร์ว่ากดแล้วตารางอัปเดตและแสดงเหตุผลเมื่อล้ม
- [x] 3.3 เพิ่มตารางค่าสุทธิย้อนหลังใต้ตารางหลักบนหน้า `investor-flow` (design D5) ตรวจด้วย `bun run lint`, `bunx tsc --noEmit` และในเบราว์เซอร์ว่าเห็นวันที่ 12 ต.ค. 2026 ต่างชาติ +266.90 และตารางไม่ล้นที่ 375px

## 4. ตรวจกับการใช้งานจริง

- [ ] 4.1 ให้ cron รัน batch หลังตลาดปิดจริงอย่างน้อย 2 วันทำการ ตรวจว่าประวัติมี 2 วันโดยไม่มีวันซ้ำ ตัวเลขของทั้ง 4 ประเภทตรงกับหน้า SET ของแต่ละวัน และไม่มีวันไหนถูกระบุว่าระหว่างวัน แล้วบันทึกผลใน `engine/README.md`

## Workflow follow-up

- Archive change นี้หลังทุก task เสร็จ
