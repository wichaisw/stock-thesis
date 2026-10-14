# Design

## Context

`core/fair_value.evaluate` คำนวณทุกเกณฑ์ใน closure `fair(method)` จาก `quarterly` (แหล่งงบ thaifin) และ `caps` (market cap รายไตรมาสที่สร้างเองจากราคาจริง × จำนวนหุ้น) แล้ว `summarize` นับ undervalued ต่อรายการ `QUARTERLY_COLUMNS` ตอนนี้ไม่มีเงินสด หนี้ หรือ EBITDA แต่ thaifin มี `cash`, `total_debt`, `ebit_dattm` ซึ่งยังไม่เคย cross-check `evaluate` ไม่รู้ sector ส่วน `quality.evaluate` รู้ และมี `roe_ttm` (กำไร 4 ไตรมาส ÷ ส่วนผู้ถือหุ้นเฉลี่ย 4 ไตรมาส) อยู่แล้ว

## Goals / Non-Goals

**Goals:**
- เพิ่ม Justified PBV ซึ่งไม่ขึ้นกับราคาในอดีต
- นับ undervalued ให้ตรงกับจำนวนมุมมองที่เป็นอิสระจริง โดยไม่เปลี่ยน median MoS ที่ candidate gate ใช้ นอกจากผลจากเกณฑ์ที่เพิ่ม

**Non-Goals:**
- ไม่จัดกลุ่ม peer PE กับ PE band แม้ใช้กำไร TTM ตัวเดียวกัน (multiple ต่างแหล่ง: อดีตตัวเอง vs sector)
- ไม่ติดป้ายเตือนใหม่สำหรับ EV/EBITDA (ใช้ `history_gap` และ `structure_change` เดิม)

## Decisions

> task 1.1 พบว่า `ebit_dattm` ของ thaifin ว่างทุกไตรมาส และ `total_debt` คือหนี้สินรวม จึงตัด EV/EBITDA band ออก D1, D2, D3, D6 ไม่ใช้แล้ว เก็บไว้เป็นเหตุผลสำหรับ change ที่จะทำ EV/EBITDA ภายหลัง

### D1 EV ใช้ market cap ของเรา + `total_debt` − `cash` จาก thaifin
- ทางเลือก: ใช้ `ev_per_ebit_da` สำเร็จรูปของ thaifin → ปฏิเสธ เพราะ thaifin คิดจากราคาที่ปรับตามปันผล ซึ่งเป็นเหตุผลเดียวกับที่ PE/PBV band เลิกใช้ราคาจากแหล่งงบ (spec "PE และ PBV ระดับบริษัท")
- ทางเลือก: ใช้หนี้สินรวมจาก D/E × equity → ปฏิเสธ เพราะรวมเจ้าหนี้การค้าและหนี้ที่ไม่มีดอกเบี้ย ทำให้ EV สูงเกินจริง
- task แรกต้องยืนยันว่า `total_debt` เป็นหนี้ที่มีภาระดอกเบี้ย และ `ebit_dattm` เป็น EBITDA ย้อนหลัง 12 เดือน (ไม่ใช่รายไตรมาส) ถ้า `ebit_dattm` เป็นรายไตรมาสให้รวม 4 ไตรมาสเอง ถ้า `total_debt` หรือ `cash` ไม่ตรงกับงบบน SET ให้หยุดส่วน EV/EBITDA และส่งเฉพาะ Justified PBV

### D2 ตั้งชื่อคอลัมน์ `ebitda_ttm` ในรูปแบบกลางของแหล่งข้อมูล
- adapter แปลง `ebit_dattm` → `ebitda_ttm` ตาม `FIELD_MAP` เดิม เพื่อให้ core ไม่ผูกกับชื่อของ thaifin ถ้าเปลี่ยนแหล่ง (เช่น SETSMART) แค่แก้ adapter

### D3 บอก `evaluate` ว่าเป็นหุ้นการเงินด้วย parameter `is_financial: bool`
- ทางเลือก: ส่ง sector + `Quality` config เข้า fair value → ปฏิเสธ เพราะ fair value จะผูกกับ config ของ gate อื่น
- ทางเลือก: ย้าย `financial_sectors` มาไว้ใน config กลาง → ปฏิเสธ เกินขอบเขต (ย้าย config ที่ผู้ใช้อาจแก้ไว้แล้ว)
- `batch.py` คิด `info.sector in cfg.quality.financial_sectors` แล้วส่งค่า bool

