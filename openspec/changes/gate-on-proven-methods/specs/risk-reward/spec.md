# Spec Delta

## MODIFIED Requirements

### Requirement: Entry, stop และ target
ระบบ SHALL ใช้ entry = ราคาปิดล่าสุด, stop = ค่าต่ำกว่าระหว่าง low ต่ำสุด 20 วันทำการล่าสุด กับ Slow EMA ของ CDC × (1 − 3%) และ target = fair value ที่ต่ำกว่าของ gate methods (`candidates.gate_methods`) ที่คำนวณได้ พร้อมแสดง target แบบ optimistic = fair value สูงสุดของ panel ค่า 20 วันและ 3% SHALL ปรับได้ใน config

#### Scenario: คำนวณ stop
- **WHEN** low ต่ำสุด 20 วันคือ 11.80 บาท และ Slow EMA × 0.97 คือ 11.50 บาท
- **THEN** stop คือ 11.50 บาท

#### Scenario: target จาก gate methods
- **WHEN** fair value ของ peer PE คือ 15.00 บาท, ของ Justified PBV คือ 14.20 บาท และ median ของ panel คือ 18.00 บาท
- **THEN** target คือ 14.20 บาท และ target แบบ optimistic คือ fair value สูงสุดของ panel

#### Scenario: gate method คำนวณได้ตัวเดียว
- **WHEN** peer PE คำนวณไม่ได้ และ fair value ของ Justified PBV คือ 14.20 บาท
- **THEN** target คือ 14.20 บาท

### Requirement: กรณีคำนวณ RRR ไม่ได้
ระบบ SHALL แสดง RRR เป็น N/A พร้อมเหตุผล เมื่อ target ≤ entry, เมื่อ stop ≥ entry หรือเมื่อไม่มี gate method ที่คำนวณได้ (แม้ method อื่นใน panel คำนวณได้)

#### Scenario: ราคาสูงกว่า target แล้ว
- **WHEN** fair value ที่ต่ำกว่าของ gate methods ต่ำกว่าราคาปัจจุบัน
- **THEN** RRR แสดงเป็น N/A ด้วยเหตุผลว่าไม่มี upside

#### Scenario: ไม่มี gate method ที่คำนวณได้
- **WHEN** peer PE และ Justified PBV คำนวณไม่ได้ทั้งคู่ แต่ PE band คำนวณได้
- **THEN** target และ RRR แสดงเป็น N/A ด้วยเหตุผลว่าไม่มี gate method ที่คำนวณได้
