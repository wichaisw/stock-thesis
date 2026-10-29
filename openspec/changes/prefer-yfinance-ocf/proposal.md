# Proposal

## Why

ผลตรวจ OCF ของ BEM (engine/README.md, 29 ต.ค. 2026) พบว่า OCF รายไตรมาสของ thaifin ต่างจากงบเกิน 2% ใน 3 จาก 6 ไตรมาส (2025Q4 +15%, 2026Q1 +7%, 2026Q2 +11%) ส่วน yfinance ตรงกับ company snapshot (2026Q1 −5,951 ลบ.) และผลรวมรายไตรมาสเท่ากับ FY2025 (−11,090 ลบ.) quality gate อ่าน OCF 4 ไตรมาสล่าสุด ถ้าค่าเพี้ยนเปลี่ยนเครื่องหมาย หุ้นจะผ่านหรือตกเกณฑ์ OCF ผิดได้

## What Changes

- OCF รายไตรมาสใช้ค่าจาก yfinance ก่อน แล้วใช้ thaifin เฉพาะไตรมาสที่ yfinance ไม่มีค่า วิธีเดียวกับกำไรสุทธิและส่วนผู้ถือหุ้นที่ทำอยู่แล้ว
- ก่อนใช้จริง ต้อง cross-check OCF ของ yfinance กับ SET สำหรับชุดหุ้นคงที่และ BEM แล้วบันทึกผลใน `engine/README.md` ถ้าเกิน tolerance ให้หยุดและรายงานก่อน
- ถ้าดึง cash flow จาก yfinance ไม่ได้ ใช้ thaifin ทั้งหมดเหมือนเดิม และไม่นับเป็นหุ้นที่ fail

## Capabilities

### New Capabilities

ไม่มี

### Modified Capabilities

- `market-data`: requirement "กำไรสุทธิและส่วนผู้ถือหุ้นจากแหล่งราคาก่อน" ครอบคลุม OCF ด้วย

## Impact

- `engine/shortlist/sources/yahoo.py`: `to_statements` / `fetch_statements` อ่าน `quarterly_cashflow` ด้วย
- `engine/tests/test_sources.py`: test ของ OCF จากแหล่งราคา
- `engine/README.md`: ผล cross-check และผล batch
- การประเมินหุ้นเปลี่ยน: เกณฑ์ OCF ของ quality gate อาจให้ผลต่างจากเดิมในหุ้นที่ thaifin เพี้ยน ซึ่งทำให้ candidate list เปลี่ยนได้
- batch เรียก yfinance เพิ่มหนึ่ง request ต่อหุ้น

## Out of scope

- แก้เกณฑ์ OCF สำหรับหุ้นสัมปทาน (TFRIC 12) OCF ติดลบของ BEM เป็นตัวเลขจริงในงบ
- backtest ยังใช้งบ thaifin อย่างเดียว (ข้อจำกัดเดิมใน `LIMITATIONS`)
- field อื่นของงบ (D/E, EPS, dividend yield)

## Dependencies

ไม่ block และไม่ถูก block โดย `backtest-ex-banking-variant` (task ครบ ยังไม่ archive) หรือ `flag-abnormal-fair-value` (ยังไม่เริ่ม) เพราะไม่แตะไฟล์เดียวกัน
