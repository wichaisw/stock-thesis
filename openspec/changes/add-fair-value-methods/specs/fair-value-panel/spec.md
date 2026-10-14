# Spec Delta

## MODIFIED Requirements

### Requirement: Fair value แยกตามเกณฑ์
ระบบ SHALL คำนวณ fair value ของแต่ละหุ้นตามเกณฑ์ที่เปิดใช้ใน config: PE band (median 5 ปี และ median − 1SD), PBV band (median 5 ปี), dividend yield band (median 5 ปี), peer PE (median ของ sector เดียวกัน), EV/EBITDA band (median 5 ปี) และ Justified PBV

#### Scenario: คำนวณครบทุกเกณฑ์
- **WHEN** หุ้นไม่ใช่หุ้นการเงิน มีงบและราคาย้อนหลัง 5 ปี เคยจ่ายปันผล มี EBITDA บวก มี ROE สูงกว่า g และมีหุ้นอื่นใน sector เดียวกัน
- **THEN** ผลการประเมินมี fair value ของทั้ง 7 รายการ

#### Scenario: ปิดบางเกณฑ์ใน config
- **WHEN** ผู้ใช้ปิดเกณฑ์ dividend yield band ใน config
- **THEN** panel ไม่แสดงเกณฑ์นั้น และไม่นำไปคิดในสรุป

### Requirement: สรุปของ panel
ระบบ SHALL แสดงสรุปของ panel ได้แก่ จำนวนมุมมองที่บอกว่า undervalued เทียบกับจำนวนมุมมองที่คำนวณได้, margin of safety ต่ำสุด, median และสูงสุด โดย PE band (median) และ PE band (median − 1SD) SHALL นับเป็นมุมมองเดียว ซึ่งนับว่า undervalued เมื่อค่าเฉลี่ย margin of safety ของรายการที่คำนวณได้ในมุมมองนั้นเป็นบวก ทุกเกณฑ์อื่นนับเป็นหนึ่งมุมมอง margin of safety ต่ำสุด, median และสูงสุด SHALL คิดจากทุกเกณฑ์ที่คำนวณได้ ไม่รวมมุมมอง

#### Scenario: แสดงสรุป
- **WHEN** คำนวณได้ 7 เกณฑ์ และทุกเกณฑ์มี margin of safety เป็นบวกยกเว้น peer PE
- **THEN** สรุปแสดง "5/6 undervalued" พร้อม margin of safety ต่ำสุด, median และสูงสุดจากทั้ง 7 เกณฑ์

#### Scenario: PE สองเส้นเห็นต่างกัน
- **WHEN** PE band (median) มี margin of safety +20% และ PE band (median − 1SD) มี −10%
- **THEN** มุมมอง PE band นับเป็น undervalued หนึ่งมุมมอง (ค่าเฉลี่ย +5%)

#### Scenario: คำนวณได้แค่ PE − 1SD
- **WHEN** ผู้ใช้ปิด PE band (median) และ PE band (median − 1SD) มี margin of safety +8%
- **THEN** มุมมอง PE band นับเป็น undervalued จาก PE − 1SD อย่างเดียว

## ADDED Requirements

### Requirement: EV/EBITDA band
ระบบ SHALL คำนวณ fair value ของเกณฑ์ EV/EBITDA band เป็น (median ของ EV/EBITDA TTM รายไตรมาสในกรอบ 5 ปี × EBITDA TTM ล่าสุด − หนี้สุทธิล่าสุด) ÷ จำนวนหุ้นล่าสุด โดย EV = market cap ตาม spec `market-data` + หนี้ − เงินสด และหนี้สุทธิ = หนี้ − เงินสด ระบบ SHALL ตัด EV/EBITDA ที่ไม่เป็นบวกหรือสูงกว่าเกณฑ์ใน config (default 50) ออกก่อนหา median

