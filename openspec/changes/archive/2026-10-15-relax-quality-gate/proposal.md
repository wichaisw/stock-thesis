# Proposal

## Why

Quality gate ตอนนี้ต้องผ่านทุกเกณฑ์ หุ้นที่พื้นฐานดีแต่ตกเกณฑ์เดียว (เช่น D/E 1.6 หรือ OCF บวก 2/4) จึงหลุดจาก candidate list ทั้งที่ MoS และ CDC timing ดี ผู้ใช้อยากให้ gate หลวมลง (ราว 4 ใน 6) และเห็นในตารางว่าแต่ละตัวผ่านกี่เกณฑ์ เพื่อตัดสินใจเอง

## What Changes

- Liquidity และจำนวนไตรมาสขั้นต่ำยังเป็นเกณฑ์บังคับ (ไม่ผ่านคือไม่ผ่าน quality gate) เพราะถ้าไม่ผ่าน engine ไม่ดึงงบหรือไม่คำนวณเกณฑ์อื่น
- ROE, D/E, OCF และไม่ขาดทุน ไม่ผ่านได้รวมไม่เกิน `quality.max_failed_checks` เกณฑ์ (default 2 จึงเท่ากับผ่าน 4 ใน 6 สำหรับหุ้นทั่วไป) เกณฑ์ที่ข้าม (D/E, OCF ของหุ้นการเงิน) ไม่นับเป็นไม่ผ่าน
- `max_failed_checks` แก้ได้บนหน้า settings หมวด quality gate พร้อม tooltip
- หน้า candidate list เพิ่มคอลัมน์ "Gates" แสดง ผ่าน/ที่ประเมิน (เช่น 5/6, หุ้นธนาคาร 4/4) และ tooltip บอกเกณฑ์ที่ไม่ผ่านพร้อมค่าจริง
- หน้ารายละเอียดแสดงจำนวนเดียวกันที่หัวข้อ Gates
- การเรียงลำดับไม่เปลี่ยน (CDC → ETA → MoS) จำนวน gate ใช้แสดงผลเท่านั้น ไม่ใช่ weighted score
- **BREAKING (ผลลัพธ์)**: จำนวน candidates จะเพิ่มขึ้นเมื่อรัน batch ครั้งถัดไป ตั้ง `max_failed_checks: 0` เพื่อกลับไปเป็นแบบเดิม

## Out of scope

- Gate ใหม่ (เช่น ป้าย C/SP ของ SET, interest coverage, EPS TTM ไม่ลดลง YoY) แยกเป็น change ของตัวเองหากต้องการ
- การใช้จำนวน gate ช่วยเรียงลำดับหรือให้น้ำหนัก
- เปลี่ยนค่าเกณฑ์เดิม (ROE 10%, D/E 1.5, ...)
- ส่วน Gates ใน LLM export ยังแสดงผลแต่ละเกณฑ์เหมือนเดิม (ค่า "Quality gate: pass/fail" ใช้ผลใหม่อัตโนมัติ)

## Dependencies with other changes

- ไม่ block และไม่ถูก block ด้วยงานที่ค้างของ change อื่นในแง่โค้ด
- batch รวมที่ค้างอยู่ (`simplify-risk-reward` 4.1, `add-fair-value-methods` 5.x, `prefer-yfinance-statements` 3.x) เทียบ candidate list ก่อน/หลัง ถ้า change นี้ลงก่อน จำนวน candidates จะเปลี่ยนจากเหตุนี้ด้วยและอธิบายยาก จึงควร implement change นี้หลัง batch รวมนั้นรันเสร็จ หรือตั้ง `max_failed_checks: 0` ตอนรัน batch รวม
- `flag-stale-price-bars` 2.1 แก้คอลัมน์ป้ายใน `web/app/page.tsx` เหมือนกัน ไม่ขัดกัน แค่ต้อง merge

## Capabilities

### New Capabilities

(ไม่มี)

### Modified Capabilities

- `quality-gate`: เกณฑ์พื้นฐานไม่ต้องผ่านครบทุกข้อ ไม่ผ่านได้ไม่เกินค่าใน config ส่วน liquidity และจำนวนไตรมาสยังบังคับ
- `candidate-list`: ตารางมีคอลัมน์จำนวน gate ที่ผ่าน และหน้ารายละเอียดแสดงจำนวนเดียวกัน
- `filter-settings`: หมวด quality gate มีช่อง "จำนวนเกณฑ์ที่ไม่ผ่านได้สูงสุด"

## Impact

- Engine: `shortlist/core/quality.py`, `shortlist/config.py`, `config.yaml`, `tests/test_quality.py`, `tests/test_config.py`
- Web: `app/page.tsx`, `app/stocks/[symbol]/page.tsx`, `lib/` (ฟังก์ชันนับ gate ใช้ร่วมกัน), `app/settings` (ถ้าไม่ render จาก metadata อัตโนมัติ)
- Docs: `docs/batch-flow.md` (กล่อง Quality gate), `README.md` ถ้าพูดถึงว่าต้องผ่านทุกเกณฑ์
- ไม่เปลี่ยน DB schema และ API (run เก่ายังแสดงจำนวน gate ได้จาก checks ที่เก็บไว้)
