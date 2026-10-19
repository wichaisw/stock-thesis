# Spec Delta

## ADDED Requirements

### Requirement: variant ของ candidate rule
backtest SHALL วัดกลุ่ม variant ของ candidate rule ที่ต่างจากกลุ่ม candidate ทีละอย่าง: min MoS ของ gate 15%, 20% และ 25%; Option A (gate method ตัวหนึ่ง MoS ≥ 15% และอีกตัว ≥ −10% ถ้าคำนวณได้ตัวเดียวต้อง ≥ 12%); Option B (ต้องคำนวณได้ทั้งสองตัว ค่าเฉลี่ย MoS ≥ 8% และไม่มีตัวไหน < −15%); quality ที่ทุกเกณฑ์ต้องผ่าน; และ quality ที่ทุกเกณฑ์ต้องผ่านพร้อม D/E ≤ 2.0 ทุก variant SHALL ใช้ตัววัด, baseline และแถวสลับ MoS เดียวกับกลุ่ม candidate และมีใน backtest เท่านั้น

#### Scenario: Option A ผ่านด้วย method ที่ MoS ติดลบ
- **WHEN** หุ้นผ่าน quality, peer PE MoS 20% และ Justified PBV MoS −5%
- **THEN** หุ้นอยู่ในกลุ่ม Option A แต่ไม่อยู่ในกลุ่ม candidate

#### Scenario: Option A คำนวณได้ตัวเดียว
- **WHEN** หุ้นผ่าน quality, peer PE คำนวณไม่ได้ และ Justified PBV MoS 11%
- **THEN** หุ้นไม่อยู่ในกลุ่ม Option A แต่อยู่ในกลุ่ม candidate

#### Scenario: Option B คำนวณได้ตัวเดียว
- **WHEN** หุ้นผ่าน quality และคำนวณได้ gate method ตัวเดียวที่ MoS 30%
- **THEN** หุ้นไม่อยู่ในกลุ่ม Option B

#### Scenario: Option B ค่าเฉลี่ยผ่านแต่มีตัวที่ติดลบมาก
- **WHEN** หุ้นผ่าน quality, peer PE MoS 40% และ Justified PBV MoS −20%
- **THEN** หุ้นไม่อยู่ในกลุ่ม Option B

#### Scenario: quality ที่ทุกเกณฑ์ต้องผ่าน
- **WHEN** หุ้นไม่ผ่านเกณฑ์ OCF ข้อเดียว และผ่าน gate ด้าน fair value
- **THEN** หุ้นอยู่ในกลุ่ม candidate แต่ไม่อยู่ในกลุ่ม quality ที่ทุกเกณฑ์ต้องผ่าน

#### Scenario: D/E 2.0
- **WHEN** หุ้นที่ไม่ใช่กลุ่มการเงินมี D/E 1.8, ผ่านเกณฑ์ quality อื่นทุกข้อ และผ่าน gate ด้าน fair value
- **THEN** หุ้นอยู่ในกลุ่ม quality ทุกเกณฑ์ + D/E ≤ 2.0 แต่ไม่อยู่ในกลุ่ม quality ที่ทุกเกณฑ์ต้องผ่าน

#### Scenario: batch ไม่ใช้ variant
- **WHEN** รัน batch
- **THEN** candidate list ใช้ quality gate และ gate ด้าน fair value ตาม `engine/config.yaml` ไม่ใช้ variant ใด

### Requirement: ตาราง variant แยกสองช่วงเวลา
ไฟล์ผล SHALL มีตาราง variant ที่แสดงกลุ่ม candidate และทุก variant แยกสองช่วง: วันที่ทดสอบ 2021Q1–2023Q4 และ 2024Q1 ถึงวันที่ทดสอบสุดท้าย แต่ละแถวแต่ละช่วง SHALL มี excess เฉลี่ย 63 วัน, ช่วงความเชื่อมั่น 95%, t-stat, จำนวนวันที่, จำนวน candidate เฉลี่ยต่อวันที่ และจำนวนวันที่ที่ไม่มี candidate ไฟล์ผล SHALL ระบุว่าการแบ่งช่วงนี้เป็นความคงที่ข้ามช่วง ไม่ใช่ out-of-sample

#### Scenario: ช่วงที่ variant ไม่มี candidate
- **WHEN** variant MoS 25% ไม่มีหุ้นเลยในวันที่ทดสอบหนึ่ง
- **THEN** วันที่นั้นไม่นับใน excess ของ variant และนับในคอลัมน์จำนวนวันที่ที่ไม่มี candidate

