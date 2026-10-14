# Design

## Context

- `batch.collect()` ทำงานเป็นช่วง: `fin_src.list_stocks()` → `prices_src.fetch_prices()` (yfinance `download` ทีละ 100 ตัว) → วนหุ้นที่ผ่าน liquidity ทีละตัวเรียก `fetch_quarterly` (thaifin) และ `fetch_market_caps` (yfinance `history` + `get_shares_full`) → ประเมิน error ต่อหุ้นถูกจับเป็นข้อความใน `failures`
- `batch.execute()` จับ `BaseException` แล้ว `db.fail_run()` อยู่แล้ว และหน้า candidates อ่านจาก run ที่สำเร็จล่าสุด run ที่ failed จึงไม่แทน candidate list และ `run-button.tsx` แสดง "รันล่าสุดล้มเหลว: <error>" อยู่แล้ว
- timeout ที่มีอยู่ (ตรวจใน site-packages 14 ต.ค. 2026): thaifin 1.1.0 ใช้ `httpx.Client()` (default 5 วินาที) + tenacity ลอง 3 ครั้ง รอ 4–10 วินาที และห่อ error เป็น `ValueError("An error occurred while fetching stock list: [Errno 8] ...")` yfinance 1.7.0 ใช้ timeout 10 วินาทีใน `download`/`history` และ 30 วินาทีใน request อื่น พร้อม retry error ชั่วคราวของตัวเอง
- yfinance 1.7.0 ซ่อน error ของเครือข่ายในการดึงราคา: ทดลองชี้ proxy ไปที่ port ที่ไม่มีอะไรฟัง (14 ต.ค. 2026) ทั้ง `yf.download` และ `Ticker.history` (แม้ตั้ง `hide_exceptions=False`) คืนข้อมูลว่างพร้อมข้อความ "possibly delisted; no price data found" โดยไม่ raise ตรงกับ log ของ run 15 ที่ TOP.BK ถูกรายงานว่า possibly delisted ส่วน `yfinance.shared._ERRORS` มีแต่ประกาศไว้ ไม่มีที่ไหนเขียน error ลงไป
- ผลคือตอนเน็ตล่ม `fetch_market_caps` ได้ประวัติราคาว่างแล้วคืน market cap ว่าง หุ้นจึงถูกประเมินต่อโดย PE/PBV/yield band เป็น N/A แทนที่จะ fail
- `PriceSource.fetch_prices()` คืน `dict[str, DataFrame]` อย่างเดียว batch จึงรู้แค่ว่าหุ้นไหนไม่มีราคา ไม่รู้ว่าเพราะอะไร
- log: CLI ใช้ `print` ส่วน API ใช้ logger `shortlist` ที่ format เป็น `%(levelname)s:     %(message)s` ไม่มีเวลาทั้งคู่
- เหตุที่ run 15 ใช้ 2 ชั่วโมงยังพิสูจน์ไม่ได้เพราะ log ไม่มีเวลา สมมติฐานที่น่าเป็นที่สุดคือการ resolve DNS ค้าง (ไม่อยู่ใต้ timeout ของ request ทุกทาง) คูณด้วย retry ของสองไลบรารี คูณหุ้น 242 ตัว change นี้ไม่ต้องพิสูจน์สมมติฐานก่อน เพราะเพดานเวลาและการนับ error ติดกันจำกัดผลได้ไม่ว่าสาเหตุคืออะไร และ log ที่มีเวลาจะบอกสาเหตุของครั้งถัดไป

## Goals / Non-Goals

**Goals:**
- เน็ตล่มแล้ว batch fail เร็วพร้อมเหตุผล และไม่แทน candidate list ด้วยข้อมูลไม่ครบ
- มีเพดานเวลารวมที่ใช้ได้ไม่ว่าจะช้าเพราะอะไร
- log บอกได้ว่าช่วงไหนกินเวลา

**Non-Goals:**
- ตัด request ที่ค้างอยู่กลางทาง (ไลบรารีไม่มีช่องให้ยกเลิกจากภายนอก)
- เปลี่ยน timeout หรือ retry ของ yfinance และ thaifin

## Decisions

