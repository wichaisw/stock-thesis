# Tasks

## 1. ความไม่แน่นอนของ excess (D1)

- [x] 1.1 `excess()` ใน `engine/shortlist/backtest.py` คืน t-stat และ CI 95% แบบ bootstrap ข้ามวันที่ (2,000 รอบ seed คงที่) และคืน None เมื่อมีน้อยกว่า 2 วันที่ ตรวจด้วย test ใหม่ใน `engine/tests/test_backtest.py`: excess ต่อวันที่ที่รู้ค่าให้ t ตรงสูตร, CI คร่อมค่าเฉลี่ย, รันสองครั้งได้ค่าเท่ากัน, วันที่เดียวได้ None แล้ว `uv run pytest` ผ่าน
- [x] 1.2 ตารางผลรวมใน `report()` เพิ่มคอลัมน์ "95% CI" และ "t" (แถวสลับ MoS เป็นช่องว่าง, None เป็น "–") ตรวจด้วย `test_report_has_every_section` ที่เพิ่ม assert หัวคอลัมน์ แล้ว `uv run pytest` ผ่าน

## 2. ผลรวมแบบไม่นับค่าผิดปกติ (D3)

- [x] 2.1 `metrics()` คิดตัววัดชุดที่สองจากแถวที่ไม่ `abnormal` โดย baseline คิดจากแถว median ทุกแถว ตรวจด้วย test ใหม่: แถว fair value > 5× ราคาถูกนับในชุดเดิม ไม่ถูกนับในชุดใหม่ และ baseline สองชุดเท่ากัน แล้ว `uv run pytest` ผ่าน
- [x] 2.2 `report()` เพิ่มส่วน "ผลรวมแบบไม่นับค่าผิดปกติ" คอลัมน์เดียวกับตารางผลรวม ตรวจด้วย assert หัวส่วนใน test รายงาน แล้ว `uv run pytest` ผ่าน

## 3. ระยะวัดผล 126 และ 252 วัน (D2)

- [x] 3.1 `with_outcomes()` เติม `ret_126` และ `ret_252` ข้าง `ret` เดิม และเป็น None เมื่อยังไม่ครบระยะ ตรวจด้วย test แบบ `test_outcome_reads_63_trading_days_after_t` ที่ 126 วัน และกรณีราคายังไม่ครบ 252 วัน แล้ว `uv run pytest` ผ่าน
- [x] 3.2 `metrics()` คิด excess (mean, CI, t, วันที่) ต่อกลุ่มต่อระยะ โดย baseline คิดใหม่ต่อระยะ และ bucket มี median excess ที่ 126/252 วัน hit ยังคิดที่ 63 วัน ตรวจด้วย test ใหม่: วันที่ที่ไม่ครบ 252 วันไม่นับที่ 252 แต่นับที่ 63 แล้ว `uv run pytest` ผ่าน
- [x] 3.3 `report()` เพิ่มส่วน "ต่อระยะวัดผล", คอลัมน์ bucket 126/252 และข้อจำกัดเรื่องช่วงวัดผลซ้อนกันและการเทียบหลายกลุ่มหลายระยะ ใน `LIMITATIONS` ตรวจด้วย assert ใน test รายงาน แล้ว `uv run pytest` ผ่าน

## 4. candidate (relative) (D4)

- [x] 4.1 `evaluate_date()` หรือ `groups()` ตั้ง flag candidate (relative): rank percentile ของ median MoS ในหุ้นที่มี median MoS ณ วันนั้น อยู่ใน 20% บน (`RELATIVE_TOP = 0.20`) และผ่าน quality gate ตรวจด้วย test ใหม่: 10 หุ้นที่ median MoS ต่างกัน 2 ตัวบนที่ผ่าน quality ถูกเลือกแม้ MoS ติดลบ ตัวที่ไม่ผ่าน quality ไม่ถูกเลือก แล้ว `uv run pytest` ผ่าน
- [x] 4.2 กลุ่ม relative มีแถวในตารางผลรวม (พร้อมสลับ MoS), ตารางไม่นับค่าผิดปกติ และตารางต่อระยะ และตารางต่อวันที่เพิ่มคอลัมน์ candidate % และ relative (จำนวน, %) ตรวจด้วย assert ใน test รายงาน แล้ว `uv run pytest` ผ่าน
- [x] 4.3 ตาราง "Reading the result" ใน `.agents/skills/fair-value-backtest/SKILL.md` เพิ่มแถว 95% CI/t, candidate (relative), ต่อระยะวัดผล และไม่นับค่าผิดปกติ พร้อมคำเตือนว่า CI ที่ไม่คร่อม 0 ราว 2 ใน 48 เกิดได้โดยบังเอิญ ตรวจโดยอ่านทวนว่าทุกส่วนใหม่ในไฟล์ผลมีแถวอธิบาย

## 5. รันจริงและเทียบกับรอบเดิม

- [x] 5.1 รัน `uv run --project engine python .agents/skills/fair-value-backtest/backtest.py` บน cache เดิม ตรวจว่าทุกค่าในตารางผลรวมเดิม (คอลัมน์เดิม), bucket (คอลัมน์ 63 วัน) และต่อวันที่ (คอลัมน์เดิม) เท่ากับ `git show HEAD:docs/backtests/fair-value-2026-10-15.md` ทุกตัว ถ้าไม่เท่าให้หยุดหาสาเหตุก่อน
- [x] 5.2 ถ้าไฟล์ผลใหม่เขียนทับ `fair-value-2026-10-15.md` คัดส่วน "Spot-check ด้วยมือ" จากไฟล์ใน git กลับมาต่อท้าย ตรวจด้วย `git diff` ว่าส่วนนั้นไม่หาย
- [x] 5.3 สรุปผลใหม่ใน `engine/README.md` ใต้หัวข้อ fair value backtest: ต่อกลุ่ม excess เฉลี่ย, CI, t ที่ 63 วัน, ผลของ candidate (relative) เทียบ candidate เดิม และ bucket ที่ 252 วัน แล้วรายงานผู้ใช้ ห้ามเปลี่ยน gate หรือ method จากผลนี้ใน change นี้ (ตาม stop rules ของ skill) ตรวจด้วยการอ่านทวนว่าตัวเลขใน README ตรงไฟล์ผล
