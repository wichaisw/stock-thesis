# Design

## Context

โปรเจกต์เริ่มจากศูนย์ ยังไม่มี code (ดูเหตุผลใน proposal.md - Why) ข้อจำกัดที่กำหนดรูปแบบของ design:

- แหล่งข้อมูลเป็น Python library ที่ unofficial ทั้งคู่ (yfinance, thaifin) และ thaifin v1.1.0 ต้องใช้ Python ≥ 3.11 ส่วน Python หลักของเครื่องคือ 3.9 แต่มี Homebrew Python 3.13
- Stack ที่ตกลงไว้คือ Next.js (TypeScript) + Python backend ใช้คนเดียวบน local ก่อน ส่วน Vercel เป็นขั้นสุดท้าย
- ผล POC: thaifin ใช้ ~0.17 วินาที/ตัว, yfinance แบบ batch เร็ว, ข้อมูลมีแถวไม่สมบูรณ์ และบางหุ้น error (ดู proposal.md - Impact)

## Goals / Non-Goals

**Goals:**
- Logic การประเมินหุ้นทั้งหมดเป็น pure function ที่ test ได้โดยไม่ต้องต่อ network
- เปลี่ยนแหล่งข้อมูลได้โดยไม่แตะ logic การประเมิน
- Batch ทั้งตลาดรันจบบนเครื่อง local ในไม่กี่นาที
- ปรับเกณฑ์ทั้งหมดได้ด้วยการแก้ไฟล์ config ไฟล์เดียว

**Non-Goals:**
- Deploy ขึ้น Vercel, hosted DB, auth หรือรองรับหลายผู้ใช้
- UI สำหรับแก้ config (แก้ไฟล์ตรงๆ)
- เก็บผลประเมินย้อนหลังไว้วิเคราะห์ (เป็นงานของ post-mortem ใน Phase 3)

## Decisions

### D1. แยกเป็น 2 โฟลเดอร์: `engine/` (Python) และ `web/` (Next.js)

```
 web/ (Next.js, TS)  --HTTP-->  engine/ (Python, FastAPI)  -->  SQLite
                                     ^
 cron / CLI  ------------------------+   (batch)
```

`engine` เป็นเจ้าของฐานข้อมูลเพียงฝ่ายเดียว ส่วน `web` อ่านและเขียนผ่าน HTTP API ของ `engine` เท่านั้น

- ทางเลือกอื่น: ให้ `web` อ่าน SQLite ตรงๆ ปฏิเสธเพราะ schema จะผูกกับสองภาษา แก้ทีหนึ่งต้องแก้สองที่
- ทางเลือกอื่น: ทำ UI เป็น Python ล้วน ปฏิเสธเพราะผู้ใช้เลือก Next.js ไว้แล้วเพื่อขึ้น Vercel ภายหลัง

### D2. Engine แบ่ง 3 ชั้น: `sources/` → `core/` ← `batch`

- `sources/` คือ adapter ของ yfinance และ thaifin ที่แปลงข้อมูลเป็นรูปแบบกลาง (ราคารายวันเป็น DataFrame `open/high/low/close/volume`, งบรายไตรมาสเป็น DataFrame ที่มีชื่อ field ของเราเอง) และทำการ clean ข้อมูลตาม spec `market-data`
- `core/` คือ pure function หนึ่งไฟล์ต่อหนึ่ง capability (`quality`, `fair_value`, `cdc`, `catalyst`, `risk_reward`, `candidates`) รับข้อมูลรูปแบบกลางกับ config แล้วคืนผลการประเมินที่มีเหตุผลประกอบ ไม่มี I/O
- `batch` ประกอบทุกส่วนเข้าด้วยกัน: ดึงข้อมูล → ประเมิน → เขียนลง DB

การแยกแบบนี้ทำให้ test `core/` ด้วย fixture ได้ และเปลี่ยนไปใช้ SETSMART ได้ด้วยการเพิ่ม adapter ใหม่ใน `sources/` เท่านั้น ใช้ `typing.Protocol` เป็น interface ของแหล่งข้อมูล ไม่สร้าง base class หรือ factory

### D3. SQLite ผ่าน `sqlite3` ของ stdlib และเก็บผลประเมินเป็น JSON

ตารางหลัก: `stocks`, `prices_daily`, `financials_quarterly`, `runs` (สถานะ, เวลา, จำนวน), `run_failures`, `evaluations` (หนึ่งแถวต่อ run ต่อหุ้น มีผลทุก gate เป็น JSON) และ `manual_events`

