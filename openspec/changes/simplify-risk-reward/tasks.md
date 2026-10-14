# Tasks

## 1. Engine: ลบ reward ต่อเดือน

- [x] 1.1 ลบ `hold_months`, `reward_per_month` และ parameter `today`/`next_deadline` ออกจาก `shortlist/core/risk_reward.py` (D2) แล้วลบ test reward ต่อเดือนใน `tests/test_risk_reward.py` และแก้การเรียกที่เหลือ ตรวจด้วย `uv run pytest tests/test_risk_reward.py`
- [x] 1.2 ลบ `min_hold_months`, `max_hold_months` และ validator ออกจาก `RiskReward` ใน `shortlist/config.py` และ `config.yaml` แล้วลบ `test_max_hold_cannot_be_below_min_hold` ตรวจด้วย `uv run pytest tests/test_config.py`
- [x] 1.3 เลิกคำนวณ/ส่ง `next_deadline` ใน `shortlist/batch.py`, ลบ `catalyst.next_statement_deadline` และ test ของมัน, แก้ assert `hold_months` ใน `tests/test_batch.py` ตรวจด้วย `uv run pytest` ทั้งชุดผ่าน และ `rg "reward_per_month|hold_months|next_statement_deadline" engine` ไม่เจอใน code
- [x] 1.4 ลบ parameter `today` ที่ไม่มีผู้ใช้แล้วออกจาก `batch.run`/`execute`/`collect` (D2) และเลิกส่ง `today()` ให้ `batch.execute` ใน `shortlist/api.py` (ยังส่งให้ event calendar) แก้การเรียกใน `tests/test_batch.py` ตรวจด้วย `uv run pytest` ทั้งชุดผ่าน และ `rg -n "today" engine/shortlist/batch.py` ไม่เจอ

## 2. Engine: ป้าย upside สูงผิดปกติ

- [x] 2.1 เพิ่ม `max_upside` (editable, percent, default 1.0) ใน `RiskReward` และ `config.yaml` และ `high_upside` ในผลของ `risk_reward.evaluate` (`false` เมื่อไม่มี upside) พร้อม test ตาม 3 scenario ของ requirement "ป้ายเตือน upside สูงผิดปกติ" ตรวจด้วย `uv run pytest tests/test_risk_reward.py tests/test_config.py`

## 3. Web

- [x] 3.1 ลบ `hold_months`/`reward_per_month` และเพิ่ม `high_upside?: boolean` ใน `web/lib/engine.ts` (D4) แล้วลบคอลัมน์ reward ต่อเดือนใน `app/page.tsx` และแถว ระยะถือที่คาด/Reward ต่อเดือน ใน `app/stocks/[symbol]/page.tsx` ตรวจด้วย `bun run lint`
- [x] 3.2 เพิ่ม Tag "upside สูงผิดปกติ" ข้างป้าย RRR ต่ำ ทั้งใน candidate list และหน้ารายละเอียด ตรวจด้วย `bun run lint` และเปิด browser ดูว่า run เก่า (ไม่มี field) ไม่พัง
- [x] 3.3 ใน `lib/llm-export.ts` ลบบรรทัด holding period/reward per month และต่อท้าย RRR หรือ Upside ด้วย "(unusually high upside)" เมื่อ `high_upside` แก้ `llm-export.test.ts` ตาม ตรวจด้วย `bun test lib/llm-export.test.ts` และ `bun run lint`

## 4. Integration

- [ ] 4.1 รัน batch ใหม่ ตรวจว่า EA, TPCH, SRICHA ติดป้าย upside สูงผิดปกติ, NSL (upside ~49%) ไม่ติด, จำนวน candidates เท่าเดิมเมื่อข้อมูลเท่าเดิม (batch นี้รวม Justified PBV ของ `add-fair-value-methods` และงบจาก yfinance ของ `prefer-yfinance-statements` แล้วตามที่ผู้ใช้เลือก 15 ต.ค. 2026 จำนวน candidates จึงอาจเปลี่ยนจากสองเหตุนั้น ให้อธิบายหุ้นที่เข้าหรือหลุดแทน) และ entry/target ของหุ้นที่ spot-check ตรงกับราคาปิดบน SET/TradingView
- [x] 4.2 เปิดหน้า settings ใน browser ตรวจว่าไม่มีช่องระยะถือ มีช่อง upside สูงสุด และบันทึกค่าได้

## Workflow follow-up

- ตอน archive แก้ Purpose ของ `openspec/specs/risk-reward/spec.md` ให้ไม่พูดถึง reward ต่อเดือน
