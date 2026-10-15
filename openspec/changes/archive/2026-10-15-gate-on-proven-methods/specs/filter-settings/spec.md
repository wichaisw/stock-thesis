# Spec Delta

## MODIFIED Requirements

### Requirement: เลือกเกณฑ์ fair value และ CDC state
ระบบ SHALL ให้เลือกเกณฑ์ fair value ที่เปิดใช้และ CDC state ที่รับเข้า candidate list ได้จากตัวเลือกที่มีอยู่เท่านั้น และ SHALL ไม่ยอมให้บันทึกโดยไม่เลือกอะไรเลย ระบบ SHALL ไม่ยอมให้บันทึกเมื่อเกณฑ์ fair value ที่เปิดใช้ไม่มี gate method (`candidates.gate_methods`) เหลืออยู่เลย และ SHALL ระบุในตัวเลือกว่าเกณฑ์ใดเป็น gate method

#### Scenario: ปิด peer PE
- **WHEN** ผู้ใช้เอา peer PE ออกจากเกณฑ์ fair value แล้วบันทึก
- **THEN** batch ครั้งถัดไปไม่คำนวณ peer PE และ gate ด้าน fair value กับ target ใช้ Justified PBV ตัวเดียว

#### Scenario: ปิด gate method ทุกตัว
- **WHEN** ผู้ใช้เอาทั้ง peer PE และ Justified PBV ออกจากเกณฑ์ fair value แล้วกดบันทึก
- **THEN** ระบบไม่บันทึก และแจ้งเป็นภาษาไทยว่าต้องเปิดอย่างน้อยหนึ่งเกณฑ์ที่ใช้เป็น gate

#### Scenario: ปิด method ที่ไม่ใช่ gate
- **WHEN** ผู้ใช้เอา PBV band ออกจากเกณฑ์ fair value แล้วบันทึก
- **THEN** ระบบบันทึก และ gate ด้าน fair value ไม่เปลี่ยน มีแค่ panel ที่ไม่แสดง PBV band

#### Scenario: ไม่เลือก state เลย
- **WHEN** ผู้ใช้เอา CDC state ออกทั้งหมดแล้วกดบันทึก
- **THEN** ระบบไม่บันทึก และแจ้งว่าต้องเลือกอย่างน้อยหนึ่ง state

## ADDED Requirements

### Requirement: เกณฑ์ MoS ของ gate
หมวด candidates บนหน้า settings SHALL มีช่อง "MoS ขั้นต่ำของ gate method" (`candidates.min_gate_mos`, default 10%) แทนช่อง median MoS ขั้นต่ำเดิม tooltip SHALL อธิบายว่าทุก gate method ที่คำนวณได้ต้องมี MoS อย่างน้อยเท่านี้ และค่านี้ไม่ใช่ median ของ panel รายชื่อ gate methods SHALL ไม่อยู่บนหน้า settings ค่า median MoS ขั้นต่ำที่เคยบันทึกบนเว็บ SHALL ถูกข้ามพร้อม log เตือน และไม่ถูกย้ายมาเป็นค่าใหม่

#### Scenario: เปิดหน้า settings หลัง change นี้
- **WHEN** ผู้ใช้เปิดหน้า settings
- **THEN** หมวด candidates มีช่อง MoS ขั้นต่ำของ gate method ค่า default 10% และไม่มีช่อง median MoS ขั้นต่ำหรือช่องเลือก gate methods

#### Scenario: เคยบันทึก median MoS ขั้นต่ำไว้
- **WHEN** ผู้ใช้เคยบันทึก median MoS ขั้นต่ำเป็น 15% บนเว็บก่อน change นี้ แล้ว batch รัน
- **THEN** batch ใช้ MoS ขั้นต่ำของ gate method ตาม default ใน config และ log เตือนว่าข้ามค่าที่บันทึกไว้