### D1. ตรวจว่าแหล่งราคาเชื่อมต่อได้ เมื่อ yfinance คืนข้อมูลว่าง

เพิ่ม `PriceSource.reachable() -> str | None` คืน `None` เมื่อเชื่อมต่อแหล่งราคาได้ และคืนข้อความ error เมื่อเชื่อมต่อไม่ได้ `YahooPrices` ทำด้วย `urllib.request.urlopen("https://query2.finance.yahoo.com", timeout=5)` ของ stdlib: ได้ HTTP response ใดก็ตาม (รวม `HTTPError` เช่น 404 หรือ 429) ถือว่าเชื่อมต่อได้ ส่วน `URLError`, `TimeoutError` หรือ `OSError` อื่นถือว่าเชื่อมต่อไม่ได้ และคืน "เชื่อมต่อแหล่งราคาไม่ได้: <error>"

batch เรียก `reachable()` เฉพาะเมื่อ yfinance คืนข้อมูลว่าง:
- ช่วงราคา: หุ้นที่ไม่ได้ราคา ถ้าเชื่อมต่อไม่ได้ เหตุผล fail เป็น "ไม่มีข้อมูลราคา: <error>" และนับเป็น error ของเครือข่าย ถ้าเชื่อมต่อได้คงเป็น "ไม่มีข้อมูลราคา" ตามเดิม
- ช่วงงบ: `fetch_market_caps` คืน market cap ว่าง ถ้าเชื่อมต่อไม่ได้ หุ้นนั้น fail ด้วย "ดึง market cap ไม่ได้: <error>" และนับเป็น error ของเครือข่าย ถ้าเชื่อมต่อได้ประเมินต่อแบบเดิม (band เป็น N/A)

run ปกติมีหุ้นไม่ได้ราคาราว 8 ตัวและ market cap ว่างไม่กี่ตัว จึงเพิ่ม request ราว 10 ครั้ง ไม่เปลี่ยน `fetch_prices` และ `fetch_market_caps`

- ทางเลือกอื่น: อ่าน error ต่อ ticker จาก `yfinance.shared._ERRORS` ปฏิเสธเพราะ 1.7.0 ไม่เขียนลงไป และถึงมีก็เป็น "possibly delisted" ซึ่งแยกจากหุ้นที่ไม่มีข้อมูลจริงไม่ได้
- ทางเลือกอื่น: ดักข้อความจาก logger ของ yfinance ปฏิเสธด้วยเหตุผลเดียวกัน
- ทางเลือกอื่น: fail run เมื่อหุ้นไม่ได้ราคาเกินสัดส่วนหนึ่ง (ปกติ 0.9%, run 15 5.7%) ปฏิเสธเพราะเดาจากจำนวน และไม่จับกรณี market cap ว่าง
- ทางเลือกอื่น: ใช้ `httpx` หรือ `curl_cffi` ทำ request ตรวจ ปฏิเสธเพราะเป็น dependency ทางอ้อมของ thaifin และ yfinance ที่ไม่ได้ประกาศใน `pyproject.toml` และ stdlib พอสำหรับ request เดียว

### D2. แยก error ของเครือข่ายด้วยข้อความ ใน `batch.py`

ใช้กับ exception จาก thaifin และจาก `fetch_market_caps` (เช่น `get_shares_full` ที่ raise `curl: (6) Could not resolve host` ได้ ตาม log ของ run 15) ส่วนข้อมูลว่างของ yfinance ใช้ `reachable()` ตาม D1 `is_network_error(message: str) -> bool` ตรวจข้อความ (ไม่สนตัวพิมพ์) ว่ามีรูปแบบใดใน `NETWORK_ERROR_PATTERNS` เช่น `Could not resolve host`, `nodename nor servname`, `Name or service not known`, `Temporary failure in name resolution`, `Errno 8`, `curl: (6)`, `curl: (7)`, `curl: (28)`, `timed out`, `Connection refused`, `Network is unreachable`, `ConnectError`, `ConnectTimeout`, `ReadTimeout` รายการอยู่ในโค้ด ไม่อยู่ใน config

