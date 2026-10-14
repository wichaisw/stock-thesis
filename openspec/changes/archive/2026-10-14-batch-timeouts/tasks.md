# Tasks

## 1. Config และ error ของแหล่งราคา

- [x] 1.1 เพิ่ม `max_consecutive_network_errors` (default 5) และ `max_run_minutes` (default 20) ในส่วน `batch` ของ `engine/config.yaml` และ `Batch` ใน `config.py` โดยไม่ใส่ `editable` (design D4) ตรวจด้วย `uv run pytest` ที่มี test ว่าโหลด default ได้, ค่าผิดประเภท error พร้อมชื่อ field และทั้งสองค่าไม่อยู่ใน `editable_fields()`
- [x] 1.2 เพิ่ม `PriceSource.reachable()` และทำใน `YahooPrices` ด้วย `urllib.request.urlopen` timeout 5 วินาที (design D1) และเพิ่มใน `FakePrices` ให้ตั้งผลได้ ตรวจด้วย `uv run pytest` ที่มี test ของ adapter (monkeypatch `urlopen`): ได้ response คืน `None`, `HTTPError` 429 คืน `None`, `URLError` ของ DNS คืนข้อความ "เชื่อมต่อแหล่งราคาไม่ได้: ..." และตรวจกับเครือข่ายจริงว่าคืน `None` ตอนเน็ตปกติ และคืนข้อความเมื่อตั้ง `HTTPS_PROXY=http://127.0.0.1:9`

## 2. หยุด batch เมื่อเน็ตล่มหรือช้าเกิน

- [x] 2.1 เพิ่ม `is_network_error`, `RunGuard` และ `BatchAborted` ใน `batch.py` แล้วเรียกในช่วงราคาและช่วงงบตาม design D2–D3 และให้ `execute` บันทึกเหตุผลของ `BatchAborted` โดยไม่มีชื่อ class นำหน้า ตรวจด้วย `uv run pytest` ที่มี test ของทุก scenario ใน spec `market-data` ที่เกี่ยวกับการหยุด: เครือข่ายล่มระหว่างรัน (5 ตัวติดกันในช่วงงบ, หุ้นที่เหลือไม่ถูกเรียก, run เป็น failed, run ที่สำเร็จครั้งก่อนยังเป็นล่าสุดที่สำเร็จ), เครือข่ายล่มช่วงดึงราคา, ไม่มีราคาแต่เครือข่ายใช้ได้ (เหตุผลคงเดิม ไม่หยุด), ไม่ได้ market cap ตอนเครือข่ายล่ม (หุ้น fail และนับ), ไม่ได้ market cap แต่เครือข่ายใช้ได้ (ประเมินต่อ band เป็น N/A), error ของเครือข่ายสลับกับหุ้นที่ไม่มีอยู่ (ไม่หยุด), batch ช้าเกินเพดาน (monkeypatch `time.monotonic`), batch ปกติ และ `is_network_error` กับข้อความจริงจาก run 15 (`[Errno 8] nodename nor servname provided`, `curl: (6) Could not resolve host`) กับ "Stock with symbol FLE not found." ที่ต้องไม่นับ
- [x] 2.2 แปลง error ของเครือข่ายจาก `list_stocks()` เป็น `BatchAborted` ที่มีเหตุผล "เครือข่ายใช้ไม่ได้: ดึงรายชื่อหุ้นไม่ได้: ..." (design D3, เพิ่มหลังพบใน task 4.2) ตรวจด้วย `uv run pytest` ที่มี test ของ scenario "เครือข่ายล่มตั้งแต่ดึงรายชื่อหุ้น" และว่า error ประเภทอื่นจาก `list_stocks()` ยังเป็น crash แบบเดิม (`test_crash_marks_run_failed`)

## 3. Log

- [x] 3.1 เพิ่มระยะเวลาของแต่ละช่วงและเวลารวมใน log ของ `collect`, เวลาใน formatter ของ API และเวลาหน้าข้อความของ CLI และ log เหตุผลเมื่อถูกหยุด (design D5) ตรวจด้วย `uv run pytest` ที่มี test ว่า log ของ `collect` มีระยะเวลาครบทุกช่วง แล้วรัน `uv run shortlist-batch` หนึ่งครั้งดูว่าทุกบรรทัดมีเวลาและแต่ละช่วงมีระยะเวลา และกดรันจาก UI ดูใน log ของ API เช่นกัน

## 4. ตรวจกับเครือข่ายจริง

- [x] 4.1 รัน `uv run shortlist-batch` ตอนเน็ตปกติ ตรวจว่า run เป็น succeeded, fail 8 ตัวเท่ากับ run 17 และ candidate list เทียบกับ run 17 ไม่เปลี่ยนเพราะ change นี้ (change นี้ไม่เปลี่ยนวิธีประเมิน จึงไม่ต้องเทียบกับ SET)
- [x] 4.2 จำลองเน็ตล่มด้วยการชี้ `HTTPS_PROXY` ไปที่ port ที่ไม่มีอะไรฟัง (เช่น `HTTPS_PROXY=http://127.0.0.1:9 uv run shortlist-batch`) ตรวจว่า batch fail ภายใน 2 นาทีด้วยเหตุผลว่าเครือข่ายใช้ไม่ได้ หน้า candidates ยังแสดง list ของ run ที่สำเร็จครั้งก่อนพร้อมข้อความ "รันล่าสุดล้มเหลว" (skill `orca-browser-check`) และบันทึกผลกับข้อความ error ที่ได้จริงใน `engine/README.md` ถ้าข้อความ error ของ proxy ไม่อยู่ใน `NETWORK_ERROR_PATTERNS` ให้หยุดและถามก่อนเพิ่ม
