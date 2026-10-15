# Spec Delta

## MODIFIED Requirements

### Requirement: วัดผลที่ 63 วันทำการ
backtest SHALL วัดผลของแต่ละการประเมินที่ 63 วันทำการหลังวันที่ทดสอบ แยกตาม method แต่ละตัว, median MoS, MoS gate (MoS ที่ต่ำกว่าของ gate methods ที่คำนวณได้) และกลุ่ม candidate rule (ผ่าน quality gate และผ่าน gate ด้าน fair value ตาม `candidates.gate_methods` และ `candidates.min_gate_mos` เหมือน batch) ด้วย hit rate, excess return และผลตอบแทนแยกตาม bucket ของ MoS การประเมินที่ยังไม่ครบ 63 วันทำการ SHALL ไม่ถูกนับ

#### Scenario: hit rate
- **WHEN** method ให้ MoS > 0 กับหุ้น ณ วันที่ทดสอบ
- **THEN** นับเป็น hit ถ้าราคาสูงสุดของวันทำการที่ 1 ถึง 63 หลังจากนั้นถึง fair value ของ method นั้น และรายงาน % hit ต่อ method แยกตาม bucket ของ MoS

#### Scenario: hit rate ของกลุ่ม candidate
- **WHEN** หุ้นอยู่ในกลุ่ม candidate ณ วันที่ทดสอบ
- **THEN** นับเป็น hit ถ้าราคาสูงสุดของวันทำการที่ 1 ถึง 63 ถึง fair value ที่ต่ำกว่าของ gate methods (target เดียวกับ batch)

#### Scenario: excess return
- **WHEN** กลุ่มของ method มีหุ้นที่ MoS ≥ `candidates.min_gate_mos` ณ วันที่ทดสอบ
- **THEN** excess return ของวันนั้นคือค่าเฉลี่ยของผลตอบแทนรวมปันผล 63 วันของกลุ่มนั้น ลบค่าเฉลี่ยของหุ้นทุกตัวที่ประเมินได้ในวันเดียวกัน และรายงานค่าเฉลี่ยกับ median ของทุกวันที่ทดสอบ พร้อม % ของวันที่เป็นบวก

#### Scenario: bucket ของ MoS
- **WHEN** รายงานผลของ method, median MoS หรือ MoS gate
- **THEN** แสดงจำนวน, median ผลตอบแทน 63 วัน และ median excess return ของแต่ละ bucket: MoS < 0, 0–10%, 10–30%, ≥ 30%

#### Scenario: method คำนวณไม่ได้
- **WHEN** method ให้ fair value เป็น None ณ วันที่ทดสอบ
- **THEN** การประเมินนั้นไม่ถูกนับใน method นั้น และรายงานจำนวนที่คำนวณไม่ได้แยกไว้

### Requirement: ผลรวมแบบไม่นับค่าผิดปกติ
ไฟล์ผล SHALL มีตารางผลรวมชุดที่สองที่ตัดการประเมินผิดปกติ (MoS < −100% หรือ fair value > 5× ราคา) ออกจากกลุ่มของ method นั้นก่อนคิดตัววัด โดย baseline ของแต่ละวันยังเป็นค่าเฉลี่ยของหุ้นทุกตัวที่ประเมินได้ ตารางผลรวมเดิมยังนับค่าผิดปกติทุกตัว

#### Scenario: fair value เกิน 5 เท่าของราคา
- **WHEN** method ให้ fair value มากกว่า 5 เท่าของราคากับหุ้นตัวหนึ่ง ณ วันที่ทดสอบ
- **THEN** การประเมินนั้นนับในตารางผลรวมเดิม แต่ไม่นับในตารางแบบไม่นับค่าผิดปกติของ method นั้น และหุ้นตัวนั้นยังนับใน baseline ของวันนั้น

#### Scenario: median ผิดปกติ
- **WHEN** median fair value ของหุ้นตัวหนึ่งผิดปกติ
- **THEN** การประเมินนั้นไม่นับในกลุ่ม median, candidate (median) และ candidate (relative) ของตารางแบบไม่นับค่าผิดปกติ

#### Scenario: fair value ของ gate ผิดปกติ
- **WHEN** fair value ที่ต่ำกว่าของ gate methods ของหุ้นตัวหนึ่งผิดปกติ
- **THEN** การประเมินนั้นไม่นับในกลุ่ม MoS gate และ candidate ของตารางแบบไม่นับค่าผิดปกติ

### Requirement: candidate แบบ relative
backtest SHALL วัดกลุ่ม candidate (relative) คือหุ้นที่ผ่าน quality gate และ median MoS อยู่ใน 20% บนของหุ้นที่มี median MoS ณ วันที่ทดสอบเดียวกัน ไม่มีเกณฑ์ MoS ขั้นต่ำ ด้วยตัววัด excess และแถวสลับ MoS เดียวกับกลุ่ม candidate กลุ่มนี้มีใน backtest เท่านั้นเป็นค่าอ้างอิง ไม่มีผลกับ batch หรือ candidate list

#### Scenario: เลือก 20% บน
- **WHEN** วันที่ทดสอบมีหุ้น 100 ตัวที่มี median MoS
- **THEN** หุ้นที่ median MoS อยู่ในอันดับ 1–20 และผ่าน quality gate อยู่ในกลุ่ม candidate (relative) ของวันนั้น ไม่ว่า median MoS จะเป็นบวกหรือลบ

#### Scenario: สัดส่วน candidate ต่อวันที่
- **WHEN** รายงานผลต่อวันที่ทดสอบ
- **THEN** ตารางต่อวันที่แสดงจำนวนและสัดส่วนต่อหุ้นที่ประเมินได้ของ candidate, candidate (median) และ candidate (relative)

#### Scenario: batch ไม่เปลี่ยน
- **WHEN** รัน batch
- **THEN** candidate list ใช้ gate ด้าน fair value ตาม `candidates.gate_methods` ไม่ใช้กลุ่ม relative

## ADDED Requirements

### Requirement: แถวเทียบ candidate rule เดิม
backtest SHALL วัดกลุ่ม candidate (median) คือหุ้นที่ผ่าน quality gate และ median MoS ≥ `candidates.min_gate_mos` (rule ก่อน change นี้) ด้วยตัววัดเดียวกับกลุ่ม candidate ในทุกตาราง ได้แก่ hit rate, excess, t-stat และช่วงความเชื่อมั่น, แถวสลับ MoS, ตารางแบบไม่นับค่าผิดปกติ และตารางต่อระยะ 63, 126 และ 252 วัน เพื่อดูว่า rule ใหม่ยังดีกว่า rule เดิมนอกช่วงที่ใช้เลือก method กลุ่มนี้มีใน backtest เท่านั้น

#### Scenario: เทียบสอง rule
- **WHEN** backtest รันจบ
- **THEN** ตารางผลรวมมีแถว candidate และ candidate (median) ติดกัน พร้อม excess, t-stat และช่วงความเชื่อมั่น 95% ของทั้งสองแถว

#### Scenario: ผลซ้ำกับ rule เดิม
- **WHEN** รัน backtest หลัง change นี้ด้วย cache และค่าเกณฑ์เดียวกับรอบ 2026-10-15
- **THEN** ตัวเลขของแถว candidate (median) เท่ากับแถว candidate ของไฟล์ผลรอบนั้น
