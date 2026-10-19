# candidate-list Specification

## Purpose

รวมผลจากทุก gate เป็นรายการหุ้น candidates รายวันที่เรียงตาม timing และ margin of safety และให้ตรวจได้ว่าหุ้นตัวใดไม่ผ่านเพราะอะไร

## Requirements

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

### Requirement: ข้อมูลที่แสดงใน candidate list
ระบบ SHALL แสดงหุ้นแต่ละตัวใน candidate list พร้อม symbol, sector, ราคาล่าสุด, CDC state และ ETA, สรุป fair value panel, RRR, ป้าย inflection, ป้ายเตือน RRR ต่ำ, ป้ายเตือน upside สูงผิดปกติ, ป้ายราคาไม่อัปเดต, ป้ายกำไรกระโดด, ป้ายงบใกล้ออก และวันที่ของข้อมูล เมื่อ run มีหุ้นที่ราคาไม่อัปเดต ระบบ SHALL แสดงบรรทัดเตือนใต้วันที่ของข้อมูล บอกจำนวนหุ้นที่ราคาไม่อัปเดตเทียบกับจำนวนที่ประเมินได้และวันที่ราคาของกลุ่มนั้น

#### Scenario: เปิดดู candidate list
- **WHEN** ผู้ใช้เปิดหน้า candidate list หลัง batch รันสำเร็จ
- **THEN** ระบบแสดงหุ้นตามลำดับพร้อมข้อมูลครบทุกคอลัมน์ และระบุวันที่ของข้อมูลราคาล่าสุด

#### Scenario: run ที่ราคาไม่อัปเดตบางส่วน
- **WHEN** run ล่าสุดประเมินได้ 922 ตัว และ 897 ตัวราคาไม่อัปเดตโดยแท่งล่าสุดเป็นวันที่ 12 ต.ค.
- **THEN** หน้า candidate list แสดงบรรทัดเตือนว่าราคา 897/922 ตัวเป็นวันที่ 12 ต.ค. และ candidate ที่ราคาไม่อัปเดตมีป้ายราคาไม่อัปเดต

#### Scenario: run เก่าที่ไม่มีข้อมูลราคาไม่อัปเดต
- **WHEN** run ล่าสุดรันก่อนมีการตรวจนี้
- **THEN** หน้า candidate list แสดงได้ตามปกติ ไม่มีบรรทัดเตือนและไม่มีป้ายราคาไม่อัปเดต

#### Scenario: candidate ที่ติดป้ายความเสี่ยง
- **WHEN** candidate ติดป้ายกำไรกระโดดและป้ายงบใกล้ออก
- **THEN** คอลัมน์ป้ายแสดงทั้งสองป้าย และเมื่อชี้ที่ป้ายจะเห็นเหตุผลของป้ายนั้น

#### Scenario: run เก่าที่ไม่มีป้ายความเสี่ยง
- **WHEN** run ล่าสุดรันก่อนมีป้ายกำไรกระโดดและป้ายงบใกล้ออก
- **THEN** หน้า candidate list แสดงได้ตามปกติโดยไม่มีป้ายเหล่านี้

### Requirement: หน้ารายละเอียดและเหตุผลที่ไม่ผ่าน
ระบบ SHALL ให้ผู้ใช้เปิดหน้ารายละเอียดของหุ้นตัวใดก็ได้ที่ถูกประเมิน (ไม่จำกัดเฉพาะ candidates) โดยแสดงผลของแต่ละ gate ว่าผ่านหรือไม่ผ่านพร้อมค่าจริงและเกณฑ์, fair value panel, ข้อมูล CDC, RRR, catalyst hints และ event calendar และ SHALL แสดงป้ายราคาไม่อัปเดตข้างวันที่ราคาเมื่อหุ้นติดป้ายนี้ และ SHALL แสดงป้ายกำไรกระโดดและป้ายงบใกล้ออกพร้อมเหตุผลเมื่อหุ้นติดป้ายนั้น

#### Scenario: ตรวจหุ้นที่ไม่ติด list
- **WHEN** ผู้ใช้ค้นหาหุ้นที่ไม่อยู่ใน candidate list
- **THEN** หน้ารายละเอียดแสดงว่าหุ้นไม่ผ่าน gate ไหนบ้าง พร้อมค่าจริงและเกณฑ์

#### Scenario: หุ้นที่ดึงข้อมูลไม่ได้
- **WHEN** ผู้ใช้ค้นหาหุ้นที่ fail ใน batch ล่าสุด
- **THEN** หน้ารายละเอียดแสดงว่าดึงข้อมูลไม่ได้พร้อมเหตุผล

#### Scenario: หุ้นที่ราคาไม่อัปเดต
- **WHEN** ผู้ใช้เปิดหน้ารายละเอียดของหุ้นที่แท่งล่าสุดเป็นวันที่ 12 ต.ค. ใน run ที่วันที่ราคาคือ 14 ต.ค.
- **THEN** บรรทัดราคาปิดแสดงวันที่ 12 ต.ค. พร้อมป้ายราคาไม่อัปเดต

