## ADDED Requirements

### Requirement: Toggle gate ด้าน fair value บนหน้า candidates
ระบบ SHALL แสดง checkbox ของ gate method แต่ละตัว (Peer PE, Justified PBV) บนหน้า candidates โดยค่าเริ่มต้นตาม `candidates.gate_methods` เมื่อผู้ใช้เปลี่ยน checkbox ระบบ SHALL แสดง candidate list ที่คำนวณใหม่จากผลการประเมินของ run ล่าสุดด้วย gate ที่เลือก โดยไม่ดึงข้อมูลใหม่ ไม่รัน batch และไม่เปลี่ยนผลที่เก็บไว้ ค่าที่เลือก SHALL อยู่ใน URL ของหน้า และ SHALL ไม่ถูกบันทึกเป็น setting

#### Scenario: เปิดหน้าครั้งแรก
- **WHEN** ผู้ใช้เปิดหน้า candidates โดยไม่มีค่า gate ใน URL
- **THEN** checkbox Peer PE และ Justified PBV ถูกเลือกทั้งคู่ และ list เหมือนผลของ batch ทุกประการ

#### Scenario: ปิด Peer PE
- **WHEN** หุ้นมี MoS ของ Peer PE −150% และของ Justified PBV 25% ผ่านเงื่อนไขอื่นทั้งหมด และผู้ใช้เอา checkbox Peer PE ออก
- **THEN** หุ้นนั้นอยู่ใน candidate list และ gate MoS ที่แสดงคือ 25% (Justified PBV)

#### Scenario: เปิดลิงก์ที่มีค่า gate
- **WHEN** ผู้ใช้เปิด URL ของหน้า candidates ที่ระบุให้ใช้ Justified PBV ตัวเดียว
- **THEN** checkbox Justified PBV ถูกเลือก Peer PE ไม่ถูกเลือก และ list ใช้ Justified PBV ตัวเดียว

#### Scenario: run ใหม่หลังเลือก gate
- **WHEN** ผู้ใช้ปิด Peer PE ไว้แล้ว batch รันเสร็จใหม่ และผู้ใช้โหลดหน้าเดิมซ้ำ
- **THEN** list คำนวณจาก run ใหม่ด้วย Justified PBV ตัวเดียว

#### Scenario: ค่าที่ไม่ใช่ gate method
- **WHEN** URL ระบุ gate เป็น `pe_median`
- **THEN** ระบบไม่ใช้ค่านั้นเป็น gate และแจ้งเป็นภาษาไทยว่าเลือกได้เฉพาะ Peer PE และ Justified PBV

#### Scenario: หน้าอื่นไม่เปลี่ยน
- **WHEN** ผู้ใช้ปิด Peer PE บนหน้า candidates แล้วเปิดหน้ารายละเอียดหุ้น, candidate history หรือหน้าหุ้นที่ถือ
- **THEN** หน้าเหล่านั้นยังแสดงผลตาม gate ของ batch

### Requirement: ไม่ใช้ gate ด้าน fair value
ระบบ SHALL ให้เอา gate method ออกทั้งหมดได้ เมื่อไม่มี gate ที่เลือก หุ้นผ่าน gate ด้าน fair value ทุกตัวที่มีงบ ระบบ SHALL เรียง list ด้วย `just-crossed` ก่อนแล้ว ETA จากน้อยไปมาก และเมื่อเท่ากันให้เรียงตาม symbol และ SHALL แสดงบนหน้าว่ากำลังไม่ใช้ gate ด้าน fair value

#### Scenario: ปิดทั้งสอง gate
- **WHEN** หุ้นมี MoS ของ Peer PE −20% และของ Justified PBV −30% ผ่าน liquidity, quality และอยู่ใน state ที่รับ และผู้ใช้เอา checkbox ออกทั้งคู่
- **THEN** หุ้นนั้นอยู่ใน candidate list และหน้าแสดงข้อความว่าไม่ได้ใช้ gate ด้าน fair value

#### Scenario: ไม่มี gate และ ETA เท่ากัน
- **WHEN** ไม่มี gate ที่เลือก และหุ้น AAA กับ BBB มี state และ ETA เท่ากัน
- **THEN** AAA อยู่ก่อน BBB

#### Scenario: ไม่มี gate แต่ quality ไม่ผ่าน
- **WHEN** ไม่มี gate ที่เลือก และหุ้นไม่ผ่าน quality gate
- **THEN** หุ้นไม่อยู่ใน candidate list
