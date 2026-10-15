# Design

## Context

ดู proposal.md (Why) `risk_reward.evaluate` ตอนนี้รับ `today` และ `next_deadline` มาเพื่อคิดระยะถือเท่านั้น ผลลัพธ์ถูกเก็บเป็น JSON ใน `evaluations.result` แล้ว web อ่านตรง ๆ ผ่าน type ใน `web/lib/engine.ts` ค่าที่ผู้ใช้แก้ในหน้า settings เก็บเป็น override ในตาราง `settings` และ `load_config` ข้าม key ที่ไม่ใช่ editable field อยู่แล้ว

## Goals / Non-Goals

**Goals:**
- ไม่มีตัวเลขไหนใน risk/reward ที่ขึ้นกับระยะเวลาถือ
- ป้าย upside สูงผิดปกติตามแบบเดียวกับ `low_rrr` (flag บน risk_reward + Tag ใน UI)

**Non-Goals:**
- ย้อนแก้ evaluation ของ run เก่า

## Decisions

**D1 ลบ reward ต่อเดือนทิ้ง ไม่เปลี่ยนสูตร**
ทางเลือกที่ไม่เลือก: หารด้วย 12 เดือนคงที่ (เป็นแค่ upside หารค่าคงที่ ไม่บอกอะไรเพิ่ม), clamp ระยะถือเป็น 3–12 เดือน (ยังผูกกับกำหนดส่งงบซึ่งไม่ใช่ระยะ re-rate จริง) ข้อแลก: thesis ใน config บอกว่าไม่ควรแช่เงินเกินราว 1 ไตรมาส ตอนนี้ไม่มีตัวเลขไหนวัด opportunity cost ตามเวลาแล้ว ผู้ใช้ตัดสินเองจาก upside, CDC ETA และ event calendar

**D2 ลบ `today`/`next_deadline` ออกจาก signature ของ `risk_reward.evaluate` และเลิกเรียก `catalyst.next_statement_deadline` ใน batch**
ทางเลือกที่ไม่เลือก: คง parameter ไว้เผื่อใช้ทีหลัง (dead input) batch เป็นผู้เรียก `catalyst.next_statement_deadline` คนเดียว จึงลบฟังก์ชันนี้พร้อม test ของมันด้วย (`statement_deadlines` ที่ event calendar ใช้ยังอยู่) หลังลบ `next_deadline` parameter `today` ใน `batch.run`/`execute`/`collect` ไม่มีผู้ใช้แล้ว จึงลบด้วย `create_app` ยังรับ `today` เพราะ event calendar ใช้ แต่เลิกส่งให้ `batch.execute`

**D3 ป้ายอยู่ที่ `risk_reward.high_upside` เกณฑ์ `risk_reward.max_upside` (editable, percent, default 1.0)**
ทางเลือกที่ไม่เลือก: ใส่ใน fair value panel ตามแบบ `structure_change` (upside คิดใน risk_reward อยู่แล้ว ย้ายไปจะต้องคิดซ้ำ), ใช้ MoS แทน upside (MoS ไม่เกิน 100% ทำให้ตั้งเกณฑ์ไม่ตรงความหมาย "target ห่างราคาหลายเท่า"), ทำเป็น gate (ผู้ใช้เลือกเตือนอย่างเดียว) `high_upside` เป็น `false` เมื่อไม่มี upside

**D4 Web อ่าน `high_upside` แบบ optional (`high_upside?: boolean`)**
run เก่าไม่มี field นี้ จึงต้องไม่พัง ตามแบบ `history_gap?` ที่ทำอยู่แล้ว

## Risks / Trade-offs

- [หุ้นถูกจริงแบบ deep value โดนป้ายเตือนด้วย] → เป็นแค่ป้าย ไม่ตัดออก และปรับเกณฑ์ได้
- [Worst case: ป้ายทำให้ผู้ใช้มองข้ามหุ้นที่ดีจริง หรือกลับกัน ไม่มีป้ายแล้วเชื่อ target ที่ผิด เช่นหุ้นที่ upside 90% จาก band เก่า] → ป้ายนี้ไม่ใช่การตรวจข้อมูล ยังต้องใช้ `stock-sanity-check` / `data-crosscheck` กับหุ้นที่สงสัย
- [ไม่มีตัวชี้วัดตามเวลาเหลือ ขัดกับ thesis 1 ไตรมาส] → บันทึกเป็นข้อแลกใน D1 ถ้าต้องการภายหลังให้ทำ change ใหม่ที่ไม่ผูกกับกำหนดส่งงบ
- [ค่า override `min_hold_months`/`max_hold_months` ที่ผู้ใช้เคยบันทึก] → loader ข้ามอยู่แล้ว ใน DB ปัจจุบันไม่มีค่านี้ (มีแค่ liquidity)

## Migration Plan

Deploy ตามปกติแล้วรัน batch ใหม่ rollback คือ revert commit แล้วรัน batch ใหม่
