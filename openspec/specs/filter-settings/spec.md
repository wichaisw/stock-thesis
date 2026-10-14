# filter-settings Specification

## Purpose

ให้ผู้ใช้ดูและปรับเกณฑ์กรองและจัดอันดับหุ้นได้จากหน้าเว็บ พร้อมคำอธิบายภาษาไทยว่าแต่ละค่ากระทบผลอย่างไร โดยไม่ต้องแก้ไฟล์ config เอง

## Requirements

### Requirement: หน้า settings แสดงเกณฑ์ทั้งหมด
ระบบ SHALL มีหน้า settings ที่เข้าได้จาก header ทุกหน้า และจากปุ่ม "ปรับเกณฑ์" ข้างปุ่มรัน batch บนหน้า candidates และแสดงเกณฑ์ที่แก้ได้แบ่งตามหมวด liquidity, quality gate, fair value, CDC, risk/reward และ candidates แต่ละช่อง SHALL แสดงชื่อภาษาไทย ค่าปัจจุบัน และค่า default

#### Scenario: เปิดหน้า settings ครั้งแรก
- **WHEN** ผู้ใช้ยังไม่เคยแก้ค่าใดและเปิดหน้า settings
- **THEN** ทุกช่องแสดงค่าเท่ากับ default ใน config และช่อง liquidity แสดง traded value ขั้นต่ำ 10 ล้านบาท/วัน

#### Scenario: ค่าที่แก้แล้วต่างจาก default
- **WHEN** ผู้ใช้เคยบันทึก traded value ขั้นต่ำเป็น 5 ล้านบาท/วัน
- **THEN** ช่องนั้นแสดงค่า 5 พร้อมระบุว่า default คือ 10 และทำเครื่องหมายว่าแก้จาก default แล้ว

#### Scenario: ไปหน้า settings จากหน้า candidates
- **WHEN** ผู้ใช้อยู่ที่หน้า candidates แล้วกดปุ่ม "ปรับเกณฑ์" ข้างปุ่มรัน batch
- **THEN** ระบบเปิดหน้า settings

### Requirement: เกณฑ์ที่ไม่อยู่บนหน้า settings
ระบบ SHALL NOT แสดงสูตร CDC (ราคาตั้งต้น, smoothing, ความยาว EMA fast/slow), รายชื่อ sector การเงิน, catalyst hints, วัน index review และค่าของ batch บนหน้า settings ค่าเหล่านี้ SHALL ยังมาจาก config ตามเดิม

#### Scenario: สูตร CDC ไม่ถูกแก้จากเว็บ
- **WHEN** ผู้ใช้เปิดหน้า settings
- **THEN** หน้านั้นไม่มีช่อง fast/slow EMA และ batch ยังใช้ค่าจาก config

### Requirement: Tooltip อธิบายผลกระทบเป็นภาษาไทย
ทุกช่องบนหน้า settings SHALL มี tooltip ภาษาไทยที่บอกว่าค่านี้ใช้ทำอะไร และถ้าเพิ่มหรือลดค่าจะทำให้ผลเปลี่ยนอย่างไร (เช่น จำนวน candidates, ความเสี่ยง, ระยะเวลาที่เงินแช่) tooltip SHALL แสดงเมื่อ hover และเมื่อ focus ด้วยคีย์บอร์ด และ screen reader SHALL อ่านได้

#### Scenario: hover ที่ liquidity
- **WHEN** ผู้ใช้ hover ที่ไอคอนข้อมูลของ traded value ขั้นต่ำ
- **THEN** tooltip อธิบายว่าลดค่าจะได้หุ้นเข้ามาประเมินมากขึ้น แต่หุ้นสภาพคล่องต่ำมักใช้เวลานานกว่าจะ re-rate ทำให้เงินแช่นานขึ้น

#### Scenario: ใช้คีย์บอร์ด
- **WHEN** ผู้ใช้กด Tab จน focus อยู่ที่ไอคอนข้อมูลของช่องใดช่องหนึ่ง
- **THEN** tooltip ของช่องนั้นแสดงขึ้นโดยไม่ต้องใช้เมาส์

### Requirement: แสดงและรับค่าเป็นหน่วยที่อ่านง่าย
ช่องที่เป็นสัดส่วน SHALL แสดงและรับค่าเป็นเปอร์เซ็นต์ และ traded value SHALL แสดงและรับค่าเป็นล้านบาท ค่าที่ engine ใช้และที่ API ส่ง SHALL ยังเป็นหน่วยเดิม (สัดส่วนเป็นทศนิยม, traded value เป็นบาท)

#### Scenario: แก้ ROE ขั้นต่ำ
- **WHEN** ผู้ใช้กรอก ROE ขั้นต่ำเป็น 8 แล้วบันทึก
- **THEN** batch ครั้งถัดไปใช้ ROE ขั้นต่ำ 0.08

#### Scenario: แก้ liquidity
- **WHEN** ผู้ใช้กรอก traded value ขั้นต่ำเป็น 3 แล้วบันทึก
- **THEN** batch ครั้งถัดไปใช้เกณฑ์ 3,000,000 บาท/วัน

### Requirement: เลือกเกณฑ์ fair value และ CDC state
ระบบ SHALL ให้เลือกเกณฑ์ fair value ที่เปิดใช้และ CDC state ที่รับเข้า candidate list ได้จากตัวเลือกที่มีอยู่เท่านั้น และ SHALL ไม่ยอมให้บันทึกโดยไม่เลือกอะไรเลย

