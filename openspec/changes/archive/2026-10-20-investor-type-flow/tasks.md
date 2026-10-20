# Tasks

## 1. Spike: headless browser ผ่าน Incapsula ได้หรือไม่

- [x] 1.1 เพิ่ม `playwright` ใน `engine/pyproject.toml` ด้วย `uv add playwright` แล้ว `uv run playwright install chromium` และเขียน `engine/scripts/spike_investor_flow.py` ที่เปิดหน้า set.or.th แบบ headless แล้ว `fetch('/api/set/market/SET/investor-type')` จากในหน้า (design D1) ตรวจว่ารันแล้วได้ `asOfDate` และครบ 4 ประเภทตรงกับที่เห็นบนหน้า SET และบันทึกเวลาที่ใช้กับผลลง `engine/README.md` ถ้าโดน Incapsula บล็อกให้หยุด ไม่หาทางหลบ แล้วถามผู้ใช้ก่อนทำ task ถัดไป

## 2. Engine

- [x] 2.1 กำหนดรูปแบบกลาง `InvestorFlow` และ `Protocol` ของแหล่งข้อมูลใน `shortlist/sources/` และทำ adapter Playwright ที่แยกการแปลง JSON เป็น pure function (ตรวจครบ 4 ประเภท และผลรวมซื้อกับขายต่างจากยอดรวมไม่เกิน 1%) ตั้ง timeout 30 วินาที ตรวจด้วย `uv run pytest` ที่ใช้ fixture JSON จริงของวันที่ 14 ต.ค. 2026: ข้อมูลครบผ่าน, ขาดประเภทไม่ผ่านพร้อมชื่อประเภทที่ขาด, ผลรวมไม่ตรงไม่ผ่าน
- [x] 2.2 เพิ่มตาราง `investor_flow` และฟังก์ชัน upsert กับอ่านประวัติใน `shortlist/db.py` (design D2) ตรวจด้วย test บน DB ชั่วคราว: บันทึกวันเดียวกันสองครั้งเหลือแถวเดียวเป็นชุดล่าสุด, `save_run` ไม่ลบประวัติ, ข้อมูลที่ดึงก่อน 17:00 น. ของวันนั้นถูกระบุว่าระหว่างวัน และหลัง 17:00 น. ไม่ถูกระบุ
- [x] 2.3 เรียก `record_investor_flow` หลัง `save_run` ใน `batch.execute` แยก try/except และให้ `default_sources` คืน adapter ตัวที่สาม (design D3) ตรวจด้วย test ใน `tests/test_batch.py` ที่ใช้ source ปลอม: ดึงได้แล้วมีแถวในประวัติ, แหล่งข้อมูล error แล้ว run ยังสำเร็จและผลประเมินครบ, ข้อมูลไม่ผ่านการตรวจแล้วประวัติไม่เปลี่ยน และมีบรรทัดใน log ทุกกรณี จากนั้นรัน `uv run pytest` ให้ผ่านทั้งหมด
- [x] 2.4 เพิ่ม `GET /investor-flow` ใน `shortlist/api.py` (design D4) ตรวจด้วย test ใน `tests/test_api.py`: ใหม่สุดก่อน, `limit` ใช้ได้, มี `intraday` และเป็นรายการว่างเมื่อยังไม่มีข้อมูล
- [x] 2.5 เพิ่มใน `engine/README.md` และ `README.md` ที่ root ว่าต้องรัน `uv run playwright install chromium` หนึ่งครั้ง, ข้อมูลเริ่มสะสมจากวันแรกที่รัน, ข้อมูลระหว่างวันคืออะไร และแหล่งข้อมูลเป็น API ที่ SET ไม่ได้เปิดให้ใช้อย่างเป็นทางการ ตรวจว่าทำตาม README บนเครื่องนี้แล้ว batch เก็บข้อมูลได้
- [x] 2.6 ลบของ siamchart ทั้งหมด (design D5): `sources/siamchart.py`, คำสั่ง `shortlist-backfill-flow` ใน `pyproject.toml` และ `cli.py`, `GET /investor-flow/history`, ฟังก์ชันและตาราง `investor_flow_net` ใน `db.py` (เพิ่ม `DROP TABLE IF EXISTS investor_flow_net`), test ที่เกี่ยวข้อง และข้อความใน `engine/README.md`, `README.md`, `docs/data-sources.md` ตรวจด้วย `rg -i siamchart` ไม่เหลือนอก `openspec/`, `uv run pytest` ผ่านทั้งชุด และหลัง `db.connect` บน `shortlist.db` จริงไม่มีตาราง `investor_flow_net`
- [x] 2.7 ให้ adapter `fetch` `investor-type-chart?period=1Y` ในการเปิดหน้าครั้งเดียวกับข้อมูลรายวัน แปลงและตรวจด้วย pure function, ตาราง `investor_flow_monthly` ที่แทนทั้งชุดใน transaction เดียว และ `GET /investor-flow/monthly` (design D5) ตรวจด้วย `uv run pytest` ที่ใช้ fixture JSON จริงของวันที่ 15 ต.ค. 2026: 13 จุดเก็บได้, ขาดประเภทไม่เก็บ, ผลรวม 4 ประเภทเกิน ±1 ล้านบาทไม่เก็บ, กราฟไม่ผ่านแล้วข้อมูลรายวันยังเก็บ (และกลับกัน) พร้อม log ทั้งสองกรณี, เก็บซ้ำเหลือชุดเดียว, endpoint เก่าสุดก่อนและว่างเมื่อไม่มีข้อมูล