#### Scenario: กลุ่ม candidate ในตาราง variant
- **WHEN** รายงานตาราง variant
- **THEN** แถว candidate ของทั้งสองช่วงรวมกันใช้วันที่ชุดเดียวกับแถว candidate ของตารางผลรวม

### Requirement: ผลต่างจับคู่ของ variant
ตาราง variant SHALL แสดงผลต่าง excess 63 วันต่อวันที่ของแต่ละ variant ลบกลุ่ม candidate โดยนับเฉพาะวันที่ที่มีทั้งสองกลุ่ม พร้อมค่าเฉลี่ยและช่วงความเชื่อมั่น 95% ทั้งช่วง เป็นข้อมูลประกอบ ไม่ใช่ส่วนของเกณฑ์ตัดสิน

#### Scenario: วันที่ที่มีกลุ่มเดียว
- **WHEN** วันที่ทดสอบหนึ่งมีหุ้นในกลุ่ม candidate แต่ไม่มีในกลุ่ม variant
- **THEN** วันที่นั้นไม่นับในผลต่างจับคู่ของ variant นั้น

### Requirement: เกณฑ์ตัดสิน variant ที่ตั้งไว้ล่วงหน้า
ตาราง variant SHALL มีคอลัมน์บอกว่า variant ผ่านเกณฑ์หรือไม่ variant ผ่านเมื่อ excess เฉลี่ย 63 วันสูงกว่ากลุ่ม candidate ในทั้งสองช่วง ขอบล่างของช่วงความเชื่อมั่น 95% ของ excess เฉลี่ยทั้งช่วงของ variant มากกว่า 0 และ variant มี candidate เฉลี่ยอย่างน้อย 3 ตัวต่อวันที่และมี candidate อย่างน้อย 80% ของวันที่ทดสอบ โดยคิดจากผลที่นับค่าผิดปกติ ผลนี้ SHALL ไม่เปลี่ยนค่าใน `engine/config.yaml`

#### Scenario: variant ชนะช่วงเดียว
- **WHEN** variant มี excess สูงกว่ากลุ่ม candidate ในช่วง 2024–2026 แต่ต่ำกว่าในช่วง 2021–2023
- **THEN** คอลัมน์เกณฑ์ของ variant นั้นแสดงว่าไม่ผ่าน

#### Scenario: variant ชนะทั้งสองช่วงแต่ CI คร่อม 0
- **WHEN** variant มี excess สูงกว่ากลุ่ม candidate ทั้งสองช่วง และช่วงความเชื่อมั่นทั้งช่วงคือ −0.5% ถึง +4%
- **THEN** คอลัมน์เกณฑ์ของ variant นั้นแสดงว่าไม่ผ่าน

#### Scenario: variant ชนะแต่ candidate น้อยเกินไป
- **WHEN** variant ชนะกลุ่ม candidate ทั้งสองช่วงและขอบล่างของช่วงความเชื่อมั่นมากกว่า 0 แต่มี candidate เฉลี่ย 1.5 ตัวต่อวันที่
- **THEN** คอลัมน์เกณฑ์ของ variant นั้นแสดงว่าไม่ผ่าน พร้อมเหตุผลว่า candidate น้อยเกินไป

#### Scenario: variant ผ่านเกณฑ์
- **WHEN** variant มี excess สูงกว่ากลุ่ม candidate ทั้งสองช่วง, ขอบล่างของช่วงความเชื่อมั่นทั้งช่วงมากกว่า 0, candidate เฉลี่ย 6 ตัวต่อวันที่ และมี candidate 21 จาก 22 วันที่
- **THEN** คอลัมน์เกณฑ์แสดงว่าผ่าน และ `engine/config.yaml` ไม่เปลี่ยน

### Requirement: ผลเดิมไม่เปลี่ยนเมื่อเพิ่ม variant
การเพิ่มกลุ่ม variant SHALL ไม่เปลี่ยนตัวเลขของกลุ่มที่มีอยู่ก่อน (แต่ละ method, median, gate, candidate, candidate (median), candidate (relative)) ในทุกตาราง

#### Scenario: รันด้วย cache เดิม
- **WHEN** รัน backtest ด้วย cache และ `engine/config.yaml` เดียวกับรอบก่อนเพิ่ม variant
- **THEN** ทุกแถวของกลุ่มเดิมในทุกตารางเท่ากับรอบก่อน