#### Scenario: หุ้นมีหนี้สุทธิ
- **WHEN** median EV/EBITDA 5 ปีคือ 8 เท่า, EBITDA TTM 1,000 ล้านบาท, หนี้สุทธิ 2,000 ล้านบาท และจำนวนหุ้น 600 ล้านหุ้น
- **THEN** fair value ของ EV/EBITDA band คือ 10.00 บาท

#### Scenario: EBITDA ใกล้ศูนย์บางไตรมาส
- **WHEN** EV/EBITDA ย้อนหลังมีไตรมาสหนึ่งเป็น 180 เท่า เพราะ EBITDA TTM ใกล้ศูนย์
- **THEN** ค่านั้นไม่ถูกนำไปคิด median

### Requirement: EV/EBITDA band ที่คำนวณไม่ได้
ระบบ SHALL แสดงเกณฑ์ EV/EBITDA band เป็น N/A พร้อมเหตุผล เมื่อหุ้นอยู่ใน sector การเงินตาม config ของ quality gate, เมื่อ EBITDA TTM ล่าสุดไม่เป็นบวก, เมื่อจุด EV/EBITDA ที่ใช้ได้น้อยกว่าจำนวนจุดขั้นต่ำใน config หรือเมื่อ fair value ที่ได้ไม่เป็นบวกเพราะหนี้สุทธิมากกว่ามูลค่ากิจการ

#### Scenario: หุ้นธนาคาร
- **WHEN** หุ้นอยู่ใน sector Banking
- **THEN** เกณฑ์ EV/EBITDA band แสดงเป็น N/A ด้วยเหตุผลว่าไม่ใช้กับหุ้นการเงิน

#### Scenario: หนี้สุทธิสูงกว่ามูลค่ากิจการ
- **WHEN** median EV/EBITDA × EBITDA TTM คือ 3,000 ล้านบาท และหนี้สุทธิคือ 3,500 ล้านบาท
- **THEN** เกณฑ์ EV/EBITDA band แสดงเป็น N/A ด้วยเหตุผลว่าหนี้สุทธิมากกว่ามูลค่ากิจการ

### Requirement: Justified PBV
ระบบ SHALL คำนวณ fair value ของเกณฑ์ Justified PBV เป็น (ROE − g) ÷ (r − g) × ส่วนผู้ถือหุ้นล่าสุด ÷ จำนวนหุ้นล่าสุด โดย ROE คือ ROE TTM ตัวเดียวกับที่ quality gate ใช้ r คือ cost of equity และ g คือ growth ระยะยาว ค่า default r = 10% และ g = 3% ปรับได้ใน config และ SHALL ไม่ยอมให้ตั้ง g ≥ r ระบบ SHALL แสดงเกณฑ์นี้เป็น N/A พร้อมเหตุผลเมื่อคำนวณ ROE TTM ไม่ได้หรือ ROE TTM ≤ g

#### Scenario: ROE สูงกว่า cost of equity
- **WHEN** ROE TTM คือ 17%, r = 10%, g = 3% และส่วนผู้ถือหุ้นต่อหุ้นล่าสุดคือ 10.00 บาท
- **THEN** fair value ของ Justified PBV คือ 20.00 บาท (PBV 2 เท่า)

#### Scenario: ROE ต่ำกว่า g
- **WHEN** ROE TTM คือ 2% และ g = 3%
- **THEN** เกณฑ์ Justified PBV แสดงเป็น N/A ด้วยเหตุผลว่า ROE ไม่สูงกว่า g

#### Scenario: ตั้ง g ไม่น้อยกว่า r
- **WHEN** ผู้ใช้ตั้ง g = 10% และ r = 10% ในหน้า settings
- **THEN** ระบบไม่บันทึกค่าและแจ้งว่า g ต้องน้อยกว่า r

#### Scenario: หุ้นการเงิน
- **WHEN** หุ้นอยู่ใน sector Banking และ ROE TTM คือ 12%
- **THEN** เกณฑ์ Justified PBV คำนวณได้ตามปกติ