- ทางเลือกอื่น: ORM (SQLAlchemy) ปฏิเสธเพราะมีตารางไม่กี่ตาราง และ query ตรงไปตรงมา
- เก็บผลประเมินเป็น JSON แทนการแตกเป็นหลายคอลัมน์ เพราะหน้า UI อ่านทั้งก้อน และโครงสร้างผลยังเปลี่ยนได้บ่อยในช่วงแรก
- connection เปิดต่อ request และ FastAPI อาจเปิดกับใช้คนละ thread จึงเปิดด้วย `check_same_thread=False` (แต่ละ connection ยังใช้กับ request เดียว)

### D4. ลำดับของ batch: liquidity ก่อน แล้วค่อยดึงงบ

1. ดึงรายชื่อหุ้นและ sector จาก thaifin
2. ดึงราคา 1 ปีของทุกหุ้นจาก yfinance แบบ batch ครั้งละประมาณ 100 ticker
3. คำนวณ liquidity แล้วดึงงบจาก thaifin เฉพาะหุ้นที่ผ่าน ทีละตัว พร้อม `try/except` รายตัว
4. คำนวณ peer PE จากหุ้นที่มีงบ แล้วประเมินทุกหุ้น
5. เขียนผลทั้งหมดลง DB ใน transaction เดียวตอนจบ เพื่อไม่ให้ UI เห็นผลครึ่งๆ กลางๆ

ดึงราคาใหม่ทั้งปีทุกครั้งแทนการดึงแบบ incremental เพราะ yfinance แบบ batch เร็วพอ และไม่ต้องจัดการกรณี split หรือ adjust ย้อนหลัง

### D5. กัน batch รันซ้อนด้วยแถวในตาราง `runs`

ก่อนเริ่ม batch ทั้ง CLI และ API เช็คว่ามี run ที่สถานะ `running` อยู่หรือไม่ ถ้า run นั้นค้างนานเกิน 30 นาทีให้ถือว่าตาย (process crash) แล้ว mark เป็น `failed` API เริ่ม batch ด้วย background task ของ FastAPI แล้วตอบกลับทันที UI จึง poll สถานะเอา

- ทางเลือกอื่น: job queue (Celery, RQ) ปฏิเสธเพราะใช้คนเดียวและรันวันละครั้ง

### D6. Config เป็น YAML ไฟล์เดียว และ validate ด้วย pydantic

`engine/config.yaml` เก็บเกณฑ์ทั้งหมด: liquidity, quality, จำนวนไตรมาสขั้นต่ำ, รายชื่อ sector การเงิน, เกณฑ์ valuation ที่เปิดใช้, ค่าความยาว EMA, window ของ ETA, state ที่รับเข้า candidate list, เกณฑ์ MoS และ RRR, mapping sector → catalyst hints และวัน SET50/100 review โหลดใหม่ทุกครั้งที่รัน batch ใช้ pydantic เพราะได้มาจาก dependency ของ thaifin อยู่แล้ว และ config ที่ผิดจะ error ตั้งแต่ตอนเริ่มรัน

### D7. Toolchain

- Engine: `uv` จัดการ Python 3.13 กับ dependency ใน `pyproject.toml`, ใช้ `pytest` สำหรับ test และ FastAPI + uvicorn สำหรับ API
- Web: Next.js App Router ใช้ `bun` และ Tailwind ที่มากับ `create-next-app` หน้าเว็บอ่านข้อมูลจาก `ENGINE_URL` ใน server component
- ตั้งเวลาบน local ด้วย cron ของเครื่องให้เรียก CLI ของ engine หลังตลาดปิดในวันทำการ ถ้าวันนั้นเป็นวันหยุด batch จะได้ข้อมูลเดิมซึ่งไม่มีผลเสีย

### D8. Phase 0: backtest CDC ก่อนสรุปว่าจะใช้ CDC เป็น gate

ทำ script แยกใน `engine/scripts/` ที่ใช้ราคา 3 ปีของหุ้นที่ผ่าน liquidity แล้ววัดว่ามีกี่ % ของวันที่หุ้นเข้า state `bear-approaching` แล้วเกิด cross จริงภายใน 20 วันทำการ ผลจะตัดสินค่า default ของ state ที่รับใน config (ดู spec `candidate-list`) ไม่ต้องแก้ code

เพื่อไม่ให้เกิด look-ahead bias script นับเฉพาะวันที่หุ้นผ่าน liquidity filter ณ วันนั้น (traded value 20 วันก่อนหน้า) ไม่ใช่สภาพคล่องของวันนี้ และรายงาน median return 20 และ 60 วันทำการหลังเข้า state `bear-approaching` เทียบกับ `bear-far` เพราะสิ่งที่ต้องการรู้คือเงินแช่สั้นลงหรือไม่ ไม่ใช่แค่ว่าเกิด cross ยังแก้ survivorship bias ไม่ได้ เพราะ yfinance ไม่มีหุ้นที่ถูกถอนออกจากตลาด

