# cdc-proximity Specification

## Purpose

คำนวณ CDC ActionZone บน timeframe daily ให้ทุกหุ้นพร้อมกัน และบอกว่าหุ้นใกล้จุด cross แค่ไหน เพื่อให้ screen หุ้นที่ timing น่าจับตาได้ทั้งตลาด

## Requirements

### Requirement: คำนวณเส้น CDC ActionZone
ระบบ SHALL คำนวณจากราคารายวันที่ clean แล้วตาม CDC ActionZone V3 2020 ที่ผู้ใช้ตั้งไว้บน TradingView: ราคาตั้งต้น = ราคาปิด, AP = EMA ของราคาตั้งต้นด้วย smoothing period 1 (คือไม่ smooth), Fast = EMA 12 วันของ AP, Slow = EMA 26 วันของ AP ราคาตั้งต้น (close หรือ (open + high + low + close) / 4) และค่าความยาว EMA ทั้งหมด SHALL ปรับได้ใน config

#### Scenario: ผลตรงกับ indicator ต้นฉบับ
- **WHEN** คำนวณ Fast และ Slow ของหุ้นตัวอย่างในวันเดียวกับที่เปิดดูบน TradingView
- **THEN** ค่าที่ได้ตรงกับ CDC ActionZone บน TradingView ภายในความคลาดเคลื่อนจากการปัดเศษ

### Requirement: Gap และ ETA ถึงจุด cross
ระบบ SHALL คำนวณ gap% = (Slow − Fast) / Slow, ความเร็วที่ gap แคบลง = (gap% เมื่อ N วันทำการก่อน − gap% วันนี้) / N (default N = 5) และ ETA = gap% / ความเร็ว ในหน่วยวันทำการ เมื่อความเร็ว ≤ 0 SHALL ไม่มีค่า ETA

#### Scenario: gap กำลังแคบลง
- **WHEN** gap% วันนี้คือ 1.0% และ gap% เมื่อ 5 วันก่อนคือ 2.0%
- **THEN** ความเร็วคือ 0.2% ต่อวัน และ ETA คือ 5 วันทำการ

#### Scenario: gap กำลังกว้างขึ้น
- **WHEN** gap% วันนี้กว้างกว่าเมื่อ 5 วันก่อน
- **THEN** หุ้นไม่มีค่า ETA

### Requirement: State ของหุ้น
ระบบ SHALL จัดหุ้นทุกตัวเข้า state เดียว: `just-crossed` (Fast ขึ้นเหนือ Slow ภายใน 5 วันทำการล่าสุด), `bull` (Fast > Slow นานกว่านั้น), `bear-approaching` (Fast < Slow และ ETA ≤ 20 วันทำการ) หรือ `bear-far` (Fast < Slow ในกรณีอื่น) ค่า 5 และ 20 วัน SHALL ปรับได้ใน config

#### Scenario: ใกล้ cross
- **WHEN** Fast < Slow และ ETA คือ 6 วันทำการ
- **THEN** หุ้นอยู่ใน state `bear-approaching`

#### Scenario: เพิ่ง cross
- **WHEN** Fast ขึ้นเหนือ Slow เมื่อ 2 วันทำการก่อน
- **THEN** หุ้นอยู่ใน state `just-crossed`

#### Scenario: ห่างจากจุด cross
- **WHEN** Fast < Slow และไม่มีค่า ETA
- **THEN** หุ้นอยู่ใน state `bear-far`

### Requirement: ข้อมูลราคาไม่พอ
ระบบ SHALL ไม่จัด state ให้หุ้นที่มีราคารายวันที่ clean แล้วน้อยกว่าเกณฑ์ (default 60 วันทำการ) และ SHALL บันทึกเหตุผล

#### Scenario: ราคาย้อนหลังสั้นเกินไป
- **WHEN** หุ้นมีราคาที่ clean แล้วเพียง 30 วันทำการ
- **THEN** หุ้นไม่มี CDC state และผลการประเมินระบุว่าข้อมูลราคาไม่พอ
