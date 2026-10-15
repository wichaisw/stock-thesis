# fair-value-panel Specification

## Purpose

แสดง fair value และ margin of safety แยกตามแต่ละเกณฑ์ valuation เพื่อให้ผู้ใช้เห็นว่าหุ้นถูกตามเกณฑ์ไหนบ้าง แทนการสรุปเป็นตัวเลขเดียว

## Requirements

### Requirement: Fair value แยกตามเกณฑ์
ระบบ SHALL คำนวณ fair value ของแต่ละหุ้นตามเกณฑ์ที่เปิดใช้ใน config: PE band (median 5 ปี และ median − 1SD), PBV band (median 5 ปี), dividend yield band (median 5 ปี), peer PE (median ของ sector เดียวกัน) และ Justified PBV

#### Scenario: คำนวณครบทุกเกณฑ์
- **WHEN** หุ้นมีงบและราคาย้อนหลัง 5 ปี เคยจ่ายปันผล มี ROE สูงกว่า g และมีหุ้นอื่นใน sector เดียวกัน
- **THEN** ผลการประเมินมี fair value ของทั้ง 6 รายการ

#### Scenario: ปิดบางเกณฑ์ใน config
- **WHEN** ผู้ใช้ปิดเกณฑ์ dividend yield band ใน config
- **THEN** panel ไม่แสดงเกณฑ์นั้น และไม่นำไปคิดในสรุป

### Requirement: PE และ PBV ระดับบริษัท
ระบบ SHALL คำนวณ PE ย้อนหลังและ peer PE จาก market cap ÷ กำไรสุทธิ 4 ไตรมาส และ PBV จาก market cap ÷ ส่วนผู้ถือหุ้น โดยใช้ market cap รายไตรมาสตาม spec `market-data` (ราคาปิดจริง × จำนวนหุ้น ณ ไตรมาสนั้น) แล้วแปลงเป็นราคาต่อหุ้นด้วยจำนวนหุ้นล่าสุด ระบบ SHALL ไม่ใช้ราคา, PE, PBV หรือค่าต่อหุ้นย้อนหลังจากแหล่งงบการเงิน เพื่อไม่ให้การปรับราคาตามปันผล การแตกพาร์ หรือการเพิ่มทุนทำให้ band เพี้ยน และ SHALL ตัด PE ที่สูงกว่าเกณฑ์ใน config (default 100) ออกก่อนคำนวณ PE band

#### Scenario: หุ้นแตกพาร์
- **WHEN** หุ้นแตกพาร์ระหว่างกรอบ 5 ปี และแหล่งข้อมูลปรับราคาย้อนหลังแต่ไม่ปรับ BVPS
- **THEN** PE และ PBV ย้อนหลังไม่เปลี่ยนไปจากกรณีที่ไม่มีการแตกพาร์

#### Scenario: หุ้นเพิ่มทุน
- **WHEN** หุ้นเพิ่มทุนทำให้จำนวนหุ้นเพิ่ม 20%
- **THEN** fair value ต่อหุ้นคำนวณจากจำนวนหุ้นหลังเพิ่มทุน

#### Scenario: PE ย้อนหลังมีค่าผิดปกติ
- **WHEN** PE ย้อนหลังมีไตรมาสหนึ่งเป็น 400 เพราะกำไร 4 ไตรมาสใกล้ศูนย์
- **THEN** PE ค่านั้นไม่ถูกนำไปคิด PE band

#### Scenario: แหล่งงบให้ราคาย้อนหลังที่ปรับตามปันผล
- **WHEN** แหล่งงบให้ราคาปิดของไตรมาสเก่าเป็น 32.29 บาท แต่ราคาปิดจริงคือ 41.00 บาท
- **THEN** PE และ PBV ของไตรมาสนั้นคำนวณจาก market cap ที่ใช้ราคา 41.00 บาท

### Requirement: ป้ายเตือนข้อมูลย้อนหลังไม่ครบ
ระบบ SHALL ข้ามไตรมาสที่ไม่มี market cap เมื่อคำนวณ PE และ PBV band และ SHALL ติดป้ายเตือนข้อมูลย้อนหลังไม่ครบ พร้อมจำนวนไตรมาสที่ใช้ได้เทียบกับกรอบ 5 ปี ป้ายนี้ SHALL แสดงใน fair value panel และใน candidate list และ SHALL ไม่ใช้คัดหุ้นออก ถ้าไม่มีไตรมาสใดมี market cap เกณฑ์ PE band และ PBV band SHALL เป็น N/A พร้อมเหตุผล

