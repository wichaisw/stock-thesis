# Spec Delta

## ADDED Requirements

### Requirement: CDC แยกจาก quality และ fair value
ผล quality gate, fair value panel และ MoS gate ของหุ้น SHALL ไม่ขึ้นกับค่า CDC ใน config หรือผล CDC และผล CDC SHALL ไม่ขึ้นกับค่า quality หรือ fair value ใน config ส่วนที่ใช้ CDC โดยตั้งใจ ได้แก่ stop ของ risk/reward และ state ใน candidate rule ไม่อยู่ในข้อนี้

#### Scenario: เปลี่ยนค่า CDC
- **WHEN** ประเมินหุ้นตัวเดียวกันด้วยราคาและงบเดียวกันสองครั้ง ต่างกันแค่ความยาว EMA ของ CDC จน CDC state ต่างกัน
- **THEN** ผล quality gate, fair value panel และ MoS gate เท่ากันทุกค่าทั้งสองครั้ง

#### Scenario: เปลี่ยนค่า fair value
- **WHEN** ประเมินหุ้นตัวเดียวกันด้วยราคาและงบเดียวกันสองครั้ง ต่างกันแค่ cost of equity ของ Justified PBV
- **THEN** ผล CDC (Fast, Slow, gap%, ETA, state) เท่ากันทุกค่าทั้งสองครั้ง
