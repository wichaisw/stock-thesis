# stock-thesis

คัดหุ้น SET/mai ที่พื้นฐานดี ราคาต่ำกว่า fair value และ CDC ActionZone (daily) ใกล้ cross ออกมาเป็น candidate list รายวัน ใช้คนเดียวบนเครื่อง local

```
web/ (Next.js)  --HTTP-->  engine/ (Python, FastAPI)  -->  SQLite (engine/shortlist.db)
                                ^
cron / CLI  --------------------+  batch
```

spec ของระบบอยู่ใน `openspec/specs/` (change ที่ทำเสร็จแล้วอยู่ใน `openspec/changes/archive/`) ผลตรวจข้อมูลและ backtest อยู่ใน `engine/README.md`

## ติดตั้ง

ต้องมี [uv](https://docs.astral.sh/uv/) (จัดการ Python 3.13 ให้เอง) และ [bun](https://bun.sh)

```sh
brew install uv bun

cd engine && uv sync && uv run playwright install chromium && cd ..
cd web && bun install && cp .env.example .env.local && cd ..
```

## รัน

เปิด 2 terminal

```sh
# 1. engine API ที่ http://127.0.0.1:8000
cd engine && uv run uvicorn shortlist.api:app --port 8000

# 2. web ที่ http://localhost:3000
cd web && bun run dev        # หรือ bun run build && bun run start
```

ครั้งแรกยังไม่มีข้อมูล กดปุ่ม **รัน batch** ในหน้าเว็บ หรือรันจาก command line

```sh
cd engine && uv run shortlist-batch
```

batch ทั้งตลาดใช้ราว 5 นาที (ดึงราคาทุกตัวจาก yfinance และงบจาก thaifin เฉพาะตัวที่ผ่าน liquidity) รันซ้อนกันไม่ได้ ถ้า run ค้างเกิน 30 นาทีจะถูกถือว่าตาย และหยุดเองเมื่อเกิน 20 นาที

ค่าที่ปรับได้ผ่าน env

| ตัวแปร | ที่ใช้ | default |
|---|---|---|
| `ENGINE_URL` | web (`web/.env.local`) | `http://127.0.0.1:8000` |
| `SHORTLIST_DB` | engine API | `engine/shortlist.db` |

## รันเองทีละอย่าง

ทุกคำสั่งรันจาก root ของ repo

| ทำอะไร | คำสั่ง | ใช้เวลา | ผลอยู่ที่ |
|---|---|---|---|
| batch (ดึงข้อมูลและประเมินทั้งตลาด) | `cd engine && uv run shortlist-batch` | ราว 5 นาที | `engine/shortlist.db` และหน้าเว็บ |
| batch ลง DB อื่น หรือ config อื่น | `cd engine && uv run shortlist-batch --db /tmp/test.db --config config.yaml` | ราว 5 นาที | DB ที่ระบุ |
| เติมประวัติประเภทนักลงทุนรายวันย้อนหลัง | `cd engine && uv run shortlist-backfill-flow` | ราว 3 นาที | ตาราง `investor_flow` |
| backtest fair value และ candidate rule | `uv run --project engine python .agents/skills/fair-value-backtest/backtest.py` | ครั้งแรกราว 8 นาที, ใช้ cache ราว 1 นาที | `docs/backtests/fair-value-<วันที่>.md` |
| backtest เดิมแต่ดึงข้อมูลใหม่ทั้งหมด | เติม `--refresh` ท้ายคำสั่งข้างบน | ราว 8 นาที | เหมือนข้างบน (cache อยู่ใน `engine/.cache/fv-backtest/`) |
| backtest CDC `bear-approaching` | `cd engine && uv run python scripts/backtest_cdc.py` | ราว 1.5 นาที | พิมพ์ออกจอ |
| ทดสอบ | `cd engine && uv run pytest` และ `cd web && bun run lint` | ราว 30 วินาที | ออกจอ |

ข้อควรรู้ตอนรันเอง

- **เลี่ยงช่วง 17:00–18:30 น.** Yahoo จำกัดจำนวน request หลังตลาดปิด batch จึงช้าและได้ราคาไม่ครบ (batch ดึงซ้ำหุ้นที่ขาดให้หนึ่งรอบ บรรทัด `ดึงราคาซ้ำ N ตัว ได้คืน M ตัว` ใน log บอกว่าโดนจำกัดแค่ไหน)
- **ราคาปิดของวันนี้** ได้หลังตลาดปิด (16:30 น.) ถ้ารันระหว่างวัน ราคาและข้อมูลประเภทนักลงทุนจะเป็นค่าระหว่างวัน
- **DB เก็บผลประเมินของ run ล่าสุดเท่านั้น** ถ้าจะเทียบก่อนและหลังแก้อะไร ให้เก็บ evaluations ของ run เดิมไว้ก่อนรัน (เช่น `sqlite3 engine/shortlist.db "select * from evaluations" > before.csv`) ส่วน candidate ของแต่ละวันยังอยู่ในหน้า **ประวัติ candidate**
- **log** ของ batch ที่รันจาก command line ออกจอ ของ cron อยู่ในไฟล์ที่ตั้งใน crontab (ตัวอย่างข้างล่างใช้ `/tmp/shortlist-batch.log`) ถ้าจะเก็บ log ของ engine API ให้รันแบบ `uv run uvicorn shortlist.api:app --port 8000 > /tmp/shortlist-api.log 2>&1`
- **restart** engine API: กด Ctrl+C ใน terminal ที่รันอยู่แล้วรันใหม่ ถ้ารันไว้เบื้องหลังให้ใช้ `pkill -f "uvicorn shortlist.api:app"` web (`bun run dev`) โหลด code ใหม่เอง แต่ถ้าหน้าเว็บยังแสดงแบบเก่าให้ restart เหมือนกัน

## แก้เกณฑ์

เกณฑ์กรองหุ้น (liquidity, quality gate, เกณฑ์ fair value ที่เปิดใช้, CDC state และ ETA, MoS, RRR) แก้ได้ที่หน้า **ตั้งค่า** ของเว็บ (ปุ่ม "ปรับเกณฑ์" ข้างปุ่มรัน batch บนหน้า candidates) แต่ละช่องมี tooltip อธิบายว่าเพิ่มหรือลดค่าแล้วผลเปลี่ยนอย่างไร ค่าที่แก้เก็บใน `engine/shortlist.db` และมีผลกับ batch ครั้งถัดไปทั้งจากปุ่มบนเว็บและ cron

`engine/config.yaml` เป็นค่า default ของทุกเกณฑ์ (ปุ่มคืนค่า default บนหน้าตั้งค่าจะกลับไปใช้ค่าในไฟล์นี้) และเป็นที่เดียวที่แก้สูตร CDC (ต้องตรงกับ TradingView), รายชื่อ sector การเงิน, catalyst hints, วัน SET50/100 review และค่าของ batch ค่าสัดส่วนในไฟล์เขียนเป็นทศนิยม (`0.10` = 10%) ลำดับการรวมค่าอยู่ใน `engine/README.md` ส่วน "ค่าเกณฑ์มาจากไหน"

batch โหลด config ใหม่ทุกครั้ง แก้ค่าแล้วกดรัน batch ใหม่ได้เลยไม่ต้อง restart ถ้าใส่ค่าผิดประเภทหรือสะกดชื่อ key ผิด batch จะ error พร้อมบอกชื่อ field แต่ถ้า**เพิ่มหรือลบ key** ใน `config.yaml` (มักมากับการแก้ code ของ engine) ต้อง restart engine API ไม่อย่างนั้น API ที่ยังรัน code เก่าจะตอบ 500 และเว็บขึ้น "engine ตอบ 500"

## มูลค่าซื้อขายตามประเภทนักลงทุน

ทุก batch ดึงมูลค่าซื้อ/ขายของตลาด SET แยกตามสถาบันในประเทศ, บัญชีบริษัทหลักทรัพย์, ต่างชาติ และรายย่อยในประเทศ ของวันซื้อขายล่าสุดเก็บไว้ใน `engine/shortlist.db` ดูได้ที่หน้า **ประเภทนักลงทุน** (ลิงก์ข้างปุ่ม "ปรับเกณฑ์" บนหน้า candidates)

- SET ให้แค่วันล่าสุด ประวัติจึงเริ่มสะสมจากวันแรกที่รัน batch และวันที่ไม่ได้รันจะขาดหายไป
- ถ้ารัน batch ก่อน 17:00 น. ของวันซื้อขาย ข้อมูลยังไม่ใช่ค่าปิดตลาดและมีป้าย "ระหว่างวัน" รันอีกครั้งหลังตลาดปิดจะเขียนทับเป็นค่าปิดตลาด
- ดึงผ่าน headless Chromium (Playwright) จึงต้องรัน `uv run playwright install chromium` หนึ่งครั้งตอนติดตั้ง ถ้าดึงไม่ได้ batch ยังจบตามปกติ เหตุผลอยู่ใน log
- ประวัติรายวันก่อนหน้านั้นเติมได้ด้วย `cd engine && uv run shortlist-backfill-flow` จากข่าวสรุปรายวันของ InfoQuest ย้อนได้ราว 4 เดือน (เริ่ม 17 มิ.ย. 2026) ไม่ทับวันที่ดึงจาก SET เอง และไม่เขียนอะไรถ้าตัวเลขไม่ตรงกับ SET บางวันไม่มีข่าว (27–28 ส.ค. 2026) แถวที่เติมมีป้าย "InfoQuest"

## ตั้งเวลา batch หลังตลาดปิด

SET ปิด 16:30 น. ตัวอย่าง crontab (`crontab -e`) ให้รันจันทร์–ศุกร์ 18:30 น. วันหยุดตลาดจะได้ข้อมูลเดิมซึ่งไม่มีผลเสีย

```cron
30 18 * * 1-5 cd /path/to/stock-thesis/engine && /opt/homebrew/bin/uv run shortlist-batch >> /tmp/shortlist-batch.log 2>&1
```

cron ไม่มี `PATH` ของ shell จึงต้องใส่ path เต็มของ `uv` (ดูด้วย `which uv`) และเครื่องต้องเปิดอยู่ตอนนั้น

## ทดสอบ

```sh
cd engine && uv run pytest
cd web && bun run lint && bun run build
```

## ข้อจำกัดของข้อมูล

yfinance และ thaifin (ซึ่งดึงจาก API ภายในของ Finnomena) เป็น library ที่ไม่เป็นทางการและตั้งใจไว้สำหรับใช้ส่วนตัว ถ้าจะเปิดให้คนอื่นใช้ ให้เปลี่ยนไปใช้ SETSMART โดยเพิ่ม adapter ใน `engine/shortlist/sources/`

ข้อมูลประเภทนักลงทุนมาจาก API ของเว็บ set.or.th ที่ SET ไม่ได้เปิดให้ใช้อย่างเป็นทางการ SET เปลี่ยน API หรือบล็อก headless browser เมื่อไหร่ก็ได้ ใช้คนเดียวบน local เท่านั้น
