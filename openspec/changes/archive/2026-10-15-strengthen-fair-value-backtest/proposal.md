# Proposal

## Why

ผล backtest 15 ต.ค. 2026 (`docs/backtests/fair-value-2026-10-15.md`) ยังตัดสินไม่ได้ว่า fair value ใช้ได้จริง: candidate มี excess เฉลี่ย +0.5% และบวก 13 จาก 22 วันที่ (p ≈ 0.26 ใกล้การโยนเหรียญ) MoS ที่สูงขึ้นไม่ได้ให้ผลดีขึ้น (bucket ≥ 30% แย่พอกับ 10–30%) และสัดส่วน candidate ต่อหุ้นที่ประเมินได้ไหลจาก 6% (2021Q1) เป็น 52% (2025Q1) เพราะ band อิงอดีตยังจำ regime เก่าตอนตลาดปรับลงทั้งตลาด ไฟล์ผลตอนนี้ไม่มีความไม่แน่นอนทางสถิติ ค่าผิดปกติ 3537 ค่าปนอยู่ในทุกตัววัด และวัดแค่ 63 วัน ถ้าเลือก method หรือเปลี่ยน gate จากผลชุดนี้ตรงๆ เสี่ยง overfit กับ 22 วันที่ จึงต้องทำให้ backtest ตัดสินได้ก่อนเปลี่ยน model

## What Changes

- ตารางผลรวมเพิ่ม t-stat และช่วงความเชื่อมั่น 95% ของ excess เฉลี่ย ต่อ method, median และ candidate คิดจาก excess ต่อวันที่ (ไม่ใช่ต่อการประเมิน เพราะการประเมินของหุ้นตัวเดียวกันในวันที่ติดกันไม่เป็นอิสระ)
- เพิ่มแถวผลรวมแบบ "ไม่นับค่าผิดปกติ" (MoS < −100% หรือ fair value > 5× ราคา) ข้างแถวเดิม แถวเดิมยังนับค่าผิดปกติตาม requirement เดิม
- วัดผลเพิ่มที่ 126 และ 252 วันทำการ เป็นตัววัดประกอบ 63 วันยังเป็นตัววัดหลักตาม thesis ถือราว 1 ไตรมาส ตัววัดยาวใช้ดูว่า MoS ที่สูงผิดพลาด หรือแค่ใช้เวลานานกว่า 1 ไตรมาส
- เพิ่มกลุ่ม "candidate (relative)": ผ่าน quality gate และ median MoS อยู่ใน 20% บนของหุ้นที่ประเมินได้ในวันเดียวกัน วัดเทียบกับ candidate rule เดิม พร้อมแถวสลับ MoS เหมือนกลุ่มอื่น
- ตารางต่อวันที่เพิ่มสัดส่วน candidate ต่อหุ้นที่ประเมินได้ ของทั้งสองกลุ่ม

นอกขอบเขต:
- การเปลี่ยน candidate gate, `candidates.min_median_mos` หรือ method ที่ใช้ใน batch และหน้า candidate list (ตัดสินหลังเห็นผลของ change นี้ แยกเป็น change ใหม่)
- การตัดหรือลดน้ำหนัก `pbv_median` หรือ method ใดออกจาก panel
- การแก้ `net_profit` ของ thaifin ในงบเก่า (ข้อจำกัดที่รู้แล้วจาก `fix-thaifin-owner-profit`)
- การใช้งบ yfinance ใน backtest, การจำลองการเทรด ค่าธรรมเนียม stop หรือ CDC
- การแก้ survivorship bias หรือการคืนหุ้นที่ถูกตัด (split, ส่วนผู้ถือหุ้นเปลี่ยน) กลับเข้ามา
- การปรับเกณฑ์ 20% ของ relative gate เป็นค่าใน config (ใช้ค่าคงที่ใน backtest ก่อน)

ความสัมพันธ์กับ change อื่น:
- ไม่บล็อกและไม่ถูกบล็อกโดยงานที่ค้างของ `add-fair-value-methods`, `prefer-yfinance-statements`, `relax-quality-gate` หรือ `simplify-risk-reward` ในแง่ code (แก้เฉพาะ backtest)
- batch รวมที่ค้างอยู่ไม่กระทบ backtest เพราะ backtest ใช้งบ thaifin อย่างเดียวและอ่าน `engine/config.yaml` ไม่ใช่ค่าที่บันทึกบนเว็บ รอบ 2026-10-15 รันบน code ที่มี gate หลวมของ `relax-quality-gate` แล้ว (`max_failed_checks: 2` ใน `config.yaml`) ถ้า cache และ `config.yaml` เหมือนเดิม แถว 63 วันเดิมต้องได้ค่าเท่าเดิม

## Capabilities

### New Capabilities

ไม่มี

### Modified Capabilities

- `fair-value-backtest`: requirement วัดผลเพิ่ม horizon 126/252 วัน, t-stat และช่วงความเชื่อมั่นต่อวันที่, แถวไม่นับค่าผิดปกติ และกลุ่ม candidate (relative) requirement ไฟล์ผลเพิ่มสัดส่วน candidate ต่อวันที่

## Impact

- `engine/shortlist/backtest.py` และ `engine/tests/test_backtest.py`
- `.agents/skills/fair-value-backtest/` (script ที่เขียนไฟล์ผล และตาราง "Reading the result" ใน SKILL.md)
- ไฟล์ผลใหม่ใน `docs/backtests/` (cache เดิมใช้ต่อได้ แต่ 252 วันทำให้วันที่ทดสอบช่วงท้ายวัดไม่ครบมากขึ้น)
- ไม่มีผลต่อ batch, `shortlist.db`, candidate list หรือ UI