#### Scenario: ปิด peer PE
- **WHEN** ผู้ใช้เอา peer PE ออกจากเกณฑ์ fair value แล้วบันทึก
- **THEN** batch ครั้งถัดไปไม่คำนวณ peer PE และ median MoS คิดจากเกณฑ์ที่เหลือ

#### Scenario: ไม่เลือก state เลย
- **WHEN** ผู้ใช้เอา CDC state ออกทั้งหมดแล้วกดบันทึก
- **THEN** ระบบไม่บันทึก และแจ้งว่าต้องเลือกอย่างน้อยหนึ่ง state

### Requirement: Validate ก่อนบันทึก
ระบบ SHALL ตรวจค่าทั้งหมดก่อนบันทึก ถ้ามีค่าผิด SHALL ไม่บันทึกค่าใดเลย และ SHALL บอกเหตุผลเป็นภาษาไทยที่ช่องที่ผิด ค่าที่ต้องตรวจ: ชนิดข้อมูล ช่วงค่าที่สมเหตุสมผลของแต่ละช่อง OCF ที่ต้องเป็นบวกไม่เกิน window และระยะถือขั้นต่ำไม่เกินระยะถือสูงสุด

#### Scenario: ค่าติดลบ
- **WHEN** ผู้ใช้กรอก D/E สูงสุดเป็น −1 แล้วบันทึก
- **THEN** ระบบไม่บันทึก และช่อง D/E แสดงเหตุผลว่าค่าต้องไม่ติดลบ

#### Scenario: ค่าสองช่องขัดกัน
- **WHEN** ผู้ใช้ตั้ง OCF เป็นบวกอย่างน้อย 5 ไตรมาส แต่ window คือ 4 ไตรมาส
- **THEN** ระบบไม่บันทึก และแจ้งว่าจำนวนไตรมาสที่ OCF เป็นบวกต้องไม่เกิน window

#### Scenario: ค่าหนึ่งผิด ค่าอื่นถูก
- **WHEN** ผู้ใช้แก้ liquidity เป็นค่าที่ถูก และแก้ ROE เป็นค่าที่ผิดในการบันทึกครั้งเดียวกัน
- **THEN** ระบบไม่บันทึกทั้งสองค่า และค่าที่บันทึกไว้ก่อนหน้ายังเหมือนเดิม

### Requirement: Reset กลับเป็น default
ระบบ SHALL ให้ reset ค่าทั้งหมดกลับเป็น default ใน config ได้ในครั้งเดียว และหลัง reset SHALL ใช้ default ใน config ตามปัจจุบัน ไม่ใช่ default ตอนที่บันทึก

#### Scenario: reset หลังแก้หลายช่อง
- **WHEN** ผู้ใช้แก้ไว้ 3 ช่องแล้วกด reset และยืนยัน
- **THEN** ทุกช่องกลับเป็นค่า default และ batch ครั้งถัดไปใช้ค่า default

#### Scenario: default ใน config เปลี่ยนภายหลัง
- **WHEN** ผู้ใช้ไม่เคยแก้ ROE ขั้นต่ำ แล้วมีการแก้ default ใน config เป็น 12%
- **THEN** หน้า settings และ batch ครั้งถัดไปใช้ ROE ขั้นต่ำ 12%

### Requirement: ค่าที่บันทึกมีผลกับ batch ครั้งถัดไป
ค่าที่บันทึก SHALL มีผลกับ batch ครั้งถัดไปทุกช่องทาง ทั้งปุ่มรัน batch บนเว็บและการรันจาก command line หรือ cron ค่าที่บันทึก SHALL คงอยู่หลัง restart engine และ SHALL ไม่เปลี่ยนผลของ run ที่รันไปแล้ว

#### Scenario: รันจาก cron หลังแก้ค่าบนเว็บ
- **WHEN** ผู้ใช้ลด liquidity เป็น 3 ล้านบาท/วันบนเว็บ แล้ว cron รัน batch
- **THEN** batch นั้นใช้เกณฑ์ 3 ล้านบาท/วัน

#### Scenario: restart engine
- **WHEN** ผู้ใช้บันทึกค่าแล้ว restart engine
- **THEN** หน้า settings ยังแสดงค่าที่บันทึกไว้

### Requirement: แจ้งเมื่อผลที่เห็นใช้ค่าเก่า
ถ้ามีการบันทึกหรือ reset ค่าหลังจาก run สำเร็จล่าสุดเริ่มทำงาน หน้า candidates และหน้า settings SHALL แจ้งว่าผลที่แสดงยังใช้ค่าเก่า และชวนให้รัน batch ใหม่

#### Scenario: แก้ค่าหลังรัน
- **WHEN** batch สำเร็จตอน 17:00 แล้วผู้ใช้บันทึกค่าใหม่ตอน 18:00
- **THEN** หน้า candidates แจ้งว่าผลใช้ค่าก่อนแก้ และควรรัน batch ใหม่

#### Scenario: รันใหม่หลังแก้ค่า
- **WHEN** ผู้ใช้รัน batch ใหม่หลังบันทึกค่า และ batch นั้นสำเร็จ
- **THEN** ข้อความแจ้งนั้นหายไป