#### Scenario: หุ้นที่กำไรกระโดด
- **WHEN** ผู้ใช้เปิดหน้ารายละเอียดของหุ้นที่ติดป้ายกำไรกระโดด
- **THEN** หน้ารายละเอียดแสดงป้ายพร้อมกำไรสุทธิทั้งสองช่วงและอัตราส่วน

### Requirement: Mark หุ้นที่ดึงข้อมูลไม่ได้
ระบบ SHALL แสดง icon เตือนที่หุ้นทุกตัวที่ fail ใน batch ล่าสุด ทั้งในผลค้นหาและในหน้ารายละเอียด และ SHALL แสดงจำนวนหุ้นที่ fail ของ run ล่าสุดในหน้า candidate list ซึ่งกดเปิดดูรายชื่อพร้อมเหตุผลได้

#### Scenario: ค้นหาเจอหุ้นที่ fail
- **WHEN** ผลค้นหามีหุ้นที่ fail ใน batch ล่าสุด
- **THEN** หุ้นตัวนั้นมี icon เตือนกำกับ และเมื่อชี้ที่ icon จะเห็นเหตุผล

#### Scenario: ดูรายชื่อหุ้นที่ fail
- **WHEN** batch ล่าสุดมีหุ้น fail 3 ตัว และผู้ใช้กดที่จำนวนหุ้นที่ fail ในหน้า candidate list
- **THEN** ระบบแสดงรายชื่อหุ้นทั้ง 3 ตัว แต่ละตัวมี icon เตือนและเหตุผล

#### Scenario: batch ไม่มีหุ้นที่ fail
- **WHEN** batch ล่าสุดไม่มีหุ้นที่ fail
- **THEN** หน้า candidate list ไม่แสดง icon เตือนหรือจำนวนหุ้นที่ fail

### Requirement: ข้อมูลเก่าหรือยังไม่มีข้อมูล
ระบบ SHALL แสดงผลของ batch ที่สำเร็จล่าสุดพร้อมเวลาที่รัน และ SHALL แจ้งเมื่อยังไม่เคยมี batch ที่สำเร็จ

#### Scenario: ยังไม่เคยรัน batch
- **WHEN** ผู้ใช้เปิดแอปครั้งแรกโดยยังไม่เคยรัน batch
- **THEN** หน้า candidate list แจ้งว่ายังไม่มีข้อมูล และมีปุ่มให้รัน batch

### Requirement: จำนวน gate ที่ผ่าน
ระบบ SHALL แสดงจำนวน gate ที่ผ่านเทียบกับจำนวน gate ที่ประเมิน (liquidity รวมกับเกณฑ์ของ quality gate ที่ไม่ถูกข้าม) เป็นคอลัมน์ "Gates" ใน candidate list และที่หัวข้อ Gates ในหน้ารายละเอียด เมื่อชี้ที่จำนวนใน candidate list ระบบ SHALL แสดงเกณฑ์ที่ไม่ผ่านพร้อมค่าจริง จำนวนนี้ SHALL ไม่ใช้เรียงลำดับ candidates

#### Scenario: หุ้นทั่วไปไม่ผ่านหนึ่งเกณฑ์
- **WHEN** candidate เป็นหุ้นทั่วไปที่ไม่ผ่านเกณฑ์ D/E (D/E 2.30) และผ่านเกณฑ์อื่นทั้งหมด
- **THEN** คอลัมน์ Gates แสดง 5/6 และเมื่อชี้จะเห็นว่าไม่ผ่าน D/E พร้อมค่า 2.30

#### Scenario: หุ้นการเงิน
- **WHEN** candidate เป็นหุ้นธนาคารที่ผ่านทุกเกณฑ์ที่ประเมิน และเกณฑ์ D/E กับ OCF ถูกข้าม
- **THEN** คอลัมน์ Gates แสดง 4/4

#### Scenario: จำนวน gate ไม่เปลี่ยนลำดับ
- **WHEN** หุ้น A ผ่าน 4/6 มี ETA 3 วัน และหุ้น B ผ่าน 6/6 มี ETA 10 วัน
- **THEN** หุ้น A อยู่ก่อนหุ้น B

#### Scenario: หน้ารายละเอียดของหุ้นที่ไม่ได้ดึงงบ
- **WHEN** ผู้ใช้เปิดหน้ารายละเอียดของหุ้นที่ไม่ผ่าน liquidity filter
- **THEN** หัวข้อ Gates แสดง 0/1 และยังแจ้งว่าไม่ได้ดึงงบเพราะไม่ผ่าน liquidity filter

#### Scenario: run เก่าก่อน change นี้
- **WHEN** ผู้ใช้เปิด candidate list ของ run ที่รันก่อน change นี้
- **THEN** คอลัมน์ Gates แสดงจำนวนจากผลของแต่ละเกณฑ์ที่เก็บไว้ โดยหน้าไม่พัง

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