#### Scenario: ไม่มีจำนวนหุ้นบางไตรมาส
- **WHEN** หุ้นมี market cap เพียง 6 จาก 20 ไตรมาสในกรอบ 5 ปี เพราะแหล่งข้อมูลไม่มีจำนวนหุ้นก่อนเปลี่ยนชื่อ
- **THEN** PE และ PBV band คำนวณจาก 6 ไตรมาสนั้น และหุ้นถูกติดป้ายเตือนว่าข้อมูลย้อนหลังมี 6/20 ไตรมาส

#### Scenario: ไม่มี market cap เลย
- **WHEN** ไม่มีไตรมาสใดในกรอบ 5 ปีที่มี market cap
- **THEN** เกณฑ์ PE band และ PBV band แสดงเป็น N/A ด้วยเหตุผลว่าไม่มี market cap ย้อนหลัง

### Requirement: Margin of safety รายเกณฑ์
ระบบ SHALL คำนวณ margin of safety ของแต่ละเกณฑ์เป็น (fair value − ราคาปัจจุบัน) / fair value

#### Scenario: ราคาต่ำกว่า fair value
- **WHEN** fair value ตาม PE band คือ 15.20 บาท และราคาปัจจุบันคือ 12.40 บาท
- **THEN** margin of safety ของเกณฑ์นั้นคือประมาณ +18%

### Requirement: เกณฑ์ที่คำนวณไม่ได้
ระบบ SHALL แสดงเกณฑ์ที่คำนวณไม่ได้เป็น N/A พร้อมเหตุผล และ SHALL ไม่นำเกณฑ์นั้นไปคิดในสรุป

#### Scenario: กำไร 4 ไตรมาสติดลบ
- **WHEN** กำไรสุทธิรวม 4 ไตรมาสล่าสุดติดลบ
- **THEN** เกณฑ์ PE band และ peer PE แสดงเป็น N/A ด้วยเหตุผลว่ากำไร 4 ไตรมาสติดลบ

#### Scenario: ไม่เคยจ่ายปันผล
- **WHEN** หุ้นไม่มี dividend yield ในช่วง 5 ปี
- **THEN** เกณฑ์ dividend yield band แสดงเป็น N/A

### Requirement: ป้ายเตือนโครงสร้างทุนเปลี่ยน
ระบบ SHALL ติดป้ายเตือนเมื่อส่วนผู้ถือหุ้นเปลี่ยนเกินเกณฑ์ (default 50%) ระหว่างไตรมาสที่ติดกันในกรอบ 5 ปีที่ใช้คำนวณ band เพราะธุรกิจหลังจากนั้นอาจต่างจากเดิม เช่น ควบรวมหรือเพิ่มทุนก้อนใหญ่ ทำให้ band ย้อนหลังอาจไม่สะท้อนธุรกิจปัจจุบัน ป้ายนี้ SHALL แสดงใน fair value panel และใน candidate list พร้อมไตรมาสและขนาดการเปลี่ยนแปลง และ SHALL ไม่ใช้คัดหุ้นออก ค่าเกณฑ์ SHALL ปรับได้ใน config

#### Scenario: หุ้นควบรวมกิจการ
- **WHEN** ส่วนผู้ถือหุ้นเพิ่มขึ้น 173% ในไตรมาสเดียวภายในกรอบ 5 ปี
- **THEN** หุ้นถูกติดป้ายเตือนโครงสร้างทุนเปลี่ยนพร้อมระบุไตรมาสนั้น และยังอยู่ใน candidate list ได้ถ้าผ่านเงื่อนไขอื่น

#### Scenario: แตกพาร์
- **WHEN** หุ้นแตกพาร์แต่ส่วนผู้ถือหุ้นแทบไม่เปลี่ยน
- **THEN** หุ้นไม่ถูกติดป้ายเตือน

### Requirement: สรุปของ panel
ระบบ SHALL แสดงสรุปของ panel ได้แก่ จำนวนมุมมองที่บอกว่า undervalued เทียบกับจำนวนมุมมองที่คำนวณได้, margin of safety ต่ำสุด, median และสูงสุด โดย PE band (median) และ PE band (median − 1SD) SHALL นับเป็นมุมมองเดียว ซึ่งนับว่า undervalued เมื่อค่าเฉลี่ย margin of safety ของรายการที่คำนวณได้ในมุมมองนั้นเป็นบวก ทุกเกณฑ์อื่นนับเป็นหนึ่งมุมมอง margin of safety ต่ำสุด, median และสูงสุด SHALL คิดจากทุกเกณฑ์ที่คำนวณได้ ไม่รวมมุมมอง