- ทางเลือกอื่น: แยกด้วยชนิดของ exception ปฏิเสธเพราะ thaifin ห่อทุกอย่างเป็น `ValueError` และ yfinance ไม่ raise เมื่อดึงราคาไม่ได้
- ทางเลือกอื่น: ใส่รูปแบบใน config ปฏิเสธเพราะเป็นรายละเอียดของไลบรารี ไม่ใช่เกณฑ์ที่ผู้ใช้ปรับ

### D3. `RunGuard` ใน `batch.py` นับ error ติดกันและเช็คเวลา

class เล็กหนึ่งตัวที่ batch สร้างตอนเริ่ม `collect`:
- `record(symbol, error: str | None)` เรียกต่อหุ้นตามลำดับ: error ของเครือข่ายเพิ่มตัวนับ อย่างอื่น (สำเร็จหรือ error ประเภทอื่น) รีเซ็ตเป็น 0 ครบ `batch.max_consecutive_network_errors` แล้ว raise `BatchAborted("เครือข่ายใช้ไม่ได้: หุ้น N ตัวติดกัน fail ด้วย error ของเครือข่าย ล่าสุด <symbol>: <error>")`
- `check(phase)` เทียบ `time.monotonic()` กับเวลาเริ่ม เกิน `batch.max_run_minutes` แล้ว raise `BatchAborted("ใช้เวลาเกิน M นาทีระหว่าง<phase>")`
- ช่วงราคา: หลัง `fetch_prices` คืนผล เรียก `record` ตามลำดับรายชื่อหุ้น (หุ้นที่ได้ราคานับเป็นสำเร็จ หุ้นที่ไม่ได้ราคาใช้ผลของ `reachable()` ตาม D1) แล้ว `check` ช่วงงบ: `check` ก่อนหุ้นแต่ละตัว และ `record` หลังแต่ละตัว (error ของงบ, error ของ market cap หรือ market cap ว่างขณะเชื่อมต่อไม่ได้) ช่วงประเมินเป็นการคำนวณในเครื่อง `check` ครั้งเดียวก่อนเริ่ม
- รายชื่อหุ้นเป็น request เดียวที่ทุกอย่างรอ ถ้า `list_stocks()` raise error ของเครือข่าย (ตาม D2) แปลงเป็น `BatchAborted("เครือข่ายใช้ไม่ได้: ดึงรายชื่อหุ้นไม่ได้: <error>")` ทันทีโดยไม่ต้องรอนับ 5 ครั้ง error ประเภทอื่นคงเป็น crash แบบเดิม (พบตอนตรวจ task 4.2: เน็ตล่มทั้งหมดทำให้ run fail ที่ request นี้ด้วย `ValueError` ดิบและ traceback)
- `BatchAborted` วิ่งออกไปที่ `execute()` ที่ `fail_run` อยู่แล้ว แก้ให้ `fail_run` ใช้แค่ข้อความของ `BatchAborted` (ไม่นำหน้าด้วยชื่อ class) เพื่อให้หน้า candidates อ่านง่าย ส่วน exception อื่นคงรูปแบบเดิม CLI จึงออกด้วย exit code ไม่เป็นศูนย์ ซึ่ง cron เห็นได้

- ทางเลือกอื่น: ใช้ thread หรือ `signal.alarm` ตัด batch เมื่อครบเวลา ปฏิเสธเพราะ batch จาก UI รันใน thread ของ API (signal ใช้ไม่ได้) และการฆ่า thread กลาง request ทิ้งสถานะไม่แน่นอน การเช็คระหว่างหุ้นพอเพราะแต่ละ request มี timeout อยู่แล้ว
- ทางเลือกอื่น: นับ error ของเครือข่ายทั้งหมด (ไม่ต้องติดกัน) ปฏิเสธเพราะ run ปกติมี error ประปรายได้ การนับติดกันแยก "เน็ตล่ม" ออกจาก "บางตัวมีปัญหา" ได้ดีกว่า

### D4. Config ในส่วน `batch` ไม่อยู่บนหน้า settings

เพิ่ม `max_consecutive_network_errors: 5` และ `max_run_minutes: 20` ใน `Batch` ของ `config.py` และ `config.yaml` ไม่ใส่ `editable` ส่วน `batch` ทั้งหมดจึงยังไม่อยู่บนหน้า settings

