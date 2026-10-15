# Spec Delta

## MODIFIED Requirements

### Requirement: เงื่อนไขการเข้า candidate list
ระบบ SHALL ใส่หุ้นใน candidate list เมื่อหุ้นผ่าน liquidity filter และ quality gate, ผ่าน gate ด้าน fair value และอยู่ใน CDC state `bear-approaching` หรือ `just-crossed` gate ด้าน fair value ผ่านเมื่อมี gate method (`candidates.gate_methods`, default `peer_pe` และ `justified_pbv`) ที่คำนวณได้อย่างน้อย 1 ตัว และทุกตัวที่คำนวณได้มี MoS ≥ เกณฑ์ (`candidates.min_gate_mos`, default 10%) เกณฑ์ MoS และรายการ state ที่รับ SHALL ปรับได้ใน config

#### Scenario: ผ่านทุกเงื่อนไข
- **WHEN** หุ้นผ่าน quality gate, MoS ของ peer PE คือ 15% และของ Justified PBV คือ 22% และอยู่ใน state `bear-approaching`
- **THEN** หุ้นอยู่ใน candidate list

#### Scenario: gate method ตัวหนึ่งต่ำกว่าเกณฑ์
- **WHEN** หุ้นผ่าน quality gate และอยู่ใน state ที่รับ MoS ของ peer PE คือ 25% แต่ของ Justified PBV คือ 4%
- **THEN** หุ้นไม่อยู่ใน candidate list และเหตุผลระบุว่า MoS ของ Justified PBV 4.0% ต่ำกว่าเกณฑ์ 10%

#### Scenario: gate method คำนวณได้ตัวเดียว
- **WHEN** Justified PBV คำนวณไม่ได้ (เช่น ROE TTM ไม่ผ่านเงื่อนไขของ method) และ MoS ของ peer PE คือ 12%
- **THEN** หุ้นผ่าน gate ด้าน fair value

#### Scenario: ไม่มี gate method ที่คำนวณได้
- **WHEN** peer PE และ Justified PBV คำนวณไม่ได้ทั้งคู่ แม้ method อื่นใน panel คำนวณได้และ median MoS คือ 40%
- **THEN** หุ้นไม่อยู่ใน candidate list และเหตุผลภาษาไทยระบุว่าไม่มี gate method ที่คำนวณได้

#### Scenario: median MoS ไม่ใช่ gate แล้ว
- **WHEN** median MoS ของ panel คือ −5% แต่ทุก gate method ที่คำนวณได้มี MoS ≥ 10% และหุ้นผ่านเงื่อนไขอื่น
- **THEN** หุ้นอยู่ใน candidate list

#### Scenario: พื้นฐานดีแต่ timing ไม่ใช่
- **WHEN** หุ้นผ่าน quality gate และ gate ด้าน fair value แต่อยู่ใน state `bear-far`
- **THEN** หุ้นไม่อยู่ใน candidate list

#### Scenario: เปลี่ยน CDC เป็นตัวเรียงอย่างเดียว
- **WHEN** ผู้ใช้ตั้ง config ให้รับทุก CDC state
- **THEN** candidate list ใช้ CDC เพื่อเรียงลำดับเท่านั้น ไม่ใช้ตัดหุ้นออก

### Requirement: การเรียงลำดับ
ระบบ SHALL เรียง candidate list โดย `just-crossed` มาก่อน ตามด้วย ETA จากน้อยไปมาก และเมื่อเท่ากันให้เรียงตาม MoS gate (MoS ที่ต่ำกว่าของ gate methods ที่คำนวณได้) จากมากไปน้อย ระบบ SHALL ไม่ใช้ weighted score

#### Scenario: เรียงตาม ETA
- **WHEN** หุ้น A มี ETA 4 วัน และหุ้น B มี ETA 12 วัน
- **THEN** หุ้น A อยู่ก่อนหุ้น B

#### Scenario: ETA เท่ากัน
- **WHEN** หุ้น A และ B มี state และ ETA เท่ากัน หุ้น A มี MoS gate 12% แต่ median MoS 50% และหุ้น B มี MoS gate 30% แต่ median MoS 20%
- **THEN** หุ้น B อยู่ก่อนหุ้น A

## ADDED Requirements

### Requirement: แสดง MoS gate
ระบบ SHALL แสดง MoS gate เป็นคอลัมน์ "MoS gate" ใน candidate list และในหน้ารายละเอียด พร้อมชื่อ gate method ที่ให้ค่านั้น คอลัมน์สรุป fair value panel (MoS ต่ำสุด / median / สูงสุด) SHALL ยังแสดงเหมือนเดิมแต่ไม่เน้นค่า median หน้ารายละเอียด SHALL แสดงในส่วน gate ว่าแต่ละ gate method มี MoS เท่าไร หรือคำนวณไม่ได้พร้อมเหตุผล เทียบกับเกณฑ์

#### Scenario: candidate ที่มี gate method สองตัว
- **WHEN** candidate มี MoS ของ peer PE 18% และของ Justified PBV 12%
- **THEN** คอลัมน์ MoS gate แสดง 12% และระบุว่ามาจาก Justified PBV

#### Scenario: หน้ารายละเอียดของหุ้นที่ไม่ผ่าน gate ด้าน fair value
- **WHEN** ผู้ใช้เปิดหน้ารายละเอียดของหุ้นที่ peer PE คำนวณไม่ได้และ Justified PBV มี MoS 4%
- **THEN** ส่วน gate แสดงว่า peer PE คำนวณไม่ได้พร้อมเหตุผล และ Justified PBV 4% ต่ำกว่าเกณฑ์ 10%

#### Scenario: run เก่าก่อน change นี้
- **WHEN** ผู้ใช้เปิดหน้าของ run ที่รันก่อน change นี้ ซึ่งไม่มีค่า MoS gate
- **THEN** คอลัมน์ MoS gate แสดง N/A และหน้าไม่พัง
