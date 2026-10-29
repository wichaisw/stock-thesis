# Spec Delta

## ADDED Requirements

### Requirement: ป้ายเกณฑ์ที่ fair value ไม่เข้ากับหุ้น
หน้ารายละเอียดหุ้น SHALL ติดป้าย "fair value ไม่เข้ากับหุ้นนี้" ที่แถวของเกณฑ์ที่ MoS ต่ำกว่า −100% ทั้งใน fair value panel และตาราง gate ด้าน fair value พร้อมคำอธิบายว่าเกณฑ์นั้นอาจไม่เหมาะกับธุรกิจของหุ้น แถวนั้น SHALL ยังแสดง fair value และ MoS เหมือนเดิม ป้ายนี้ SHALL ไม่เปลี่ยน gate, candidate rule, การเรียง, target หรือสรุปของ panel

#### Scenario: MoS ต่ำกว่า −100%
- **WHEN** Peer PE ของ BEM ได้ fair value 2.54 บาทที่ราคา 6.35 บาท (MoS −150%)
- **THEN** แถว Peer PE ติดป้าย "fair value ไม่เข้ากับหุ้นนี้" และยังแสดง fair value 2.54 และ MoS −150%

#### Scenario: MoS เท่ากับ −100% พอดี
- **WHEN** เกณฑ์หนึ่งมี MoS −100%
- **THEN** แถวนั้นไม่ติดป้าย

#### Scenario: เกณฑ์ที่คำนวณไม่ได้
- **WHEN** เกณฑ์หนึ่งเป็น N/A
- **THEN** แถวนั้นไม่ติดป้าย และแสดงเหตุผลที่คำนวณไม่ได้เหมือนเดิม

#### Scenario: gate ไม่เปลี่ยน
- **WHEN** gate method ตัวหนึ่งติดป้าย
- **THEN** ผลผ่านหรือไม่ผ่าน gate, MoS gate และ target ของหุ้นเท่ากับก่อนมีป้าย
