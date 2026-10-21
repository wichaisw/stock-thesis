# Spec Delta

## MODIFIED Requirements

### Requirement: Liquidity filter
ระบบ SHALL ตัดหุ้นที่ค่าเฉลี่ย traded value (ราคาปิด × volume) 20 วันทำการล่าสุดต่ำกว่าเกณฑ์ (default 10 ล้านบาท/วัน) หุ้นที่ไม่ผ่าน filter SHALL ไม่ถูกดึงงบ ยกเว้นหุ้นที่อยู่ในรายการหุ้นที่ถือ ซึ่ง SHALL ถูกดึงงบและประเมิน quality gate และ fair value panel ตามปกติ แต่ยังไม่ผ่าน liquidity filter และไม่เข้า candidate list

#### Scenario: หุ้นสภาพคล่องต่ำ
- **WHEN** ค่าเฉลี่ย traded value 20 วันของหุ้นคือ 4 ล้านบาท/วัน และเกณฑ์คือ 10 ล้านบาท/วัน
- **THEN** หุ้นไม่ผ่าน liquidity filter พร้อมเหตุผลที่ระบุค่าจริงและเกณฑ์

#### Scenario: หุ้นที่ถือสภาพคล่องต่ำ
- **WHEN** หุ้นที่ถือมีค่าเฉลี่ย traded value 20 วันคือ 2 ล้านบาท/วัน และเกณฑ์คือ 3 ล้านบาท/วัน
- **THEN** batch ดึงงบของหุ้นนั้น หุ้นนั้นมีผล quality gate และ fair value panel แต่ไม่ผ่าน liquidity filter และไม่อยู่ใน candidate list