#### Scenario: แสดงสรุป
- **WHEN** คำนวณได้ 6 เกณฑ์ และทุกเกณฑ์มี margin of safety เป็นบวกยกเว้น peer PE
- **THEN** สรุปแสดง "4/5 undervalued" พร้อม margin of safety ต่ำสุด, median และสูงสุดจากทั้ง 6 เกณฑ์

#### Scenario: PE สองเส้นเห็นต่างกัน
- **WHEN** PE band (median) มี margin of safety +20% และ PE band (median − 1SD) มี −10%
- **THEN** มุมมอง PE band นับเป็น undervalued หนึ่งมุมมอง (ค่าเฉลี่ย +5%)

#### Scenario: คำนวณได้แค่ PE − 1SD
- **WHEN** ผู้ใช้ปิด PE band (median) และ PE band (median − 1SD) มี margin of safety +8%
- **THEN** มุมมอง PE band นับเป็น undervalued จาก PE − 1SD อย่างเดียว

### Requirement: Dividend yield band จากปันผลเงินสด
ระบบ SHALL คำนวณ fair value ของเกณฑ์ dividend yield band เป็นปันผลเงินสดต่อหุ้น 12 เดือนล่าสุด (ฐานจำนวนหุ้นปัจจุบัน) ÷ median ของ dividend yield 12 เดือนรายไตรมาสในกรอบ 5 ปีตาม spec `market-data`

#### Scenario: หุ้นจ่ายปันผลสม่ำเสมอ
- **WHEN** ปันผลเงินสด 12 เดือนล่าสุดคือ 2.80 บาทต่อหุ้น และ median ของ dividend yield 12 เดือนในกรอบ 5 ปีคือ 5.0%
- **THEN** fair value ของ dividend yield band คือ 56.00 บาท

### Requirement: ไม่นับไตรมาสที่ yield ต่ำกว่าเกณฑ์
ระบบ SHALL ไม่นำไตรมาสที่ dividend yield 12 เดือนต่ำกว่าเกณฑ์ใน config (default 0.5%) ไปคิด median ของ dividend yield band เพราะถือว่าไตรมาสนั้นไม่ได้จ่ายปันผลเงินสดอย่างมีนัย ถ้าไตรมาสที่เหลือน้อยกว่าจำนวนจุดขั้นต่ำใน config เกณฑ์นี้ SHALL เป็น N/A พร้อมเหตุผลที่ระบุจำนวนไตรมาสที่ใช้ได้

#### Scenario: ช่วงที่จ่ายปันผลเป็นหุ้น
- **WHEN** หุ้นมี dividend yield 12 เดือนต่ำกว่า 0.1% อยู่ 7 ไตรมาสเพราะช่วงนั้นจ่ายปันผลเป็นหุ้น และอีก 10 ไตรมาสมี yield 1.1–4.6%
- **THEN** median ของ band คิดจาก 10 ไตรมาสนั้นเท่านั้น

#### Scenario: จ่ายปันผลเป็นหุ้นทุกปี
- **WHEN** ทุกไตรมาสในกรอบ 5 ปีมี dividend yield 12 เดือนต่ำกว่าเกณฑ์
- **THEN** เกณฑ์ dividend yield band แสดงเป็น N/A พร้อมเหตุผลว่าไม่มีไตรมาสที่จ่ายปันผลเงินสดถึงเกณฑ์

### Requirement: ต้องจ่ายปันผลเงินสดใน 12 เดือนล่าสุด
ระบบ SHALL แสดงเกณฑ์ dividend yield band เป็น N/A เมื่อ dividend yield 12 เดือนของไตรมาสล่าสุดต่ำกว่าเกณฑ์ใน config เพราะไม่มีปันผลปัจจุบันให้แปลงเป็น fair value

#### Scenario: หยุดจ่ายปันผล
- **WHEN** หุ้นเคยจ่ายปันผลเงินสด 12 ไตรมาสในกรอบ 5 ปี แต่ไม่มี XD ปันผลเงินสดใน 12 เดือนล่าสุด
- **THEN** เกณฑ์ dividend yield band แสดงเป็น N/A ด้วยเหตุผลว่าไม่ได้จ่ายปันผลเงินสดใน 12 เดือนล่าสุด

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
