# Design

## Context

ดู proposal.md - Why สำหรับปัญหาของ `dividend_yield` ของ thaifin

สิ่งที่มีอยู่แล้วจาก `value-stock-shortlist`:
- `YahooPrices.fetch_market_caps()` ดึงประวัติราคา 6 ปีด้วย `history(auto_adjust=False, actions=True)` ต่อหุ้นที่ผ่าน liquidity แล้ว ผลที่ได้มีคอลัมน์ `Dividends` และ `Stock Splits` มาด้วย แต่ยังไม่ได้ใช้ `Dividends`
- `core/fair_value.evaluate()` คิด dividend yield band จาก `dividend_yield` และ `close` ของ thaifin (DPS = yield × close ของ thaifin)

ตรวจ yfinance แล้ว (14 ต.ค. 2026): ปันผลเงินสดของ PTT (0.8 + 1.3 บาท ปี 2022), AOT (ไม่มีในปีที่ขาดทุน), DITTO (0.0093 บาท พร้อม split 1.2 ปี 2022) และ DOHOME (เงินสดเล็กน้อย + split ทุกปี) ตรงกับลักษณะการจ่ายจริง ปันผลเป็นหุ้นอยู่ใน `Stock Splits` ไม่อยู่ใน `Dividends`

## Goals / Non-Goals

**Goals:**
- Dividend yield band ใช้ข้อมูลชุดเดียวกับ market cap (ราคาและ split จาก yfinance) จึงอยู่บนฐานจำนวนหุ้นเดียวกัน
- ไม่เพิ่ม network request

**Non-Goals:**
- ลบ `dividend_yield` ออกจาก adapter ของ thaifin และตาราง `financials_quarterly` (ยังเก็บไว้ดู แค่ไม่ใช้คำนวณ)
- คิด yield จากปันผลประกาศจ่ายที่ยังไม่ XD

## Decisions

### D1. คิด yield 12 เดือนจาก `Dividends` ÷ `Close` ที่ปรับ split แล้วทั้งคู่

`Dividends` ของ yfinance ถูกปรับตาม split เหมือน `Close` (`auto_adjust=False` ปรับ split แต่ไม่ปรับปันผล) อัตราส่วนของสองค่าจึงเท่ากับ yield ที่ราคาจริงโดยไม่ต้องถอดการปรับ split ส่วนผลรวม `Dividends` 12 เดือนล่าสุดเป็น DPS บนฐานจำนวนหุ้นปัจจุบันพอดี ใช้หาร median yield เป็น fair value ต่อหุ้นได้เลย

yield ของไตรมาส = ผลรวม `Dividends` ที่ XD ในช่วง 365 วันก่อนวันซื้อขายสุดท้ายของไตรมาส ÷ `Close` วันนั้น คืนจาก adapter เป็นคอลัมน์ `dividend_yield_ttm` และ `dps_ttm` เพิ่มใน DataFrame เดียวกับ market cap (key เป็นไตรมาส)

- ทางเลือกอื่น: ถอดการปรับ split ออกแบบ market cap แล้วคูณจำนวนหุ้น ปฏิเสธเพราะได้ผลเท่ากันแต่มีขั้นตอนมากกว่าและพึ่งจำนวนหุ้นที่มีช่องว่าง (WSOL)
- ทางเลือกอื่น: ใช้ `ticker.dividends` แยก ปฏิเสธเพราะเพิ่ม request ทั้งที่ `history(actions=True)` ให้มาแล้ว
- ทางเลือกอื่น: แก้ `dividend_yield` ของ thaifin ด้วยการตัดค่าต่ำทิ้งอย่างเดียว ปฏิเสธเพราะไม่แก้ปัญหา PTT ที่ไตรมาสไม่จ่ายแสดง ~1% แทน yield 12 เดือน
- ทางเลือกอื่น: นับมูลค่าหุ้นปันผลเป็น yield ปฏิเสธเพราะปันผลเป็นหุ้นไม่ได้โอนมูลค่าให้ผู้ถือหุ้น (ราคาปรับลงตามสัดส่วน) และจะทำให้ DITTO ปี 2022 มี yield ราว 20%

