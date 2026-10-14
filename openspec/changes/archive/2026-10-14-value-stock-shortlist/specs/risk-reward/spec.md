# Spec Delta

## Purpose

คำนวณ entry, stop, target, RRR และ reward ต่อเดือนของแต่ละหุ้น เพื่อบอกว่าโอกาสคุ้มความเสี่ยงและคุ้มเวลาที่เงินต้องแช่หรือไม่

## ADDED Requirements

### Requirement: Entry, stop และ target
ระบบ SHALL ใช้ entry = ราคาปิดล่าสุด, stop = ค่าต่ำกว่าระหว่าง low ต่ำสุด 20 วันทำการล่าสุด กับ Slow EMA ของ CDC × (1 − 3%) และ target = median ของ fair value panel พร้อมแสดง target แบบ optimistic = fair value สูงสุดของ panel ค่า 20 วันและ 3% SHALL ปรับได้ใน config

#### Scenario: คำนวณ stop
- **WHEN** low ต่ำสุด 20 วันคือ 11.80 บาท และ Slow EMA × 0.97 คือ 11.50 บาท
- **THEN** stop คือ 11.50 บาท

### Requirement: RRR
ระบบ SHALL คำนวณ RRR = (target − entry) / (entry − stop) และ SHALL ติดป้ายเตือนเมื่อ RRR ต่ำกว่าเกณฑ์ (default 2) โดยไม่ตัดหุ้นออก

#### Scenario: RRR ผ่านเกณฑ์
- **WHEN** entry 12.40, stop 11.50 และ target 14.20
- **THEN** RRR คือ 2.0 และไม่มีป้ายเตือน

#### Scenario: RRR ต่ำ
- **WHEN** RRR ที่คำนวณได้คือ 1.2
- **THEN** หุ้นถูกติดป้ายเตือนว่า RRR ต่ำกว่าเกณฑ์

### Requirement: กรณีคำนวณ RRR ไม่ได้
ระบบ SHALL แสดง RRR เป็น N/A พร้อมเหตุผล เมื่อ target ≤ entry, เมื่อ stop ≥ entry หรือเมื่อ fair value panel ไม่มีเกณฑ์ที่คำนวณได้

#### Scenario: ราคาสูงกว่า target แล้ว
- **WHEN** median ของ fair value panel ต่ำกว่าราคาปัจจุบัน
- **THEN** RRR แสดงเป็น N/A ด้วยเหตุผลว่าไม่มี upside

### Requirement: Reward ต่อเดือน
ระบบ SHALL คำนวณ reward ต่อเดือน = upside% / ระยะถือที่คาด โดยระยะถือที่คาดคือจำนวนเดือนจากวันนี้ถึงกำหนดส่งงบครั้งถัดไป (จาก event calendar) แต่ไม่น้อยกว่า 1 และไม่เกิน 3 เดือน

#### Scenario: งบใกล้ออก
- **WHEN** upside คือ 15% และกำหนดส่งงบครั้งถัดไปอยู่ในอีก 0.5 เดือน
- **THEN** ระยะถือที่คาดคือ 1 เดือน และ reward ต่อเดือนคือ 15%

#### Scenario: งบอีกนาน
- **WHEN** upside คือ 15% และกำหนดส่งงบครั้งถัดไปอยู่ในอีก 2.5 เดือน
- **THEN** reward ต่อเดือนคือ 6%
