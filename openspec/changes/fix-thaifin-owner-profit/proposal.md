# Proposal

## Why

spot-check ของ `backtest-fair-value` (task 3.2) พบว่า `net_profit` ของ thaifin ไม่ตรงกำไรส่วนของบริษัทใหญ่บน SET ในงบเก่า (PTT FY2022 +28.5%, FY2023 +10.6%, FY2024–2025 ตรง) ขณะที่ EPS ตรง SET ทุกปี วัดทั้ง cache ของ backtest (551 หุ้น) พบว่า 255 หุ้นมีอย่างน้อยหนึ่งไตรมาสที่ `net_profit` ต่างจาก EPS × จำนวนหุ้นเกิน 10% (14–24% ของไตรมาสก่อนปี 2024, 5–8% ตั้งแต่ 2025) PE ทุกตัวของ engine ใช้ `net_profit` จึงเพี้ยน: PE ปัจจุบันของหุ้นที่มีส่วนได้เสียที่ไม่มีอำนาจควบคุมต่ำเกินจริง, fair value ของ `peer_pe` สูงเกินจริง และ PE band เพี้ยนเมื่อสัดส่วนที่ต่างเปลี่ยนไปตามเวลา

## What Changes

- PE ทุกจุดคิดต่อหุ้นจาก EPS: PE ปัจจุบัน = ราคา ÷ EPS 4 ไตรมาส, PE ย้อนหลังของแต่ละไตรมาส = ราคาปิด ณ สิ้นไตรมาส (ปรับ split แต่ไม่ปรับปันผล) ÷ EPS 4 ไตรมาส ณ ไตรมาสนั้น และ fair value ของ PE band และ `peer_pe` = PE ที่ได้ × EPS 4 ไตรมาสล่าสุด โดยไม่ใช้จำนวนหุ้น
- market cap รายไตรมาสเพิ่มราคาปิดสิ้นไตรมาสที่ปรับ split (ค่าที่ engine คำนวณอยู่แล้วตอนหา dividend yield ไม่ต้องดึงเพิ่ม)
- ตรวจ EPS ของ thaifin เทียบ SET ก่อนเปลี่ยน code (กฎของ project: ไม่เชื่อ field ใหม่จนกว่าจะเทียบแล้วบันทึกใน `engine/README.md`) ถ้า EPS ของหุ้นที่เคยแตกพาร์หรือจ่ายปันผลเป็นหุ้นไม่ถูกปรับย้อนหลังตาม split ให้หยุดและเปลี่ยนแผนเป็นการตัดไตรมาสที่ `net_profit` กับ EPS × จำนวนหุ้นต่างกันเกินเกณฑ์ออกจาก PE แทน
- **BREAKING** (พฤติกรรม): ยกเลิกข้อห้ามใช้ค่าต่อหุ้นจากแหล่งงบใน requirement "PE และ PBV ระดับบริษัท" สำหรับ PE (PBV ยังเป็นระดับบริษัทเหมือนเดิม) fair value และ candidate list เปลี่ยนหลัง batch แรก

นอกขอบเขต:
- ROE (quality gate และ Justified PBV), no-loss check และ net profit YoY ยังใช้ `net_profit` เดิม (ผู้ใช้เลือก)
- PBV band และ dividend yield band ไม่เปลี่ยน
- แก้ข้อมูล `net_profit` ที่แหล่ง หรือหาแหล่งกำไรส่วนของบริษัทใหญ่ย้อนหลังใหม่
- หุ้นที่รายงานงบเป็นสกุลเงินอื่น (เช่น BANPU) ไม่แก้แยก แต่ PE แบบต่อหุ้นใช้ EPS ที่เป็นบาท จึงได้ผลดีขึ้นเอง

## Capabilities

### New Capabilities

ไม่มี

### Modified Capabilities

- `fair-value-panel`: PE ย้อนหลัง, PE ปัจจุบันและ peer PE คิดต่อหุ้นจาก EPS แทนกำไรสุทธิ ÷ จำนวนหุ้น และเหตุผลของเกณฑ์ที่คำนวณไม่ได้เปลี่ยนจาก "กำไร 4 ไตรมาสติดลบ" เป็น EPS
- `market-data`: market cap รายไตรมาสมีราคาปิดสิ้นไตรมาสที่ปรับ split เพิ่ม

## Impact

- `engine/shortlist/core/fair_value.py` (`current_pe`, `evaluate`), `engine/shortlist/sources/yahoo.py` (`quarterly_market_cap`), `MARKET_CAP_COLUMNS`, test ที่เกี่ยวข้อง และ `engine/README.md` (ผลตรวจ EPS)
- backtest (`shortlist/backtest.py`) ใช้ `fair_value` ตรงๆ จึงได้ผลใหม่เอง แต่ cache ใน `engine/.cache/fv-backtest/` ไม่มีคอลัมน์ใหม่ ต้องรันด้วย `--refresh`
- `prefer-yfinance-statements` แทน `net_profit` ไตรมาสล่าสุดด้วย Net Income ของ yfinance หลัง change นี้ค่านั้นมีผลแค่ ROE ไม่มีผลต่อ PE อีก
- ลำดับ: change นี้ไม่บล็อก change อื่น แต่ควร apply หลัง batch ร่วมของ `simplify-risk-reward` 4.1, `add-fair-value-methods` 5.x และ `prefer-yfinance-statements` 3.x เพราะ batch นั้นเทียบผลกับ code ก่อนหน้า ถ้าเปลี่ยน PE ก่อน ผลเทียบจะปนกันสองเรื่อง
- ไม่มี DB migration: market cap ไม่ได้เก็บใน DB