### D4 Justified PBV ใช้ `quality.roe_ttm` (ส่วนผู้ถือหุ้นเฉลี่ย 4 ไตรมาส)
- ทางเลือก: กำไร TTM ÷ ส่วนผู้ถือหุ้นล่าสุด → ปฏิเสธ เพราะหน้ารายละเอียดจะมี ROE สองค่าที่ต่างกันเล็กน้อย (gate กับ fair value) ทำให้สับสน และ ROE ของ thaifin annualize ไตรมาสเดียว (เหตุผลเดียวกับ gate)
- ย้าย `roe_ttm` ไป `core/__init__` หรือ import จาก `core.quality` ตรงๆ เลือก import ตรงๆ เพราะเป็นฟังก์ชันเดียว ไม่ต้องสร้าง module ใหม่
- ใช้ส่วนผู้ถือหุ้นล่าสุดเป็นฐาน book (ไม่ใช่ BVPS ของ thaifin) แปลงด้วยจำนวนหุ้นล่าสุด เหมือน PBV band

### D5 การนับมุมมองใช้ map คงที่ `VIEW = {"pe_minus_1sd": "pe_median"}`
- มุมมองที่มีหลายรายการ นับ undervalued จากค่าเฉลี่ย MoS ของรายการที่คำนวณได้
- ทางเลือก: นับ undervalued เมื่อทุกรายการในกลุ่มเป็นบวก → ปฏิเสธ เข้มเกินไป PE − 1SD ออกแบบมาให้ติดลบบ่อย
- ทางเลือก: ใช้ PE median ตัวเดียว → ปฏิเสธ เพราะถ้าผู้ใช้ปิด PE median มุมมองนี้จะหายไปทั้งที่ยังมี − 1SD
- ไม่ทำ config สำหรับการจัดกลุ่ม มีแค่คู่นี้คู่เดียว

### D6 `max_ev_ebitda` (default 50) แยกจาก `max_pe`
- EV/EBITDA ปกติต่ำกว่า PE ราว 1.5–2 เท่า ใช้ `max_pe` ร่วมจะเก็บค่าที่เพี้ยนไว้ ต้องตัดด้วยเหตุผลเดียวกัน (EBITDA ใกล้ศูนย์ทำให้ median เพี้ยน)

### D7 `cost_of_equity` และ `terminal_growth` เป็นค่า editable ใน `FairValue` พร้อม validator g < r
- ทางเลือก: คิด r จาก risk-free + beta → ปฏิเสธ ต้องมีแหล่งข้อมูลพันธบัตรและ beta ซึ่งยังไม่ cross-check
- validator ระดับ model ทำให้หน้า settings ปฏิเสธค่าที่ทำให้ตัวหารเป็นศูนย์หรือติดลบ

## Risks / Trade-offs

- [worst case: `total_debt` ของ thaifin คือหนี้สินรวม หรือ `cash` ขาดเงินลงทุนระยะสั้น ทำให้ EV/EBITDA band ผิดทุกตัวเงียบๆ และ median MoS ของทั้งตลาดเพี้ยน candidate list ผิด] → task 1 cross-check ก่อนเขียน code ถ้าไม่ตรงหยุดส่วน EV/EBITDA
- [Justified PBV ไวต่อ r − g มาก: r 10% → 9% ทำให้ fair value สูงขึ้นราว 17% สำหรับ ROE 17%] → แสดง r, g ใน tooltip และ settings; รายการนี้เป็นแค่ 1 ใน 6 ของ median
- [หุ้น ROE สูงผิดปกติจากกำไรพิเศษครั้งเดียว ได้ Justified PBV สูงมาก → `max_fair_value` ดัน target optimistic] → มีป้าย upside สูงผิดปกติของ risk/reward อยู่แล้ว และ median ไม่โดนค่าเดียวดึง
- [median MoS เปลี่ยนเพราะมีเกณฑ์ใหม่ candidate ที่เคยผ่านอาจหลุด หรือกลับกัน] → task integration เทียบ candidate list ก่อน/หลัง และ spot-check หุ้นที่เปลี่ยน
- [หุ้นเงินสดสุทธิสูง (หนี้สุทธิติดลบ) ได้ fair value สูงขึ้นจากเงินสด] → ตั้งใจ เป็นมุมมองที่เกณฑ์อื่นไม่มี

## Migration Plan

- run เก่าไม่มีเกณฑ์ใหม่ เว็บแสดงเฉพาะ items ที่มี จึงไม่พัง
- rollback: เอา `justified_pbv` ออกจาก `fair_value.enabled` ในหน้า settings แล้วรัน batch ใหม่
