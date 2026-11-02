## ADDED Requirements

### Requirement: Target ตาม gate ที่เลือกบนหน้า candidates
เมื่อผู้ใช้เลือก gate บนหน้า candidates ระบบ SHALL คำนวณ target, upside, RRR และป้ายเตือน RRR ต่ำและ upside สูงผิดปกติใหม่จาก entry และ stop ที่ batch เก็บไว้ โดย target = fair value ที่ต่ำกว่าของ gate ที่เลือกที่คำนวณได้ เมื่อไม่มี gate ที่เลือก target SHALL เป็น median fair value ของ panel ระบบ SHALL ระบุว่า target มาจาก median ของ panel ในกรณีนั้น

#### Scenario: ปิด Peer PE
- **WHEN** fair value ของ Peer PE คือ 2.54, ของ Justified PBV คือ 9.00, entry 6.35, stop 6.00 และผู้ใช้เอา Peer PE ออก
- **THEN** target คือ 9.00 และ RRR คือ (9.00 − 6.35) ÷ (6.35 − 6.00) = 7.57

#### Scenario: ไม่มี gate ที่เลือก
- **WHEN** ไม่มี gate ที่เลือก และ median fair value ของ panel คือ 18.00
- **THEN** target คือ 18.00 พร้อมระบุว่ามาจาก median ของ panel

#### Scenario: ไม่มี gate และ panel ไม่มีเกณฑ์ที่คำนวณได้
- **WHEN** ไม่มี gate ที่เลือก และ panel ไม่มีเกณฑ์ที่คำนวณได้
- **THEN** target และ RRR แสดงเป็น N/A ด้วยเหตุผลว่าไม่มีเกณฑ์ที่คำนวณได้

#### Scenario: gate เท่ากับ batch
- **WHEN** gate ที่เลือกเท่ากับ `candidates.gate_methods`
- **THEN** target, RRR และป้ายเตือนเท่ากับค่าที่ batch คำนวณไว้
