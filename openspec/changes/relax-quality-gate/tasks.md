# Tasks

> ควร implement หลัง batch รวมของ `simplify-risk-reward` 4.1 รันเสร็จ (ดู proposal ส่วน Dependencies)

## 1. Engine

- [x] 1.1 เพิ่ม `max_failed_checks` ใน `Quality` (`shortlist/config.py`) ด้วย `editable(...)` หน่วย `checks`, `ge=0, le=4` พร้อมชื่อและ tooltip ภาษาไทยตาม spec filter-settings และใส่ `max_failed_checks: 2` ใน `config.yaml` (D2) เพิ่ม test ใน `tests/test_config.py` ว่าค่า 5 ไม่ผ่าน validation ตรวจด้วย `uv run pytest tests/test_config.py`
- [x] 1.2 เปลี่ยนเงื่อนไข `passed` ใน `quality.evaluate` เป็น min_quarters ผ่านและจำนวน check ที่ `passed is False` ≤ `max_failed_checks` (D1, D2) เพิ่ม test ใน `tests/test_quality.py` ตามทุก scenario ของ requirement "เกณฑ์พื้นฐาน" (ตก 1 ผ่าน, ตก 3 ไม่ผ่าน, ตั้ง 0 แล้วตก 1 ไม่ผ่าน, ไตรมาสไม่พอไม่ผ่าน, ธนาคารตก ROE ผ่าน) และแก้ test เดิมที่คาดว่าตกข้อเดียวแล้วไม่ผ่าน ตรวจด้วย `uv run pytest` ทั้งชุดผ่าน
- [x] 1.3 แก้กล่อง Quality gate ใน `docs/batch-flow.md` ให้บอกว่าไม่ผ่านได้ไม่เกิน N ข้อ (liquidity และจำนวนไตรมาสบังคับ) ตรวจโดยอ่าน diagram ว่าตรงกับ spec

## 2. Web

- [x] 2.1 เพิ่มหน่วย `checks` → "เกณฑ์" ใน `SettingUnit` และ `UNIT_LABEL` (`lib/format.ts`, `lib/engine.ts`) ตรวจด้วย `bun run lint` และเปิดหน้า settings ใน browser ว่าหมวด quality gate มีช่องใหม่ default 2 tooltip แสดงทั้ง hover และ focus และกรอก 5 แล้วบันทึกไม่ได้
- [x] 2.2 สร้างฟังก์ชันนับ gate ใน `web/lib` (D3) แล้วให้หน้ารายละเอียดและ `lib/llm-export.ts` ใช้สร้างแถว gate แทนโค้ดที่ซ้ำ พร้อม test (5/6 เมื่อตก D/E, 4/4 สำหรับธนาคาร, 0/1 เมื่อไม่มี quality) ตรวจด้วย `bun test` ผ่านทั้งชุด (รวม `llm-export.test.ts` ที่ผลไม่เปลี่ยน) และ `bun run lint`
- [x] 2.3 เพิ่มคอลัมน์ "Gates" หลัง Sector ใน `app/page.tsx` พร้อม `Tooltip` รายการเกณฑ์ที่ไม่ผ่าน (D4) และแสดง `ผ่าน N/M` ที่หัวข้อ Gates ใน `app/stocks/[symbol]/page.tsx` ตรวจด้วย `bun run lint` และเปิด browser ด้วย skill `orca-browser-check` ดูว่าตารางแสดงจำนวน, hover เห็นเกณฑ์ที่ไม่ผ่าน, หน้ารายละเอียดตรงกับตาราง และ run เก่าไม่พัง

## 3. ตรวจกับ batch จริง

- [x] 3.1 บันทึก candidate list ของ run ล่าสุดไว้เทียบ แล้วรัน batch ใหม่ด้วย default 2 ตรวจว่า run สำเร็จ ทุกหุ้นที่เคยอยู่ใน list ยังอยู่ (gate หลวมขึ้นอย่างเดียว) และลำดับของหุ้นเดิมเทียบกันยังตามกฎ CDC → ETA → MoS นับหุ้นใหม่ที่เข้ามาแยกตามเกณฑ์ที่ตก และระบุหุ้นที่ตกทั้ง ROE และไม่ขาดทุน (worst case ใน design) ตรวจด้วย skill `stock-sanity-check`
- [x] 3.2 spot-check หุ้นใหม่อย่างน้อย 3 ตัว (รวมหุ้นการเงิน 1 ตัวถ้ามี) ว่า D/E, ROE TTM, OCF และกำไรรายไตรมาสของเกณฑ์ที่ตกตรงกับงบบน SET และจำนวนในคอลัมน์ Gates ตรงกับหน้ารายละเอียด บันทึกผลและหุ้นที่เข้ามาใหม่ใน `engine/README.md`
