# Proposal

## Why

gate ด้าน fair value ใช้ Peer PE และ Justified PBV ตายตัว (`candidates.gate_methods`) ผู้ใช้อยากเห็นว่าถ้าไม่ใช้ gate ตัวใดตัวหนึ่ง หรือไม่ใช้ทั้งคู่ candidate list จะเป็นอย่างไร เช่น หุ้นที่ Peer PE ไม่เข้ากับธุรกิจ (BEM: peer ใน sector เป็นเรือและสายการบิน) ตอนนี้ต้องแก้ config แล้วรัน batch ใหม่ทั้งตลาดเพื่อดูผล ทั้งที่ batch เก็บ MoS ของทุกเกณฑ์ของทุกหุ้นไว้แล้ว

## What Changes

- หน้า candidates มี checkbox เปิด/ปิด gate Peer PE และ Justified PBV ค่าเริ่มต้นตาม `candidates.gate_methods` และเก็บใน URL (เช่น `/?gates=justified_pbv`, `/?gates=` = ปิดทั้งหมด)
- `GET /candidates` รับ `gates` แล้วคำนวณ gate, เงื่อนไขการเข้า list, ลำดับ, target และ RRR ใหม่จากผลการประเมินที่ run ล่าสุดเก็บไว้ ไม่ดึงข้อมูลใหม่และไม่เขียน DB
- ปิด gate ทั้งหมดได้: list เหลือเงื่อนไข liquidity, quality และ CDC state เรียงด้วย just-crossed แล้ว ETA และ target ใช้ median fair value ของ panel แทน
- ไม่ส่ง `gates` หรือส่งค่าเท่ากับ config = ผลเหมือน batch ทุกประการ

## Out of scope

- batch, `engine/config.yaml`, หน้า settings และ `candidates.gate_methods` ไม่เปลี่ยน ค่า toggle ไม่ถูกบันทึก
- candidate history (snapshot รายวัน), หน้ารายละเอียดหุ้น, LLM export และ verdict ของหุ้นที่ถือยังใช้ gate ของ batch
- เลือกเกณฑ์อื่นใน panel (PE band, PBV band, dividend yield band) เป็น gate ไม่ได้ เพราะไม่เคย backtest เป็น gate
- เกณฑ์ที่ปิดใน `fair_value.enabled` ไม่ถูกคำนวณใน batch จึงเปิดเป็น gate จากหน้านี้ไม่ได้
- backtest ของ gate แบบอื่น

## Blocking

ไม่ block และไม่ถูก block โดย `flag-abnormal-fair-value` (แก้ป้ายในหน้ารายละเอียด) หรือ `prefer-yfinance-ocf` (แก้แหล่ง OCF ใน engine) ทั้งสอง change แตะไฟล์คนละส่วน ยกเว้น `web/lib/gates.ts` ที่ `flag-abnormal-fair-value` เพิ่มฟังก์ชัน ซึ่ง merge ได้ตรงๆ

## Capabilities

### New Capabilities

ไม่มี

### Modified Capabilities

- `candidate-list`: เพิ่ม requirement toggle gate ด้าน fair value บนหน้า candidates และ gate ว่าง, ลำดับเมื่อไม่มี gate
- `risk-reward`: target เมื่อเลือก gate ผ่าน toggle และเมื่อไม่มี gate

## Impact

- `engine/shortlist/api.py`: `/candidates` รับ `gates`
- `engine/shortlist/core/candidates.py`, `core/fair_value.py`, `core/risk_reward.py`: ฟังก์ชันคำนวณใหม่จากผลที่เก็บไว้ และกรณี gate ว่าง
- `engine/shortlist/db.py`: อ่านผลการประเมินทั้งหมดของ run
- `web/app/page.tsx` และ component checkbox ใหม่
- engine tests (`test_api.py`, `test_candidates.py`, `test_risk_reward.py`)
- API เดิมที่ไม่ส่ง `gates` ได้ผลเดิม จึงไม่ breaking
