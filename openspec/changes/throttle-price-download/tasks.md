## 1. Config

- [x] 1.1 เพิ่ม `price_threads` (`gt=0`) และ `price_retry_delay_seconds` (`ge=0`) ใน `Batch` ของ `engine/shortlist/config.py` ใส่ `price_threads: 4`, `price_retry_delay_seconds: 30` และเปลี่ยน `chunk_delay_seconds` เป็น 3.0 ใน `engine/config.yaml` ตรวจ: `uv run pytest tests/test_config.py` ผ่าน และ config ที่ขาดค่าใหม่โหลดไม่ผ่าน

## 2. ดึงราคา

- [x] 2.1 `YahooPrices` รับ `threads` และ `retry_delay_seconds` ส่ง `threads=self.threads` ให้ `yf.download` แยกลูปชุดเป็น helper แล้วดึงซ้ำหุ้นที่ขาดหนึ่งรอบตาม D2 เก็บ `last_retry` ตาม D3 ให้ parameter ใหม่มี default เท่ากับ config (4 และ 30) เพื่อให้ `YahooPrices()` ที่เรียกแบบไม่ส่งค่าใน test ยังใช้ได้ ตรวจ: test ใหม่ใน `tests/test_sources.py` ที่ patch `yf.download` ครอบ scenario ทั้ง 4 ของ spec (ได้คืนบางตัว, ครบตั้งแต่รอบแรกไม่พัก, รอบแรกไม่ได้เลยไม่ดึงซ้ำ, `threads` ที่ส่งเท่ากับ config) โดย patch `time.sleep` ไม่ให้รอจริง
- [x] 2.2 `batch.py` และ `scripts/backtest_cdc.py` ส่งค่าใหม่ให้ `YahooPrices` batch log "ดึงราคาซ้ำ N ตัว ได้คืน M ตัว" ต่อจากบรรทัด "ได้ราคา" เมื่อ `last_retry` มีค่า ตรวจ: `uv run pytest` ผ่านทั้งหมด

## 3. ตรวจกับ batch จริง

- [x] 3.1 รัน batch จริงหนึ่งรอบ จดเวลาช่วงดึงราคา, เวลารวม, จำนวนที่ดึงซ้ำและได้คืน เทียบกับ run 31 (568 วินาที, 828/930) และ run 30 แล้วแก้ comment "ปกติ 2–3 นาที" ของ `max_run_minutes` ใน config.yaml ให้ตรงเวลาที่วัดได้ ตรวจ: ตัวเลขทั้งหมดบันทึกใน `engine/README.md` และ fail เพราะไม่มีราคาใกล้ระดับ run 30 (11 ตัว)
- [ ] 3.2 สุ่ม 3 หุ้นที่ได้คืนจากรอบซ้ำ เทียบราคาปิดล่าสุดกับ TradingView ตรวจ: ราคาปิดตรงกัน