### D2. เกณฑ์ yield ขั้นต่ำเป็น config `fair_value.min_dividend_yield` default 0.005

ไตรมาสที่ yield 12 เดือนต่ำกว่าเกณฑ์ถือว่าไม่ได้จ่าย เหมือนกับที่ปัจจุบันตัดไตรมาสที่ yield เป็นศูนย์ ใช้ทั้งตอนคิด median และตอนเช็คว่าไตรมาสล่าสุดยังจ่ายอยู่หรือไม่ ใช้ `min_history_points` เดิมเป็นจำนวนไตรมาสขั้นต่ำ

0.5% เพราะเงินสดที่มากับปันผลเป็นหุ้นของ DITTO และ DOHOME ให้ yield ไม่เกิน 0.1% ส่วนหุ้นที่จ่ายเงินสดจริงในตลาดไทยมักเกิน 1% ค่านี้ตรวจอีกครั้งใน task ตรวจผลทั้งตลาด

- ทางเลือกอื่น: ตัดไตรมาสที่มี split (ปันผลเป็นหุ้น) ใน 12 เดือนก่อนหน้าแทนเกณฑ์ yield ปฏิเสธเพราะหุ้นที่จ่ายทั้งหุ้นและเงินสดก้อนใหญ่ในปีเดียวกันจะถูกตัดไปด้วย และไม่ช่วยกรณีที่จ่ายเงินสดน้อยมากโดยไม่มีหุ้นปันผล

### D3. `core/fair_value` อ่าน yield จากข้อมูล market cap ไม่ใช่จากงบ

`evaluate()` รับ `caps` อยู่แล้ว จึงเปลี่ยนแค่แหล่งของคอลัมน์ ไม่ต้องเปลี่ยน signature และไม่แตะ batch flow (design D4 ของ `value-stock-shortlist`) ถ้าหุ้นไม่มีประวัติราคาจาก yfinance (ไม่มี `caps`) เกณฑ์นี้เป็น N/A เหมือน PE/PBV band

## Risks / Trade-offs

- [yfinance ขาดปันผลบางครั้งหรือบันทึกวัน XD ผิด] → yield 12 เดือนของไตรมาสนั้นต่ำหรือสูงไป median รับได้ไม่กี่จุด และมี task เทียบกับ dividend yield ของ SET ก่อนใช้
- [กรณีแย่สุด: yfinance ไม่มีปันผลของหุ้นไทยเลยสำหรับบางตัว] → band เป็น N/A แทนที่จะได้ค่าผิด ไม่ทำให้หุ้นหลุดจาก candidate list เพราะ fair value เป็น panel ไม่ใช่ gate
- [ปันผลพิเศษทำให้ DPS 12 เดือนล่าสุดสูง] → fair value สูงชั่วคราวจนครบ 12 เดือน tooltip เตือนไว้แล้ว
- [หุ้นที่เพิ่งเปลี่ยนจากปันผลเป็นหุ้นมาเป็นเงินสด (DITTO)] → band คิดจากไตรมาสหลังเปลี่ยนเท่านั้น ถ้าน้อยกว่า `min_history_points` จะเป็น N/A
- [เกณฑ์ 0.5% ตัดหุ้นที่จ่ายเงินสดน้อยจริง เช่น หุ้นเติบโตที่ yield 0.3%] → เกณฑ์นี้เป็น N/A สำหรับหุ้นเหล่านั้น ซึ่งยอมรับได้เพราะ yield band ไม่มีความหมายกับหุ้นที่ไม่ได้ให้ผลตอบแทนเป็นปันผล ปรับเกณฑ์ได้ใน config
- [fair value ของ dividend yield band เปลี่ยนเกือบทุกหุ้น ลำดับ candidate เปลี่ยน] → เทียบ candidate list ก่อนและหลังเปลี่ยน แล้วบันทึกหุ้นที่เข้าหรือออกใน `engine/README.md`

## Migration Plan

ไม่มีการย้ายข้อมูล ผลประเมินเก็บเป็น JSON ต่อ run (design D3 ของ `value-stock-shortlist`) run ถัดไปจะใช้สูตรใหม่เอง rollback ด้วยการ revert commit แล้วรัน batch ใหม่
