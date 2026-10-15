# candidate-list Specification

## Purpose

รวมผลจากทุก gate เป็นรายการหุ้น candidates รายวันที่เรียงตาม timing และ margin of safety และให้ตรวจได้ว่าหุ้นตัวใดไม่ผ่านเพราะอะไร

## Requirements

### Requirement: เงื่อนไขการเข้า candidate list
ระบบ SHALL ใส่หุ้นใน candidate list เมื่อหุ้นผ่าน liquidity filter และ quality gate, มี median margin of safety ≥ เกณฑ์ (default 10%) และอยู่ใน CDC state `bear-approaching` หรือ `just-crossed` เกณฑ์ margin of safety และรายการ state ที่รับ SHALL ปรับได้ใน config

#### Scenario: ผ่านทุกเงื่อนไข
- **WHEN** หุ้นผ่าน quality gate, median margin of safety คือ 15% และอยู่ใน state `bear-approaching`
- **THEN** หุ้นอยู่ใน candidate list

#### Scenario: พื้นฐานดีแต่ timing ไม่ใช่
- **WHEN** หุ้นผ่าน quality gate และ margin of safety แต่อยู่ใน state `bear-far`
- **THEN** หุ้นไม่อยู่ใน candidate list

#### Scenario: เปลี่ยน CDC เป็นตัวเรียงอย่างเดียว
- **WHEN** ผู้ใช้ตั้ง config ให้รับทุก CDC state
- **THEN** candidate list ใช้ CDC เพื่อเรียงลำดับเท่านั้น ไม่ใช้ตัดหุ้นออก

### Requirement: การเรียงลำดับ
ระบบ SHALL เรียง candidate list โดย `just-crossed` มาก่อน ตามด้วย ETA จากน้อยไปมาก และเมื่อเท่ากันให้เรียงตาม median margin of safety จากมากไปน้อย ระบบ SHALL ไม่ใช้ weighted score

#### Scenario: เรียงตาม ETA
- **WHEN** หุ้น A มี ETA 4 วัน และหุ้น B มี ETA 12 วัน
- **THEN** หุ้น A อยู่ก่อนหุ้น B

### Requirement: ข้อมูลที่แสดงใน candidate list
ระบบ SHALL แสดงหุ้นแต่ละตัวใน candidate list พร้อม symbol, sector, ราคาล่าสุด, CDC state และ ETA, สรุป fair value panel, RRR, ป้าย inflection, ป้ายเตือน RRR ต่ำ, ป้ายเตือน upside สูงผิดปกติ, ป้ายราคาไม่อัปเดต และวันที่ของข้อมูล เมื่อ run มีหุ้นที่ราคาไม่อัปเดต ระบบ SHALL แสดงบรรทัดเตือนใต้วันที่ของข้อมูล บอกจำนวนหุ้นที่ราคาไม่อัปเดตเทียบกับจำนวนที่ประเมินได้และวันที่ราคาของกลุ่มนั้น

#### Scenario: เปิดดู candidate list
- **WHEN** ผู้ใช้เปิดหน้า candidate list หลัง batch รันสำเร็จ
- **THEN** ระบบแสดงหุ้นตามลำดับพร้อมข้อมูลครบทุกคอลัมน์ และระบุวันที่ของข้อมูลราคาล่าสุด

#### Scenario: run ที่ราคาไม่อัปเดตบางส่วน
- **WHEN** run ล่าสุดประเมินได้ 922 ตัว และ 897 ตัวราคาไม่อัปเดตโดยแท่งล่าสุดเป็นวันที่ 12 ต.ค.
- **THEN** หน้า candidate list แสดงบรรทัดเตือนว่าราคา 897/922 ตัวเป็นวันที่ 12 ต.ค. และ candidate ที่ราคาไม่อัปเดตมีป้ายราคาไม่อัปเดต

#### Scenario: run เก่าที่ไม่มีข้อมูลราคาไม่อัปเดต
- **WHEN** run ล่าสุดรันก่อนมีการตรวจนี้
- **THEN** หน้า candidate list แสดงได้ตามปกติ ไม่มีบรรทัดเตือนและไม่มีป้ายราคาไม่อัปเดต

### Requirement: หน้ารายละเอียดและเหตุผลที่ไม่ผ่าน
ระบบ SHALL ให้ผู้ใช้เปิดหน้ารายละเอียดของหุ้นตัวใดก็ได้ที่ถูกประเมิน (ไม่จำกัดเฉพาะ candidates) โดยแสดงผลของแต่ละ gate ว่าผ่านหรือไม่ผ่านพร้อมค่าจริงและเกณฑ์, fair value panel, ข้อมูล CDC, RRR, catalyst hints และ event calendar และ SHALL แสดงป้ายราคาไม่อัปเดตข้างวันที่ราคาเมื่อหุ้นติดป้ายนี้

#### Scenario: ตรวจหุ้นที่ไม่ติด list
- **WHEN** ผู้ใช้ค้นหาหุ้นที่ไม่อยู่ใน candidate list
- **THEN** หน้ารายละเอียดแสดงว่าหุ้นไม่ผ่าน gate ไหนบ้าง พร้อมค่าจริงและเกณฑ์

#### Scenario: หุ้นที่ดึงข้อมูลไม่ได้
- **WHEN** ผู้ใช้ค้นหาหุ้นที่ fail ใน batch ล่าสุด
- **THEN** หน้ารายละเอียดแสดงว่าดึงข้อมูลไม่ได้พร้อมเหตุผล

#### Scenario: หุ้นที่ราคาไม่อัปเดต
- **WHEN** ผู้ใช้เปิดหน้ารายละเอียดของหุ้นที่แท่งล่าสุดเป็นวันที่ 12 ต.ค. ใน run ที่วันที่ราคาคือ 14 ต.ค.
- **THEN** บรรทัดราคาปิดแสดงวันที่ 12 ต.ค. พร้อมป้ายราคาไม่อัปเดต

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
