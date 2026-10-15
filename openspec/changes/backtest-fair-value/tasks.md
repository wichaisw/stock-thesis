# Tasks

## 1. Core (`engine/shortlist/backtest.py`)

- [x] 1.1 ฟังก์ชันตัดหุ้นที่ข้อมูลเพี้ยน (D3): มี `Stock Splits` ≠ 0 หรือส่วนผู้ถือหุ้นเปลี่ยนเกิน `structure_change_threshold` ระหว่างไตรมาสติดกันในช่วงทดสอบ คืนรายชื่อพร้อมเหตุผล พร้อม test ใน `tests/test_backtest.py` ตาม scenario "หุ้นที่เคย split" (รวมปันผลเป็นหุ้น ratio 1.1) และ "หุ้นที่ merge" (equity +173%) ตรวจด้วย `cd engine && uv run pytest tests/test_backtest.py`
- [x] 1.2 ฟังก์ชันตัดข้อมูล ณ วันที่ทดสอบ T (D2, ใช้ `catalyst.*_deadline_days`): งบตามกำหนดส่ง, caps ≤ ไตรมาสของ T, ราคา ≤ T พร้อม test scenario "งบที่ยังไม่ถึงกำหนดส่งไม่ถูกใช้" (T = 31 มี.ค. 2023 ใช้ถึง 2022Q4) และ "ราคาหลังวันที่ทดสอบไม่ถูกใช้ในการประเมิน" ตรวจด้วย `uv run pytest tests/test_backtest.py`
- [x] 1.3 ฟังก์ชันประเมินหนึ่งวันที่ทดสอบ: liquidity ณ T, peer PE จากหุ้นที่ผ่าน liquidity ณ T, เรียก `fair_value.evaluate` และ `quality.evaluate` (D1), ข้ามเมื่อ market cap ขาดกลาง lookback (D3) คืนแถวต่อหุ้นต่อ method (fair value, MoS, ผ่าน quality, candidate rule, ผิดปกติหรือไม่) พร้อม test scenario "หุ้นไม่ผ่าน liquidity ณ วันนั้น", "market cap ย้อนหลังขาด", "method คำนวณไม่ได้" และ "ค่าประเมินผิดปกติ" (ยังนับ) ตรวจด้วย `uv run pytest tests/test_backtest.py`
- [x] 1.4 ตัววัดที่ 63 วันทำการ: return จาก Adj Close, hit จาก High (D4), excess return ต่อวันที่ทดสอบแล้วสรุปข้ามวัน (D5), bucket MoS คงที่ (D9), placebo ที่สลับ MoS ด้วย seed คงที่ (D10) และไม่นับการประเมินที่ยังไม่ครบ 63 วัน พร้อม test ด้วยราคาสังเคราะห์ที่รู้คำตอบสำหรับ scenario hit rate, excess return, bucket และค่าอ้างอิงจากการสลับ MoS ตรวจด้วย `uv run pytest tests/test_backtest.py`
- [x] 1.5 poison check (D10): ประเมินซ้ำ 5 วันที่สุ่ม (seed คงที่) โดยแทนทุกแถวหลัง T ของราคา งบ และ caps ด้วยค่า ×1000 แล้ว raise พร้อมหุ้น วันที่ และ method ที่ต่าง พร้อม test 2 กรณี: ข้อมูลปกติผ่าน และฟังก์ชันตัดข้อมูลที่จงใจรั่ว (ไม่ตัดงบ) ทำให้ raise ตรวจด้วย `uv run pytest tests/test_backtest.py`
- [x] 1.6 สร้าง markdown ของผล (commit + ป้ายแก้ที่ยังไม่ commit, วันที่ของ cache, ช่วงวันที่, ค่าเกณฑ์, จำนวนหุ้น/การประเมิน, หุ้นที่ตัดพร้อมเหตุผลและ %, ผล poison check, ตารางผลพร้อมแถว placebo, ตารางค่าผิดปกติ, หุ้นที่ดึงไม่ได้, ข้อจำกัด) พร้อม test ว่ามีทุกส่วนตาม requirement "บันทึกผลเป็น markdown" ตรวจด้วย `uv run pytest` ทั้งชุดผ่าน

## 2. Skill

- [x] 2.1 script `.agents/skills/fair-value-backtest/backtest.py`: ดึงรายชื่อหุ้น (thaifin), ราคา 8 ปีด้วย `yf.download(auto_adjust=False, actions=True)`, งบและ market cap ของหุ้นที่เคยผ่าน liquidity ในช่วงทดสอบ, cache pickle ใน `engine/.cache/fv-backtest/` มี `--refresh` (D7), ข้ามหุ้นที่ดึงไม่ได้, รัน poison check ก่อนเขียน แล้วเขียน `docs/backtests/fair-value-<YYYY-MM-DD>.md` (ทับไฟล์ของวันเดียวกัน) และพิมพ์ตารางเดียวกันออกจอ เพิ่ม `engine/.cache/` ใน `.gitignore` ตรวจด้วยการรัน `uv run --project engine python .agents/skills/fair-value-backtest/backtest.py` สองครั้ง ครั้งที่สองใช้ cache และเร็วกว่ามาก
- [x] 2.2 `SKILL.md` ของ skill (เมื่อไหร่ใช้, ขั้นตอน, วิธีอ่านตัววัดแต่ละตัวรวม placebo, stop rule: poison check fail = หยุดแก้ bug ก่อน และผลไม่ใช่เหตุให้แก้เกณฑ์เองโดยไม่ถามผู้ใช้, ถ้าตัดหุ้นเกินราว 30% ให้บอกผู้ใช้ก่อนสรุป) ตามแบบ `stock-sanity-check`, symlink `.claude/skills/fair-value-backtest`, และเพิ่มหนึ่งบรรทัดใน `stock-sanity-check/SKILL.md` ให้รัน skill นี้หลังแก้ `core/fair_value` ตรวจด้วย `ls -l .claude/skills/fair-value-backtest` ชี้ถูก และ skill ขึ้นในรายการ skill ของ session ใหม่

## 3. Integration

- [x] 3.1 รัน backtest เต็มบนข้อมูลจริง ตรวจว่า poison check ผ่าน และ placebo excess ใกล้ 0 commit ไฟล์ผลรอบแรก แล้วเพิ่มสรุป (2–4 บรรทัด + ลิงก์ไฟล์ผล) ใต้ `## ผลตรวจข้อมูล` ใน `engine/README.md` ตรวจด้วยไฟล์ผลมีทุก method, จำนวนวันที่ทดสอบ 22 วัน (2021Q1–2026Q2) และ % หุ้นที่ตัด (ถ้าเกินราว 30% บอกผู้ใช้ก่อน commit)
- [x] 3.2 spot-check ด้วยมือ: PTT ณ 30 มิ.ย. 2023 คำนวณ PE TTM, PBV และ fair value ของ PE band จากงบ SET (Company Highlights) ที่ประกาศแล้ว ณ วันนั้น เทียบกับแถวใน backtest และตรวจว่า SCAP (par split 2022–2023) และ GULF (merger 2Q25) อยู่ในรายการหุ้นที่ตัด บันทึกผลในไฟล์ผล

## Workflow follow-up

- รัน backtest ซ้ำหลัง `add-fair-value-methods` 5.x และ `relax-quality-gate` 3.x เสร็จ แล้วเทียบกับไฟล์ผลรอบแรก
- archive เมื่อครบทุก task ไม่ต้องรอ change อื่น
