# Proposal

## Why

Dividend yield band ใน fair value panel ใช้ `dividend_yield` ของ thaifin ซึ่งตรวจใน task 8.2 ของ `value-stock-shortlist` แล้วพบว่าใช้ไม่ได้ ทำให้ fair value สูงเกินจริง:

- **ปันผลเป็นหุ้น:** DITTO ปี 2022–2023 จ่ายปันผลเป็นหุ้นพร้อมเงินสดเล็กน้อย yield จึงเป็น 0.01–0.04% อยู่ 7 ไตรมาส median เหลือ 1.3% fair value ได้ 43.52 ทั้งที่ราคา 12.40 (DOHOME เป็นแบบนี้ทุกปี)
- **ความหมายของ field ไม่คงที่:** ก่อนปี 2025 ไตรมาสที่ไม่ได้จ่ายแสดง yield ราว 1% แทน yield 12 เดือน (PTT 2022Q3 1.0%, 2023Q3 0.99% ขณะที่ปีนั้นจ่ายจริงราว 6%) median จึงต่ำไปและ fair value สูงไป
- **ค่าขยะ:** AOT ปีที่ขาดทุนและไม่ได้จ่ายปันผล thaifin กลับมี yield 0.001%

หุ้นที่ผ่าน liquidity 58 จาก 167 ตัวมี yield ต่ำกว่า 0.1% อย่างน้อยหนึ่งไตรมาสในกรอบ 5 ปี ปัญหานี้จึงกระทบ candidate list ทั้งรายการ ไม่ใช่แค่ DITTO

## What Changes

- คำนวณ dividend yield 12 เดือนย้อนหลังของแต่ละไตรมาสเอง จากปันผลเงินสดของ yfinance ÷ ราคาปิดสิ้นไตรมาส ไม่ใช้ `dividend_yield` ของ thaifin อีก
- ปันผลเป็นหุ้นไม่นับเป็น yield เพราะเป็นการเพิ่มจำนวนหุ้น (yfinance บันทึกเป็น split และ market cap รองรับอยู่แล้ว)
- ไตรมาสที่ yield 12 เดือนต่ำกว่าเกณฑ์ (default 0.5% ปรับได้ใน config) ถือว่าไม่ได้จ่ายปันผลเงินสด และไม่นำไปคิด band
- fair value ของเกณฑ์นี้คือปันผลเงินสด 12 เดือนล่าสุดต่อหุ้น ÷ median ของ yield 12 เดือน
- ตรวจผลกับ dividend yield บน SET ก่อนใช้ และบันทึกผลใน `engine/README.md`

นอกขอบเขต:
- PE band (median − 1SD) ที่ติดลบมากในหุ้นที่ re-rate จริง เช่น DITTO PE ลดจาก 146 เหลือ 12 เป็นค่าที่ถูกต้องตามวิธีคำนวณ และมีป้ายโครงสร้างทุนเปลี่ยนอยู่แล้ว
- ปันผลพิเศษที่ทำให้ yield 12 เดือนสูงขึ้นชั่วคราว band ใช้ median ซึ่งรับค่าผิดปกติไม่กี่จุดได้
- การเปลี่ยนแหล่งงบการเงินอื่นจาก thaifin

## Capabilities

### New Capabilities
- (ไม่มี)

### Modified Capabilities
- `market-data`: เพิ่มการดึงปันผลเงินสดย้อนหลังและคำนวณ yield 12 เดือนรายไตรมาส
- `fair-value-panel`: dividend yield band ใช้ yield จากปันผลเงินสดที่คำนวณเอง และไม่นับไตรมาสที่ yield ต่ำกว่าเกณฑ์

## Impact

- **Code:** `engine/shortlist/sources/yahoo.py` (ใช้ข้อมูลจาก request ประวัติราคาเดิมของ market cap ไม่เพิ่ม request), `engine/shortlist/core/fair_value.py`, `engine/config.yaml` และ `config.py` (เกณฑ์ yield ขั้นต่ำ), test ที่เกี่ยวข้อง
- **ผลต่อผู้ใช้:** fair value ของ dividend yield band เปลี่ยนเกือบทุกหุ้นที่จ่ายปันผล หุ้นที่จ่ายปันผลเป็นหุ้นเป็นหลัก (เช่น DOHOME) จะเป็น N/A ลำดับใน candidate list อาจเปลี่ยนเพราะ MoS เปลี่ยน
- **ลำดับ:** ต้อง archive `value-stock-shortlist` ก่อน (ทุก task เสร็จแล้ว รอ commit) เพราะ spec `market-data` และ `fair-value-panel` ยังอยู่ใน change นั้น ยังไม่อยู่ใน `openspec/specs/` ไม่เกี่ยวกับ `filter-settings-page`
