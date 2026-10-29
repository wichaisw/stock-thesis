# Tasks

## 1. Cross-check OCF ของ yfinance

- [ ] 1.1 รัน skill `data-crosscheck` ตาม D3: OCF ของ yfinance (`quarterly_cashflow` และ `cashflow`) เทียบกับงบบน SET สำหรับ PTT, CPALL, KBANK, SCAP, GULF และ BEM บันทึกตารางใน `engine/README.md` ส่วน `## ผลตรวจข้อมูล` ตรวจด้วยทุกตัวอยู่ใน tolerance 2% และผลรวมรายไตรมาสเท่ากับ FY ถ้าไม่ผ่าน หยุดและรายงานผู้ใช้ก่อนทำ 2.x

## 2. OCF จากแหล่งราคา

- [ ] 2.1 เพิ่ม `ocf` ใน `to_statements` / `fetch_statements` ของ `engine/shortlist/sources/yahoo.py` ตาม D1–D2 ตรวจด้วย test ใน `engine/tests/test_sources.py` ครบทุก scenario ใหม่ของ requirement (OCF จากแหล่งราคา, แหล่งราคาไม่มี OCF บางไตรมาส, ดึง cash flow ไม่ได้แต่กำไรยังมาจากแหล่งราคา, งบไม่ใช่สกุลบาท) และ `uv run pytest` ผ่านทั้งหมด
- [ ] 2.2 รัน batch แล้วเทียบกับ run ก่อน: จำนวนหุ้นที่ผ่านเกณฑ์ OCF, candidate ที่เข้าหรือออก และเวลาช่วงดึงงบ (หยุดดูก่อนถ้าจำนวนที่ผ่าน OCF เปลี่ยนเกิน 10% หรือเวลาเกินเพดาน) spot-check OCF ของ BEM และหุ้นที่ผล OCF เปลี่ยน 2 ตัวกับงบบน SET ตรวจด้วยตัวเลขตรงกับ SET ภายใน 2% บันทึกผลใน `engine/README.md`

## Workflow follow-up

- archive change นี้หลังผู้ใช้อ่านผล 2.2
