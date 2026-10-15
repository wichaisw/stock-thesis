# Tasks

## 1. ตรวจ EPS ก่อนแก้ code (D3)

- [ ] 1.1 เทียบ EPS รายปี FY2022–FY2025 (ผลรวม 4 ไตรมาสของ thaifin) กับ Company Highlights ของ SET (in-page fetch ใน Orca ตาม skill `data-crosscheck`) สำหรับ PTT, COM7, HTC, SAWAD, BANPU, CHO, TOP, CPF, CPALL, KBANK ผ่านเมื่อต่างไม่เกิน 0.01 บาทต่อไตรมาส หรือต่างเท่ากับ factor ของ split ที่เกิดหลังงวดนั้นพอดี ตรวจด้วยตารางผลต่อหุ้นต่อปี
- [ ] 1.2 ตรวจทั้งตลาดจาก `engine/.cache/fv-backtest/`: ทุกหุ้นที่ yfinance มี split ไตรมาสก่อน split มี `net_profit` ÷ (EPS × จำนวนหุ้น) ≈ factor ของ split ที่เกิดหลังไตรมาสนั้น (±10%) นับหุ้นและไตรมาสที่ไม่เข้าแบบนี้ ตรวจด้วยรายชื่อที่ไม่ผ่าน (ดู HTC 2019Q1 เป็นพิเศษ)
- [ ] 1.3 บันทึกผล 1.1–1.2 ใต้ `## ผลตรวจข้อมูล` ใน `engine/README.md` ถ้ามีหุ้นที่ EPS ไม่ถูกปรับตาม split หยุดและถามผู้ใช้ว่าจะใช้แผนสำรองของ D1 หรือแก้เฉพาะหุ้นเหล่านั้น ก่อนทำกลุ่ม 2 ตรวจด้วย README มีตารางและข้อสรุป

## 2. Engine

- [ ] 2.1 `quarterly_market_cap` คืนคอลัมน์ `close` (ราคาปิดสิ้นไตรมาสที่ปรับ split ไม่ปรับปันผล) และเพิ่มใน `MARKET_CAP_COLUMNS` (D2) พร้อม test scenario "หุ้นแตกพาร์" (ได้ 5.35 คู่กับราคาจริง 26.75) และ "ไม่มีจำนวนหุ้นย้อนหลัง" (ไม่มี market cap แต่มี `close`) ตรวจด้วย `cd engine && uv run pytest`
- [ ] 2.2 `fair_value.current_pe` = ราคา ÷ `eps_ttm` และ `evaluate`: PE ย้อนหลัง = `close` ÷ EPS 4 ไตรมาส บนไตรมาสที่มี market cap, fair value ของ PE band และ peer PE = PE × `eps_ttm` ไม่ใช้จำนวนหุ้น, เหตุผล N/A ตาม D4 (PBV และ Justified PBV ไม่เปลี่ยน) พร้อม test scenario "กำไรสุทธิของแหล่งงบรวมส่วนของผู้ถือหุ้นส่วนน้อย" (PE 10.18), "หุ้นแตกพาร์" (EPS และราคาปรับ split แล้ว PE ไม่เปลี่ยน), "หุ้นเพิ่มทุน", "PE ย้อนหลังมีค่าผิดปกติ" และ "กำไร 4 ไตรมาสติดลบ" (EPS ≤ 0) ตรวจด้วย `uv run pytest` ทั้งชุดผ่าน
- [ ] 2.3 ถ้า test ของ `backtest.py` หรือ `tests/fakes.py` (`market_caps`) ต้องมี `close` เพิ่ม ให้แก้ fake ให้คิดเหมือน adapter ตรวจด้วย `uv run pytest tests/test_backtest.py`

## 3. ตรวจบนข้อมูลจริง (D5)

- [ ] 3.1 รัน `fair-value-backtest` ด้วย `--refresh` เทียบกับ `docs/backtests/fair-value-2026-10-15.md`: poison check ผ่าน, placebo ใกล้ 0, จำนวนค่าผิดปกติไม่เพิ่ม และสรุปความต่างของ peer_pe และ PE band ใน `engine/README.md` ตรวจด้วยไฟล์ผลใหม่ใน `docs/backtests/`
- [ ] 3.2 snapshot candidate list แล้วรัน batch และ skill `stock-sanity-check` ตรวจว่าไม่มี fair value > 5× ราคาเพิ่มขึ้นจาก PE band หรือ peer PE จากนั้น spot-check PE ปัจจุบันของ PTT, COM7, SAWAD เทียบ P/E บน SET (ต่างได้เพราะ SET จับคู่ราคากับงบที่ประกาศล่าสุด ให้เทียบ input คือ EPS 4 ไตรมาส) บันทึกผลและหุ้นที่เข้า/ออก candidate list ใน `engine/README.md`

## Workflow follow-up

- apply หลัง batch ร่วมของ `simplify-risk-reward` 4.1, `add-fair-value-methods` 5.x และ `prefer-yfinance-statements` 3.x
