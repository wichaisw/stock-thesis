# Proposal

## Why

ผู้ใช้ต้องการให้ข้อมูลจาก yfinance มาก่อน thaifin ราคา จำนวนหุ้น และปันผลมาจาก yfinance อยู่แล้ว แต่กำไรสุทธิและส่วนผู้ถือหุ้นยังมาจาก thaifin ซึ่งตรวจแล้วมี field ที่ผิดความหมายหลายตัว (ROE annualize ไตรมาสเดียว, PE แบบสะสมตั้งแต่ต้นปี, `total_debt` คือหนี้สินรวม, `ebit_dattm` ว่าง) สองค่านี้เป็นฐานของ ROE TTM ที่ทั้ง quality gate และ Justified PBV ใช้ จึงควรมาจากแหล่งเดียวกับราคาและจำนวนหุ้นเมื่อมีข้อมูล

yfinance มีงบรายไตรมาสแค่ 5–6 ไตรมาสล่าสุด ไม่พอทำ band 5 ปี จึงใช้ yfinance เฉพาะไตรมาสที่มี และใช้ thaifin สำหรับไตรมาสที่เก่ากว่า

## What Changes

- กำไรสุทธิและส่วนผู้ถือหุ้น (ไม่รวมส่วนได้เสียที่ไม่มีอำนาจควบคุม) รายไตรมาส ใช้ค่าจาก yfinance ก่อน ถ้าไตรมาสนั้นไม่มีค่าจาก yfinance ใช้ค่าจาก thaifin
- ไม่ใช้งบจาก yfinance ของบริษัทที่รายงานงบเป็นสกุลเงินอื่นที่ไม่ใช่บาท (เช่น PTTEP รายงานเป็น USD) ใช้ thaifin ทั้งหมด
- ดึงงบจาก yfinance ไม่ได้ (error หรือข้อมูลว่าง) ไม่ทำให้หุ้น fail ใช้ thaifin ทั้งหมดแทน
- ก่อนเขียน code ต้อง cross-check `Stockholders Equity` และ `Net Income Common Stockholders` ของ yfinance กับงบบน SET ของชุดหุ้นที่ใช้ตรวจ ถ้าไม่ตรงในเกณฑ์ หยุดและให้ผู้ใช้ตัดสินใจ (ผล task 1.1: ใช้ `Net Income` แทน `Net Income Common Stockholders` ดู design D3)

ผลที่ตามมา: ROE TTM ของ quality gate และ Justified PBV, กำไร TTM ของ PE band, peer PE และ PE ปัจจุบัน คิดจากค่าใหม่ใน 4–6 ไตรมาสล่าสุด

นอกขอบเขต:
- EV/EBITDA band (ตัดออกใน `add-fair-value-methods` เพราะ thaifin ไม่มี EBITDA และ yfinance มีประวัติไม่พอทำ band)
- การเลิกใช้ thaifin สำหรับประวัติงบ 5 ปี, รายชื่อหุ้น และ sector
- field อื่นของ thaifin: EPS, กำไร YoY, D/E, OCF, NPM, BVPS (ยังใช้ thaifin)
- การแสดงแหล่งที่มาของแต่ละค่าในหน้าเว็บ

ความสัมพันธ์กับ change อื่น:
- ทำหลัง `add-fair-value-methods` (ใช้ ROE TTM ตัวเดียวกันกับ Justified PBV) code ไม่บล็อกกัน
- ผู้ใช้เลือก (15 ต.ค. 2026) ให้ change นี้มีผลกับ batch ของ `simplify-risk-reward` ข้อ 4.1 และ `add-fair-value-methods` ข้อ 5.1 ด้วย ไม่รัน batch แยกบน code ก่อน change นี้ ผลของเกณฑ์ใหม่กับผลของการเปลี่ยนแหล่งข้อมูลจึงปนกันใน batch เดียว
- ไม่บล็อกและไม่ถูกบล็อกโดย `simplify-risk-reward`, `investor-type-flow`, `flag-stale-price-bars`

## Capabilities

### New Capabilities
- (ไม่มี)

### Modified Capabilities
- `market-data`: เพิ่ม requirement ว่ากำไรสุทธิและส่วนผู้ถือหุ้นรายไตรมาสใช้ yfinance ก่อน thaifin พร้อมกรณีสกุลเงินและกรณีดึงไม่ได้

## Impact

- **engine**: `shortlist/sources/yahoo.py` (ดึงงบรายไตรมาสและแปลงเป็นรูปแบบกลาง), adapter ที่รวมสองแหล่ง, `shortlist/batch.py` (ใช้ adapter ที่รวมแล้ว), tests `test_sources.py`, `test_batch.py`
- **core**: ไม่แก้ (ยังรับ `QUARTERLY_COLUMNS` เดิม)
- **เวลา batch**: request เพิ่ม 2 ครั้งต่อหุ้นที่ผ่าน liquidity (ราว 170 ตัว) อาจเพิ่มเวลาและโอกาสโดน rate limit ของ Yahoo
- **ข้อมูล**: ผล cross-check บันทึกใน `engine/README.md` ตาราง `financials_quarterly` ไม่เปลี่ยนคอลัมน์
- **ผลต่อผู้ใช้**: ROE TTM และ fair value ของ PE, peer PE และ Justified PBV อาจเปลี่ยน candidate list อาจเปลี่ยนหลัง batch แรก
