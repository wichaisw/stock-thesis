# Tasks

ก่อนเริ่ม: commit `gate-on-proven-methods` ก่อน (แก้ไฟล์เดียวกัน) และเก็บ snapshot evaluation ของ run ล่าสุดไว้เทียบใน 3.1

## 1. Engine

- [x] 1.1 เพิ่ม `reported_quarters` ใน `shortlist/core/quality.py` ตาม D1–D3 และให้ `quality.evaluate` ใช้ พร้อมเหตุผลของ `min_quarters` ตาม D4 ตรวจด้วย `uv run pytest tests/test_quality.py` ที่ครอบทุก scenario ของ requirement "ไตรมาสล่าสุดที่งบยังไม่ครบ": EPS-only ไตรมาสสุดท้าย (ROE และไม่ขาดทุนคิดจาก 4 ไตรมาสก่อนหน้า, เหตุผลบอกไตรมาสที่ไม่นับ), EPS ≤ 0 ไม่ตัด, ไตรมาสก่อนหน้าไม่ครบไม่ตัด, ช่องว่างตรงกลางไม่ตัด และหุ้นงบครบได้ผลเหมือนเดิม
- [x] 1.2 ให้ `fair_value.evaluate` ใช้ `reported_quarters` ตรวจด้วย `uv run pytest tests/test_fair_value.py` ที่มี test ว่า EPS TTM, band และ Justified PBV ไม่ใช้ EPS ของไตรมาสที่ไม่นับ (ผลเท่ากับเมื่อไม่มีแถวนั้น)
- [x] 1.3 ให้ `backtest.excluded`, `backtest.cap_gap` และ `.agents/skills/stock-sanity-check/sanity.py` ใช้ `reported_quarters` ตรวจด้วย `uv run pytest` ทั้งชุดผ่าน แล้วรัน skill `fair-value-backtest` ด้วย cache เดิม ถ้าตัวเลขเปลี่ยนให้นับจำนวนการประเมินที่เปลี่ยนและบันทึกใน README (อย่าเขียนทับส่วน spot-check ของไฟล์ผล)

## 2. เอกสาร

- [x] 2.1 เพิ่มย่อหน้าใน `engine/README.md` ส่วนผลตรวจข้อมูล: thaifin มีไตรมาสที่มีแค่ EPS (หุ้นที่พบ, กฎที่ใช้) ตรวจด้วยการอ่านทวน

## 3. Integration

- [x] 3.1 รัน batch แล้วเทียบกับ snapshot: AEONTS, DIF, RBF, TURBO (หรือหุ้นที่มีไตรมาส EPS-only ใน run นั้น) ไม่ตกเพราะข้อมูลไม่ครบอีก และหุ้นอื่นผลไม่เปลี่ยน (นับ evaluation ที่ quality หรือ fair value ต่างจาก snapshot ต้องเป็นหุ้นกลุ่มนี้เท่านั้น) ตรวจด้วย skill `stock-sanity-check` ว่าธง "missing in" ของไตรมาสสุดท้ายหายไป
- [x] 3.2 spot-check อย่างน้อย 2 หุ้นในกลุ่มนี้: คำนวณ ROE TTM ด้วยมือจาก 4 ไตรมาสก่อนหน้าบนงบ SET ให้ตรงกับหน้ารายละเอียดภายใน 1% และหน้ารายละเอียดแสดงเหตุผลว่าไม่นับไตรมาสไหน บันทึกผลใน `engine/README.md`