20 นาทีเพราะ run ปกติใช้ 2–3 นาที (run 16, 17) และ backtest ที่โดน yfinance จำกัดเคยช้าถึงราว 6 นาที เผื่อไว้ 3 เท่า

- ทางเลือกอื่น: ให้แก้บนหน้า settings ปฏิเสธตามที่ผู้ใช้เลือก

### D5. Log ที่มีเวลาและระยะเวลาของแต่ละช่วง

- `collect` จับเวลาแต่ละช่วงด้วย `time.monotonic()` แล้วต่อท้ายข้อความ log เดิมด้วยระยะเวลา เช่น "ได้ราคา 922 ตัว (41 วินาที)" และ log ระยะเวลารวมตอนจบ
- ใส่เวลาที่ต้นบรรทัด: API เพิ่ม `%(asctime)s` ใน formatter ของ logger `shortlist` และ CLI เติมเวลา `HH:MM:SS` หน้าข้อความใน `print`
- ตอนถูกหยุด ข้อความของ `BatchAborted` ถูก log ด้วย เพื่อให้ log ครบแม้ run fail

- ทางเลือกอื่น: บันทึกระยะเวลาของแต่ละช่วงลงตาราง `runs` ปฏิเสธเพราะยังไม่มีใครต้องดูย้อนหลังจาก UI เพิ่มเมื่อจำเป็น

## Risks / Trade-offs

- [หยุด run ที่ควรสำเร็จ: เน็ตกระตุกสั้นๆ ตรงหุ้น 5 ตัวติดกัน] → run fail ทั้งที่รันใหม่ก็สำเร็จ ผลเสียคือรอ cron รอบถัดไปหรือกดรันใหม่ candidate list ไม่หายเพราะใช้ run ที่สำเร็จครั้งก่อน retry ของไลบรารีเองช่วยลดโอกาสนี้แล้ว
- [กรณีแย่สุด: error ของเครือข่ายข้อความใหม่ที่ไม่อยู่ในรายการ] → ไม่นับ batch ทำต่อเหมือนเดิมจนชนเพดาน 20 นาที แล้วจึง fail เพดานเวลาจึงเป็นตาข่ายชั้นที่สอง และ log ที่มีเวลาจะบอกข้อความที่ต้องเพิ่ม
- [`reachable()` ตอบว่าเชื่อมต่อได้ แต่ yfinance ได้ข้อมูลว่างเพราะเน็ตกระตุกในช่วงนั้น] → หุ้นนั้นถูกบันทึกว่าไม่มีข้อมูลราคา หรือประเมินโดย band เป็น N/A เหมือนพฤติกรรมเดิม ถ้าเน็ตล่มต่อเนื่อง request ตรวจครั้งถัดไปจะเห็น
- [DNS lookup ของ `urlopen` ไม่อยู่ใต้ `timeout=5` ในทุกระบบ] → request ตรวจอาจช้ากว่า 5 วินาทีตอน DNS ค้าง แต่ batch หยุดหลังครบ 5 ครั้งติดกัน และเพดานเวลารวมยังทำงาน
- [Yahoo บล็อก request ตรวจ (เช่น 429)] → ยังถือว่าเชื่อมต่อได้ เพราะ request ตรวจตอบแค่ว่าเน็ตถึง Yahoo หรือไม่ ไม่ใช่ว่า Yahoo ให้ข้อมูลหรือไม่
- [เพดานเวลาตรวจระหว่างหุ้นเท่านั้น] → request ที่ค้างนานอาจทำให้เกินเพดานได้ไม่เกินเวลาของหุ้นหนึ่งตัว และช่วงดึงราคาทั้งหมดอยู่ในการเรียกครั้งเดียว จึงตรวจได้หลังจบช่วงเท่านั้น ถ้า DNS ค้างในช่วงราคานานกว่าที่คาด batch จะหยุดช้ากว่า 20 นาที log ที่มีเวลาจะแสดงให้เห็น
- [เพิ่ม method ใน `PriceSource`] → `FakePrices` ใน `tests/fakes.py` ต้องมี `reachable()` ด้วย `scripts/backtest_cdc.py` ไม่กระทบเพราะเรียกแค่ `fetch_prices`
