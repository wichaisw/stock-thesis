# Tasks

## 1. Engine setup

- [x] 1.1 ติดตั้ง `uv` แล้วสร้าง `engine/` ด้วย `pyproject.toml` ที่ใช้ Python 3.13 มี dependency yfinance, thaifin, pandas, fastapi, uvicorn, pyyaml, pydantic และ dev dependency pytest ตรวจว่า `uv run python -c "import yfinance, thaifin"` ผ่าน และ `uv run pytest` รันได้
- [x] 1.2 สร้าง `engine/config.yaml` ที่มีค่า default ทั้งหมดตาม proposal และ specs พร้อม loader ที่ใช้ pydantic (design D6) ตรวจด้วย test ว่าโหลด default ได้ และ config ที่ค่าผิดประเภทจะ error พร้อมบอกชื่อ field

## 2. Data sources และฐานข้อมูล

- [x] 2.1 กำหนดรูปแบบข้อมูลกลางและ `Protocol` ของแหล่งราคาและแหล่งงบ (design D2) ตรวจด้วย type check ว่า adapter ทั้งสองตัวตรงตาม Protocol
- [x] 2.2 ทำ adapter yfinance ที่ดึงเป็น chunk และตัดแถวที่ไม่มีราคาปิดทิ้ง ตรวจด้วย test จาก fixture DataFrame ที่แถวสุดท้ายมี Close เป็น NaN
- [x] 2.3 ทำ adapter thaifin (รายชื่อหุ้น, sector, งบรายไตรมาส) ที่ map ชื่อ field เป็นของเรา และหาไตรมาสล่าสุดจากแถวที่มี EPS ตรวจด้วย test จาก fixture ที่มีแถวไตรมาสล่วงหน้า
- [x] 2.4 เทียบ ROE และ PE ของ thaifin กับงบจริงของ PTT, CPALL และ KBANK เพื่อดูว่า ROE เป็นค่า annualize หรือไม่ แล้วบันทึกผลเป็นข้อความสั้นๆ ใน `engine/README.md`
- [x] 2.5 สร้าง schema SQLite (design D3) และฟังก์ชันอ่านเขียน ตรวจด้วย test ที่ใช้ DB ชั่วคราว เขียน run และ evaluation แล้วอ่านกลับได้ตรง

## 3. CDC และ Phase 0 spike

- [x] 3.1 ทำ `core/cdc` ที่คำนวณ AP/Fast/Slow, gap%, ความเร็ว, ETA และ state ตาม spec `cdc-proximity` ตรวจด้วย test ที่ครอบคลุมทุก scenario ใน spec รวมถึงกรณีราคาไม่พอ 60 วัน
- [x] 3.2 เทียบค่า Fast/Slow ที่คำนวณได้กับ CDC ActionZone บน TradingView ของหุ้น 3 ตัว แล้วบันทึกผลใน `engine/README.md` ตรวจว่าค่าตรงกันภายในความคลาดเคลื่อนจากการปัดเศษ
- [x] 3.3 ทำ script backtest ใน `engine/scripts/` (design D8) ที่รายงาน % ที่ `bear-approaching` เกิด cross จริงภายใน 20 วันทำการ ตรวจว่า script รันจบและพิมพ์ผล แล้วบันทึกผลและค่า default ของ state ที่เลือกลง `config.yaml` และ `engine/README.md`
- [x] 3.4 แก้ backtest ให้นับเฉพาะวันที่หุ้นผ่าน liquidity ณ วันนั้น และรายงาน median return 20/60 วันของ `bear-approaching` เทียบกับ `bear-far` (design D8) รันใหม่ แล้วอัปเดตผลใน `engine/README.md` และทบทวน `accepted_states` ใน `config.yaml`
- [x] 3.5 เปลี่ยนสูตร CDC ตาม spec `cdc-proximity` (ราคาตั้งต้นเป็น close และ smoothing 1 โดยเลือก ohlc4 ได้ใน config) ตรวจด้วย test ของทั้งสองแบบ แล้วรัน backtest (task 3.4) ใหม่และอัปเดตผลใน `engine/README.md`

## 4. Core evaluation

