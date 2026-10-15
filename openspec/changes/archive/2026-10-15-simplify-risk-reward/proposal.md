# Proposal

## Why

reward ต่อเดือนให้ค่าที่สุดโต่งและไม่บอกอะไรเพิ่ม ใน run 19 ทุกหุ้นที่มีค่า (249 ตัว) มีระยะถือ 1.02 เดือนเท่ากันหมด เพราะงบ Q3 ใกล้ออกและโดน clamp ที่ขั้นต่ำ reward ต่อเดือนจึงเท่ากับ upside × 0.98 แต่ดูเหมือนตัวเลขต่อเดือนที่แม่นยำ (เช่น EA 474%/เดือน, SRICHA ซึ่งเป็น candidate อันดับ 8 ที่ 264%/เดือน) สูตรยังสมมติว่าราคาจะถึง fair value ภายในรอบงบเดียว ทั้งที่การ re-rate มักใช้หลายไตรมาส ผู้ใช้ตั้งใจถือราว 1–4 เดือน แต่ไม่ต้องการให้ระยะเวลานี้กำหนดสูตร

ต้นเหตุอีกครึ่งคือ target ที่สูงผิดปกติ (EA target 15.73 เทียบราคา 2.70) ซึ่งมักมาจาก band ที่ยังจำช่วงกำไรดีในอดีต ตอนนี้ไม่มีอะไรเตือนเรื่องนี้

ตรวจแล้วด้วยว่า fair value ไม่ได้ใช้ CDC ส่วน stop ยังใช้ Slow EMA ของ CDC ต่อไปตามที่ผู้ใช้เลือก

## What Changes

- **BREAKING** เลิกคำนวณและแสดง reward ต่อเดือนกับระยะถือที่คาด ทั้งใน engine, candidate list, หน้ารายละเอียด และข้อความที่คัดลอกให้ LLM
- **BREAKING** ลบเกณฑ์ `risk_reward.min_hold_months` และ `risk_reward.max_hold_months` ออกจาก config และหน้า settings ค่าที่เคยบันทึกไว้ใน DB ถูกข้ามไปเอง (loader ข้าม key ที่ไม่รู้จักอยู่แล้ว)
- risk/reward ไม่ใช้กำหนดส่งงบครั้งถัดไปอีก (event calendar ยังแสดงตามเดิม)
- เพิ่มป้ายเตือน "upside สูงผิดปกติ" เมื่อ upside เกินเกณฑ์ (default 100%, แก้ได้ในหน้า settings) แสดงคู่กับป้าย RRR ต่ำ เตือนเท่านั้น ไม่ตัดหุ้นออกจาก candidate list

นอกขอบเขต:
- สูตร stop (ยังเป็นค่าที่ต่ำกว่าระหว่าง swing low กับ Slow EMA × (1 − buffer))
- การแก้ fair value หรือ band ที่ทำให้ target สูงเกินจริง ป้ายเตือนนี้แค่ชี้ให้เห็น
- ค่า RRR ที่สูงมากเพราะ stop ชิด entry
- การใช้ upside เป็น gate หรือตัว sort

ความสัมพันธ์กับ change อื่น: ไม่บล็อกและไม่ถูกบล็อกโดย `investor-type-flow` (คนละไฟล์ คนละ capability)

## Capabilities

### New Capabilities
- (ไม่มี)

### Modified Capabilities
- `risk-reward`: ลบ requirement reward ต่อเดือน, เพิ่ม requirement ป้ายเตือน upside สูงผิดปกติ, ปรับ Purpose
- `candidate-list`: คอลัมน์ reward ต่อเดือนออก, เพิ่มป้ายเตือน upside สูงผิดปกติ
- `filter-settings`: การตรวจค่าไม่มีเงื่อนไขระยะถือขั้นต่ำ/สูงสุดอีก

## Impact

- **engine**: `shortlist/core/risk_reward.py`, `shortlist/config.py` (`RiskReward`), `config.yaml`, `shortlist/batch.py` (เลิกส่ง `next_deadline` และลบ `today` ที่ไม่มีผู้ใช้แล้ว), `shortlist/api.py` (เลิกส่ง `today()` ให้ `batch.execute`), tests `test_risk_reward.py`, `test_config.py`, `test_batch.py`
- **web**: `lib/engine.ts`, `app/page.tsx`, `app/stocks/[symbol]/page.tsx`, `lib/llm-export.ts` และ test
- **ข้อมูลเก่า**: evaluation ของ run ก่อนหน้ายังมี `reward_per_month` แต่ web ไม่อ่านแล้ว และไม่มี `high_upside` จนกว่าจะรัน batch ใหม่
