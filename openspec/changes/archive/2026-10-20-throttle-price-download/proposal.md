# Proposal

## Why

run 31 (cron 17:30 วันที่ 15 ต.ค. 2026 ราว 1 ชั่วโมงหลังตลาดปิด) ใช้เวลาช่วงดึงราคา 568 วินาที (run 30 ตอน 02:13 ใช้ทั้ง batch ราว 4 นาที) และได้ราคาแค่ 828 จาก 930 ตัว (run 30 fail ทั้งหมด 11 ตัว) log มี `curl: (28) Connection timed out after 10001 milliseconds` ของ yfinance 167 บรรทัด และ request ตรวจไปที่ `query2.finance.yahoo.com` ได้ 429

ตอนนี้ `yf.download` ดึงทีละ 100 ตัวด้วย `threads=True` ซึ่ง yfinance 1.7.0 แปลงเป็น `cpu_count × 2` thread (ราว 20 request พร้อมกัน) และพักระหว่างชุดแค่ 1 วินาที ช่วงหลังตลาดปิดที่คนดึงข้อมูลพร้อมกัน Yahoo จึงตัด connection หุ้นที่หายไปเป็นหุ้นที่มีราคาจริง ทำให้ candidate list ขาดหุ้นโดยไม่ใช่เพราะพื้นฐาน และเทียบ run กันไม่ได้ (joint batch ของวันนี้ต้องรันใหม่ตอนดึก)

## What Changes

- ดึงราคาด้วยจำนวน thread ที่กำหนดใน config (default 4) แทน `cpu_count × 2`
- พักระหว่างชุดของการดึงราคานานขึ้น (default 3 วินาที จากเดิม 1)
- หลังดึงครบทุกชุด หุ้นที่ไม่ได้ราคาจะถูกดึงซ้ำอีกหนึ่งรอบหลังพัก (default 30 วินาที) หุ้นที่รอบซ้ำยังไม่ได้ราคาจึง fail ด้วยเหตุผลเดิม
- log บอกจำนวนหุ้นที่ดึงซ้ำและที่ได้คืนมา
- ค่าใหม่อยู่ในส่วน `batch` ของ `engine/config.yaml` ไม่อยู่บนหน้า settings

นอกขอบเขต:
- หน่วงช่วงดึงงบและ market cap รายตัว (run 31 ไม่มีหลักฐานว่าช่วงนั้นโดนจำกัด เพิ่มเมื่อ run ไหนแสดงว่าโดน)
- retry ด้วย backoff หลายรอบ หรืออ่าน header `Retry-After`
- เปลี่ยนเวลา cron (อยู่ใน crontab ของผู้ใช้ ไม่อยู่ใน repo)
- เปลี่ยน `max_run_minutes` (คงไว้ 20 นาที แก้แค่ comment "ปกติ 2–3 นาที" หลังวัดเวลา run แรก)
- แยก 429 ออกจาก "ไม่มีข้อมูล" ในเหตุผลที่ fail

## Capabilities

### New Capabilities
- (ไม่มี)

### Modified Capabilities
- `market-data`: เพิ่ม requirement การดึงราคาแบบจำกัดอัตราและดึงซ้ำหุ้นที่ไม่ได้ราคาหนึ่งรอบ

## Impact

- **Code:** `engine/shortlist/sources/yahoo.py` (`YahooPrices.fetch_prices`), `engine/shortlist/config.py` และ `engine/config.yaml` (ส่วน `batch`), `engine/shortlist/batch.py` (ส่งค่าใหม่และ log), `engine/scripts/backtest_cdc.py` (constructor เดียวกัน) และ test
- **ผลต่อผู้ใช้:** batch ปกติช้าขึ้นราว 1–2 นาที แต่ได้ราคาครบขึ้นเมื่อ Yahoo จำกัดอัตรา ไม่เปลี่ยนวิธีประเมินหุ้น
- **ความสัมพันธ์กับ change อื่น:** ไม่บล็อกและไม่ถูกบล็อกโดย change ไหน แต่ถ้า apply ก่อน joint batch รอบใหม่ (C→A→B→D) run A และ B ใน worktree ที่ commit เก่าจะยังดึงราคาแบบเดิม จึงควร apply หลัง joint batch หรือรัน joint batch ทุกตัวนอกช่วงหลังตลาดปิด
