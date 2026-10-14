# Proposal

## Why

run 15 (14 ต.ค. 2026) ใช้เวลา 2 ชม. 18 นาที แทนที่จะเป็นราว 2 นาที เพราะ DNS ล่มระหว่างรัน หุ้น 53 ตัวไม่ได้ราคา และดึงงบไม่ได้อีก 10 ตัว (`[Errno 8] nodename nor servname provided`) แต่ batch ยังทำต่อทีละตัวจนจบ แล้วบันทึก run เป็น "succeeded" พร้อมหุ้นที่ fail 67 ตัว candidate list จึงถูกแทนด้วยข้อมูลที่ไม่ครบโดยไม่มีอะไรเตือน

ตรวจแล้วว่าแต่ละ request มี timeout อยู่แล้ว (httpx ของ thaifin 5 วินาที ลอง 3 ครั้ง, yfinance 10–30 วินาทีพร้อม retry ของตัวเอง) ปัญหาจึงไม่ใช่ request ที่ค้างตลอดไป แต่เป็นการที่ batch ไม่มีเพดานรวม และแยกไม่ออกระหว่าง "หุ้นตัวนี้ไม่มีข้อมูล" กับ "เครือข่ายใช้ไม่ได้" log ของ engine ก็ไม่มีเวลา จึงบอกไม่ได้ว่าช่วงไหนกินเวลา 2 ชั่วโมง

## What Changes

- Batch หยุดและบันทึก run เป็น failed เมื่อหุ้น fail ด้วย error ของเครือข่ายติดกัน 5 ตัว (ปรับได้ใน config) error ที่ไม่ใช่เครือข่าย เช่น "Stock with symbol X not found" ไม่นับ
- Batch หยุดและบันทึก run เป็น failed เมื่อใช้เวลารวมเกิน 20 นาที (ปรับได้ใน config)
- run ที่ failed ไม่แทน candidate list เดิม (เป็นพฤติกรรมที่มีอยู่แล้วของ run ที่ failed) และ UI แสดงเหตุผลที่หยุด
- log ของ engine มีเวลาและระยะเวลาของแต่ละช่วง (รายชื่อหุ้น, ราคา, งบและ market cap, ประเมิน)
- ค่าเพดานทั้งสองอยู่ในส่วน `batch` ของ `engine/config.yaml` ไม่อยู่บนหน้า settings

นอกขอบเขต:
- ลองดึงหุ้นที่ fail ซ้ำในรอบท้าย
- เปลี่ยน timeout หรือจำนวน retry ของ yfinance และ thaifin
- เก็บผลบางส่วนของ run ที่ถูกหยุดไว้ดู (run ที่ failed ไม่มี evaluations)
- แจ้งเตือนนอกแอป (เช่น push notification) เมื่อ batch จาก cron ล้ม

## Capabilities

### New Capabilities
- (ไม่มี)

### Modified Capabilities
- `market-data`: requirement "หุ้นแต่ละตัว fail ได้โดยไม่ล้มทั้ง batch" มีข้อยกเว้นเมื่อเครือข่ายใช้ไม่ได้ และเพิ่ม requirement เวลารวมสูงสุดของ batch และ log ระยะเวลาของแต่ละช่วง

## Impact

- **Code:** `engine/shortlist/batch.py` (นับ error ของเครือข่ายติดกัน, เช็คเวลารวม, log ระยะเวลา), `engine/shortlist/sources/` (request ตรวจว่าเชื่อมต่อแหล่งราคาได้ เพราะ yfinance รายงานเน็ตล่มเป็น "ไม่มีข้อมูล"), `engine/shortlist/config.py` และ `engine/config.yaml` (ส่วน `batch`), `engine/shortlist/api.py` (เวลาใน log format) และ test
- **ผลต่อผู้ใช้:** เมื่อเน็ตล่ม batch จะ fail ภายในไม่กี่นาทีพร้อมเหตุผลบนหน้า candidates แทนการรันนานแล้วแสดง list ที่ไม่ครบ ไม่เปลี่ยนวิธีประเมินหุ้น
- **ความสัมพันธ์กับ change อื่น:** ไม่บล็อกและไม่ถูกบล็อกโดย `investor-type-flow` แต่ถ้า change นั้นเพิ่มการดึงข้อมูลจาก SET ใน batch ควรให้ error ของเครือข่ายนับรวมกับกลไกนี้ด้วย