- [x] 4.1 ทำ `core/quality` (liquidity, จำนวนไตรมาสขั้นต่ำ, เกณฑ์พื้นฐาน, เกณฑ์หุ้นการเงิน, inflection flag) ตรวจด้วย test ที่ครอบคลุมทุก scenario ใน spec `quality-gate`
- [x] 4.2 ทำ `core/fair_value` (5 เกณฑ์, margin of safety, N/A พร้อมเหตุผล, สรุป panel, peer PE เป็น N/A เมื่อ peer น้อยกว่า 3 ตัว) ตรวจด้วย test ที่ครอบคลุมทุก scenario ใน spec `fair-value-panel`
- [x] 4.3 ทำ `core/catalyst` (hints ตาม sector, กำหนดส่งงบที่ประมาณ, วัน index review, รวม event manual ภายใน 6 เดือน) ตรวจด้วย test ที่ครอบคลุมทุก scenario ใน spec `catalyst-watch` รวมถึงกรณีวันที่ 14 ต.ค. 2026
- [x] 4.4 ทำ `core/risk_reward` (entry, stop, target, RRR, ป้ายเตือน, N/A, reward ต่อเดือน) ตรวจด้วย test ที่ครอบคลุมทุก scenario ใน spec `risk-reward`
- [x] 4.5 ทำ `core/candidates` (เงื่อนไขเข้า list, การเรียงลำดับ) ตรวจด้วย test ที่ครอบคลุมทุก scenario ใน spec `candidate-list` รวมถึงกรณีตั้ง config ให้รับทุก CDC state
- [x] 4.6 เพิ่ม `equity` ในรูปแบบข้อมูลงบกลางและ adapter thaifin แล้วเปลี่ยนเกณฑ์ ROE ใน `core/quality` เป็น ROE TTM ตรวจด้วย test ของ scenario ไตรมาสกำไรสูงผิดปกติและข้อมูล ROE ไม่ครบใน spec `quality-gate`
- [x] 4.7 เปลี่ยนทุก band ใน `core/fair_value` เป็น median (PE band มี median − 1SD) และตัด PE ที่เกินเกณฑ์ใน config (default 100) ตรวจด้วย test ของ scenario PE ย้อนหลังมีค่าผิดปกติใน spec `fair-value-panel`

## 5. Batch

- [x] 5.1 ทำ batch ตามลำดับใน design D4 โดยมี error handling รายหุ้นและเขียนผลใน transaction เดียว ตรวจด้วย test ที่ใช้ source ปลอมซึ่งให้หุ้นหนึ่งตัว error แล้ว batch ยังจบและบันทึก failure
- [x] 5.2 ทำการกัน batch รันซ้อนและการ mark run ที่ค้างเกิน 30 นาที (design D5) ตรวจด้วย test ที่เริ่ม run ที่สองขณะ run แรกยัง `running`
- [x] 5.3 ทำคำสั่ง CLI สำหรับรัน batch ตรวจด้วยการรันกับข้อมูลจริงทั้งตลาด แล้วบันทึกเวลาที่ใช้และจำนวนหุ้นที่ fail ลง `engine/README.md`

## 6. Engine API

- [x] 6.1 ทำ endpoint: candidate list ของ run สำเร็จล่าสุด, รายละเอียดหุ้นรายตัว, ค้นหา symbol (ระบุว่าหุ้นตัวไหน fail พร้อมเหตุผล), รายชื่อหุ้นที่ fail ของ run ล่าสุด, สั่งรัน batch และดูสถานะ run ตรวจด้วย test ผ่าน FastAPI TestClient รวมถึงกรณีที่ยังไม่เคยมี run สำเร็จ
- [x] 6.2 ทำ endpoint เพิ่มและลบ event manual ตรวจด้วย test ว่า event ยังอยู่หลังมี run ใหม่ และ event ที่เลยวันแล้วไม่ถูกส่งกลับมา
- [x] 6.3 เพิ่ม regression test ที่เปิด connection ของ DB ใน thread หนึ่งแล้วใช้ใน thread อื่นได้โดยไม่ error (design D3)

## 7. Web

- [x] 7.1 สร้าง `web/` ด้วย Next.js App Router, TypeScript, Tailwind ผ่าน `bun` และตั้งค่า `ENGINE_URL` ตรวจว่า `bun run build` ผ่าน
- [x] 7.2 ทำหน้า candidate list ที่มีคอลัมน์ครบตาม spec, วันที่ของข้อมูล, ปุ่มรัน batch พร้อมสถานะ, ข้อความเมื่อยังไม่มีข้อมูล และจำนวนหุ้นที่ fail ที่กดเปิดดูรายชื่อพร้อม icon เตือนและเหตุผลได้ ตรวจด้วยการเปิดหน้าเว็บขณะ engine รันอยู่ ทั้งก่อนและหลังมี run สำเร็จ และทั้งกรณีที่มีและไม่มีหุ้น fail
- [x] 7.3 ทำหน้ารายละเอียดหุ้น (ผลแต่ละ gate พร้อมค่าจริงและเกณฑ์, fair value panel, CDC, RRR, catalyst hints, event calendar, ฟอร์มเพิ่มและลบ event manual) และช่องค้นหา symbol ที่แสดง icon เตือนพร้อมเหตุผลเมื่อชี้ที่หุ้นที่ fail ตรวจด้วยการเปิดหุ้นที่อยู่ใน list, หุ้นที่ไม่ผ่าน gate และหุ้นที่ fail

## 8. Local operation และ integration

- [x] 8.1 เขียน `README.md` ที่ root อธิบายการติดตั้ง, การรัน engine และ web, การแก้ config และตัวอย่าง cron ที่รัน batch หลังตลาดปิดในวันทำการ ตรวจว่าทำตาม README บนเครื่องใหม่แล้วรันได้
- [ ] 8.2 ทดสอบ end-to-end: รัน batch จริงจาก UI แล้วสุ่มหุ้นใน candidate list 3 ตัวมาเทียบ CDC state กับ TradingView และ fair value กับงบจริง ตรวจว่าผลสอดคล้องกัน และบันทึกสิ่งที่ไม่ตรงเป็น issue รวมถึงตัดสินว่าหุ้นที่ควบรวมหรือปรับโครงสร้างต้องมีป้ายเตือนหรือไม่ (design Risks)
