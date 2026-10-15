# risk-reward Specification

## Purpose

คำนวณ entry, stop, target, RRR และ reward ต่อเดือนของแต่ละหุ้น เพื่อบอกว่าโอกาสคุ้มความเสี่ยงและคุ้มเวลาที่เงินต้องแช่หรือไม่

## Requirements

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

### Requirement: ป้ายเตือน upside สูงผิดปกติ
ระบบ SHALL ติดป้ายเตือนเมื่อ upside = (target − entry) / entry สูงกว่าเกณฑ์ (default 100%, ปรับได้ในหน้า settings) เพื่อบอกว่า target อาจถูก band ในอดีตดึงสูงเกินจริง ระบบ SHALL ไม่ตัดหุ้นออกและไม่ใช้ป้ายนี้ในการเรียงลำดับ

#### Scenario: upside เกินเกณฑ์
- **WHEN** entry 2.70 และ target 15.73 (upside 483%)
- **THEN** หุ้นถูกติดป้ายเตือน upside สูงผิดปกติ และยังอยู่ใน candidate list ถ้าผ่าน gate อื่น

#### Scenario: upside ไม่เกินเกณฑ์
- **WHEN** entry 12.40 และ target 14.20 (upside 14.5%)
- **THEN** ไม่มีป้ายเตือน upside สูงผิดปกติ

#### Scenario: ไม่มี upside
- **WHEN** target ต่ำกว่าหรือเท่ากับ entry หรือ fair value panel ไม่มีเกณฑ์ที่คำนวณได้
- **THEN** ไม่มีป้ายเตือน upside สูงผิดปกติ