## 3. หน้าเว็บ

- [x] 3.1 เพิ่ม type ใน `web/lib/engine.ts` และหน้า `web/app/investor-flow/page.tsx` ที่แสดงตารางรายวันใหม่สุดก่อน ซื้อ/ขาย/สุทธิเป็นล้านบาท ชื่อประเภทภาษาไทย สีของค่าสุทธิ ป้าย "ระหว่างวัน" และข้อความเมื่อยังไม่มีข้อมูล แล้วเพิ่มลิงก์บนหน้า candidates ข้างปุ่ม "ปรับเกณฑ์" ตรวจด้วย `bun run lint`, `bunx tsc --noEmit` และในเบราว์เซอร์ทั้งตอนยังไม่มีข้อมูลและหลังรัน batch โดยเทียบตัวเลขของต่างชาติกับหน้า SET ของวันเดียวกัน และที่ความกว้าง 375px ตารางเลื่อนในกรอบของตัวเองได้โดยหน้าไม่ล้น
- [x] 3.2 เพิ่ม `POST /investor-flow` ใน `shortlist/api.py` และปุ่ม "ดึงข้อมูลตอนนี้" บนหน้า `investor-flow` (design D4) ตรวจด้วย test ใน `tests/test_api.py`: สำเร็จแล้วมีแถว, source error ได้ 502 พร้อมเหตุผลและประวัติไม่เปลี่ยน และในเบราว์เซอร์ว่ากดแล้วตารางอัปเดตและแสดงเหตุผลเมื่อล้ม
- [x] 3.3 เอาตารางค่าสุทธิย้อนหลังของ siamchart และ type ของมันออกจากหน้า `investor-flow` และ `web/lib/engine.ts` แล้วเพิ่มกราฟเส้น SVG มูลค่าสุทธิสะสมรายเดือน 1 ปีของ 4 ประเภทเหนือตารางรายวัน พร้อมปุ่มเปิด/ปิดแต่ละประเภท, ค่าของแต่ละจุดเมื่อ hover และ focus, คำอธิบายและวันที่ดึงใต้กราฟ และข้อความเมื่อยังไม่มีข้อมูล (design D5) ตรวจด้วย `bun run lint`, `bunx tsc --noEmit` และในเบราว์เซอร์ด้วย skill `orca-browser-check` ว่ารูปร่างเส้นและค่าจุด ต.ค. 69 ของทั้ง 4 ประเภทตรงกับกราฟบนหน้า settrade.com ของวันเดียวกัน ปุ่มซ่อนเส้นได้ และกราฟไม่ล้นที่ 375px

## 4. ตรวจกับการใช้งานจริง

- [x] 4.1 ให้ cron รัน batch หลังตลาดปิดจริงอย่างน้อย 2 วันทำการ ตรวจว่าประวัติมี 2 วันโดยไม่มีวันซ้ำ ตัวเลขของทั้ง 4 ประเภทตรงกับหน้า SET ของแต่ละวัน ไม่มีวันไหนถูกระบุว่าระหว่างวัน และกราฟรายเดือนถูกแทนเป็นชุดใหม่ (`fetched_at` เปลี่ยน, ยังมี 13 จุด) แล้วบันทึกผลใน `engine/README.md`

## Workflow follow-up

- Archive change นี้หลังทุก task เสร็จ