## Risks / Trade-offs

- [thaifin พังหรือ Finnomena เปลี่ยน API] → error ถูกจำกัดอยู่รายหุ้น และ batch บันทึกจำนวนหุ้นที่ fail ถ้าพังทั้งหมด หน้า UI ยังแสดงผลของ run ที่สำเร็จล่าสุด และทางออกระยะยาวคือ adapter SETSMART ตาม D2
- [yfinance โดน rate limit] → ดึงเป็น chunk และหน่วงเวลาระหว่าง chunk ถ้ายังโดน ให้ลดขนาด chunk ใน config
- [ROE ของ thaifin คือกำไรไตรมาสเดียว × 4 (ตรวจแล้วใน task 2.4) ไตรมาสที่กำไรพิเศษทำให้หุ้นผ่าน gate ได้] → quality gate ใช้ ROE TTM ที่คำนวณเองจากกำไรสุทธิ 4 ไตรมาสและส่วนผู้ถือหุ้น ข้อเสียคือ TTM ตอบสนองช้าต่อหุ้นที่กำลังฟื้น ซึ่ง inflection flag ช่วยชี้ไว้แล้ว
- [PE ย้อนหลังที่ EPS TTM ใกล้ศูนย์ทำให้ค่าเฉลี่ยเพี้ยน และ yield ของ thaifin มีค่าผิดปกติบางไตรมาส] → ทุก band ใช้ median และ PE band ตัด PE > 100 ออกก่อน
- [หุ้นที่ควบรวมหรือปรับโครงสร้าง (เช่น GULF) ทำให้ PE/PBV ย้อนหลังไม่มีความหมาย] → ติดป้ายเตือนเมื่อส่วนผู้ถือหุ้นเปลี่ยนเกิน 50% ระหว่างไตรมาสในกรอบ 5 ปี (ตัดสินใน task 8.2) ใช้ส่วนผู้ถือหุ้นอย่างเดียว ไม่ใช้จำนวนหุ้น เพราะการแตกพาร์เปลี่ยนจำนวนหุ้นแต่ไม่เปลี่ยนตัวธุรกิจ (GULF 2Q25 เปลี่ยน 173%, SCAP ที่แตกพาร์ปี 2023 เปลี่ยนไม่เกิน 12%)
- [thaifin ปรับราคาตามการแตกพาร์แต่ไม่ปรับ BVPS และปรับ EPS แค่บางไตรมาส (SCAP ปี 2022: ราคา 4.83 เทียบ 26.75 บน SET แต่ BVPS 8.18 ไม่ปรับ ทั้งตลาด 54 จาก 165 ตัวมีจำนวนหุ้นตาม BVPS ไม่คงที่ใน 5 ปี)] → คำนวณ PE/PBV band ระดับบริษัทจาก market cap ÷ กำไรหรือส่วนผู้ถือหุ้น แล้วแปลงเป็นต่อหุ้นด้วยจำนวนหุ้นปัจจุบัน ซึ่งรองรับการเพิ่มทุนด้วย ต้องตรวจ market cap ของ thaifin กับ SET ก่อนใช้
- [CDC ที่คำนวณเองไม่ตรงกับ TradingView เพราะวิธีเริ่มต้น EMA ต่างกัน] → ใช้ราคา 1 ปีเพื่อให้ EMA ลู่เข้า และมี task เทียบค่ากับ TradingView
- [สูตรเดิมใน spec (ohlc4 + EMA 2) ต่างจาก CDC ActionZone V3 2020 ที่ผู้ใช้ตั้งไว้ (close, smoothing 1) ราว 0.2% ทำให้วัน cross อาจไม่ตรงกับ chart ที่ใช้เทรดจริง (พบใน task 3.2)] → ใช้ close และ smoothing 1 เป็น default โดยเลือก ohlc4 ได้ใน config
- [peer PE คิดจากหุ้นที่ผ่าน liquidity เท่านั้น] → sector ที่มีหุ้นสภาพคล่องน้อยจะมี peer น้อย ถ้า peer น้อยกว่า 3 ตัว ให้ peer PE เป็น N/A
- [dividend yield band ใช้ yield จาก thaifin ซึ่งอิงราคาของ thaifin] → ยอมรับได้ เพราะใช้เทียบกับค่าเฉลี่ยของตัวเองเท่านั้น
- [SQLite ใช้กับ Vercel ไม่ได้] → ตั้งใจไว้แล้ว เพราะการย้ายไป Postgres เป็นขั้นสุดท้ายตาม proposal และการที่ `engine` เป็นเจ้าของ DB ฝ่ายเดียว (D1) ทำให้ต้องแก้แค่ชั้นเดียว
