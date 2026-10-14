# Design

## Context

- `quality.evaluate` คืน `checks` 5 ข้อ (`min_quarters`, `roe`, `de`, `ocf`, `no_loss`) โดย `passed=None` คือข้าม และตั้ง `passed = all(c["passed"] is not False ...)`
- ถ้า `min_quarters` ไม่ผ่าน ฟังก์ชัน return ทันที เกณฑ์อื่นไม่ถูกคำนวณ
- Liquidity อยู่นอก quality (`ev["liquidity"]`) ถ้าไม่ผ่าน batch ไม่ดึงงบ `ev["quality"]` จึงเป็น `None`
- `candidates.inclusion` อ่านแค่ `quality.passed` และ reason ของ check ที่ `passed is False`
- เว็บสร้างแถว gate (liquidity + checks) ซ้ำกันสองที่: `app/stocks/[symbol]/page.tsx` และ `lib/llm-export.ts`
- หน้า settings render ช่องจาก `editable(...)` ใน `config.py` อัตโนมัติ หน่วยแสดงผลอยู่ใน `UNIT_LABEL` ของ `lib/format.ts`

## Goals / Non-Goals

**Goals:** ให้ `quality.passed` ใช้กฎ "ไม่ผ่านได้ไม่เกิน N" และให้หน้าเว็บแสดงจำนวน gate ที่ผ่าน

**Non-Goals:** ไม่เปลี่ยน DB schema หรือ API ไม่แตะ `candidates.inclusion` และ `sort_key`

## Decisions

### D1 เกณฑ์ไหนบังคับ: liquidity และ min_quarters
ผู้ใช้เลือก (15 ต.ค. 2026) Liquidity บังคับอยู่แล้วโดยโครงสร้าง (ไม่ผ่านคือไม่มีงบ ไม่มี fair value) ส่วน `min_quarters` คงการ return ทันทีไว้
- ทางเลือก: ให้ `min_quarters` ไม่บังคับ ไม่เลือกเพราะต้องคำนวณ ROE/D/E/OCF บนประวัติสั้น และ PE/PBV band ของ fair value มีข้อมูลน้อยเกินจนเชื่อถือไม่ได้

### D2 กฎเป็น `max_failed_checks` (default 2) ไม่ใช่ `min_passed`
นับเฉพาะ check ที่ `passed is False` ในเกณฑ์ไม่บังคับ: `passed = min_quarters ผ่าน and failed <= cfg.max_failed_checks` check ที่ข้าม (`None`) ไม่นับ
- ทางเลือก `min_passed_checks: 4` จาก 6: หุ้นการเงินมีเกณฑ์ที่ประเมินแค่ 4 ข้อ (รวม liquidity) จะต้องผ่านครบ ไม่ยุติธรรมกับหุ้นทั่วไป ไม่เลือก
- ทางเลือก ยอมให้ไม่ผ่านแยกตามเกณฑ์ (เช่น ROE บังคับ D/E ไม่บังคับ): ยืดหยุ่นกว่าแต่เพิ่ม config หลายช่องโดยยังไม่มีความต้องการ ไม่เลือก (YAGNI) ทำทีหลังได้
- Validate `ge=0, le=4` ด้วย `editable(...)` เหมือนช่องอื่น หน่วยใหม่ `checks` → "เกณฑ์" ใน `UNIT_LABEL`

### D3 นับจำนวน gate ที่เว็บ จาก checks ที่เก็บไว้
ฟังก์ชันเดียวใน `web/lib` (เช่น `gateRows(ev)` คืนแถว liquidity + checks และ `gateTally(rows)` คืน `{passed, evaluated, failed}`) ใช้ร่วมกันใน candidate list, หน้ารายละเอียด และ `llm-export.ts` (ย้ายโค้ดสร้างแถวที่ซ้ำอยู่มาใช้ฟังก์ชันนี้ ผลลัพธ์ของ export ไม่เปลี่ยน) `evaluated` = แถวที่ `passed !== null`
- ทางเลือก ให้ engine เก็บ `passed_count` ใน evaluation: ต้องแก้ batch และ run เก่าไม่มีค่า ข้อมูลที่ต้องใช้อยู่ใน checks ครบแล้ว ไม่เลือก
- ทางเลือก สร้างแถวแยกในแต่ละหน้าต่อไป: มีผู้ใช้ 3 ที่แล้ว ถ้าแยกกันจำนวนบนตารางกับหน้ารายละเอียดอาจไม่ตรงกัน ไม่เลือก

### D4 คอลัมน์ "Gates" วางหลัง Sector, tooltip ใช้ `Tooltip` ใน `app/badges.tsx`
แสดง `passed/evaluated` ใช้สีเดิมของตาราง tooltip เป็นรายการ reason ของ check ที่ไม่ผ่าน (เช่น "D/E 2.30") ถ้าผ่านครบไม่มี tooltip ใช้ component `Tooltip` เดียวกับ fair value panel และหน้า settings ซึ่ง hover และ focus ได้
- ทางเลือก attribute `title` แบบคอลัมน์ RRR: เคยพบว่า native `title` ไม่แสดงในแอปนี้ และใช้คีย์บอร์ดไม่ได้ ไม่เลือก
- ทางเลือก แสดงชื่อเกณฑ์ที่ไม่ผ่านเป็นป้ายในคอลัมน์ป้าย: ตารางกว้างอยู่แล้ว ไม่เลือก

### D5 ข้อความของ inclusion ไม่เปลี่ยน
หุ้นที่ผ่าน gate แบบมีเกณฑ์ตก ไม่มี inclusion reason (เพราะผ่าน) หุ้นที่ไม่ผ่านยังแสดง "ไม่ผ่าน quality gate: <reason ทุกข้อที่ตก>" เหมือนเดิม

## Risks / Trade-offs

- **[Worst case] หุ้นที่ขาดทุนและ ROE ต่ำเข้า candidate list**: default 2 ยอมให้ตกทั้ง ROE และไม่ขาดทุนพร้อมกัน หุ้นการเงินที่ตกทั้งสองข้อก็ผ่าน (เหลือแค่ liquidity + จำนวนไตรมาส) ถ้ามี MoS สูงจากกำไรในอดีต (PBV band, dividend yield) อาจเป็น value trap ที่เงินแช่เกินหนึ่งไตรมาส → คอลัมน์ Gates และ tooltip ทำให้เห็นทันที, task 3.1 ตรวจว่ามีหุ้นแบบนี้ใน list หรือไม่ ถ้าพบบ่อยค่อยเสนอให้ `no_loss` บังคับ หรือเพิ่ม gate "EPS TTM ไม่ลดลง YoY" เป็น change แยก
- **[Risk] จำนวน candidates เพิ่มมากจนตารางยาว**: ปรับ `max_failed_checks` ลงบนหน้า settings ได้โดยไม่ต้องแก้โค้ด
- **[Risk] เทียบ batch รวมของ change อื่นไม่ได้**: ดู proposal ส่วน Dependencies → implement หลัง batch รวมเสร็จ หรือตั้ง 0 ชั่วคราว
- **[Trade-off] ค่าที่ผู้ใช้บันทึกบนเว็บไว้ก่อน**: ไม่มี key ใหม่ใน DB จึงใช้ default 2 จาก `config.yaml` ทันทีหลัง deploy

## Migration Plan

ไม่มี migration ของข้อมูล rollback ด้วยการตั้ง `max_failed_checks: 0` (กลับเป็นพฤติกรรมเดิม) หรือ revert commit
