# Spec Delta

## Purpose

แสดง fair value และ margin of safety แยกตามแต่ละเกณฑ์ valuation เพื่อให้ผู้ใช้เห็นว่าหุ้นถูกตามเกณฑ์ไหนบ้าง แทนการสรุปเป็นตัวเลขเดียว

## ADDED Requirements

### Requirement: Fair value แยกตามเกณฑ์
ระบบ SHALL คำนวณ fair value ของแต่ละหุ้นตามเกณฑ์ที่เปิดใช้ใน config: PE band (ค่าเฉลี่ย 5 ปี และ ค่าเฉลี่ย − 1SD), PBV band (ค่าเฉลี่ย 5 ปี), dividend yield band (ค่าเฉลี่ย 5 ปี) และ peer PE (median ของ sector เดียวกัน)

#### Scenario: คำนวณครบทุกเกณฑ์
- **WHEN** หุ้นมีข้อมูล PE, PBV, BVPS, dividend yield ย้อนหลัง 5 ปี และมีหุ้นอื่นใน sector เดียวกัน
- **THEN** ผลการประเมินมี fair value ของทั้ง 5 รายการ

#### Scenario: ปิดบางเกณฑ์ใน config
- **WHEN** ผู้ใช้ปิดเกณฑ์ dividend yield band ใน config
- **THEN** panel ไม่แสดงเกณฑ์นั้น และไม่นำไปคิดในสรุป

### Requirement: Margin of safety รายเกณฑ์
ระบบ SHALL คำนวณ margin of safety ของแต่ละเกณฑ์เป็น (fair value − ราคาปัจจุบัน) / fair value

#### Scenario: ราคาต่ำกว่า fair value
- **WHEN** fair value ตาม PE band คือ 15.20 บาท และราคาปัจจุบันคือ 12.40 บาท
- **THEN** margin of safety ของเกณฑ์นั้นคือประมาณ +18%

### Requirement: เกณฑ์ที่คำนวณไม่ได้
ระบบ SHALL แสดงเกณฑ์ที่คำนวณไม่ได้เป็น N/A พร้อมเหตุผล และ SHALL ไม่นำเกณฑ์นั้นไปคิดในสรุป

#### Scenario: EPS TTM ติดลบ
- **WHEN** ผลรวม EPS 4 ไตรมาสล่าสุดติดลบ
- **THEN** เกณฑ์ PE band และ peer PE แสดงเป็น N/A ด้วยเหตุผลว่า EPS TTM ติดลบ

#### Scenario: ไม่เคยจ่ายปันผล
- **WHEN** หุ้นไม่มี dividend yield ในช่วง 5 ปี
- **THEN** เกณฑ์ dividend yield band แสดงเป็น N/A

### Requirement: สรุปของ panel
ระบบ SHALL แสดงสรุปของ panel ได้แก่ จำนวนเกณฑ์ที่บอกว่า undervalued เทียบกับจำนวนเกณฑ์ที่คำนวณได้, margin of safety ต่ำสุด, median และสูงสุด

#### Scenario: แสดงสรุป
- **WHEN** คำนวณได้ 5 เกณฑ์ และ 4 เกณฑ์มี margin of safety เป็นบวก
- **THEN** สรุปแสดง "4/5 undervalued" พร้อม margin of safety ต่ำสุด, median และสูงสุด
