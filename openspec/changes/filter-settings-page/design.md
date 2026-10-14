# Design

## Context

- `engine/config.yaml` เก็บเกณฑ์ทั้งหมด และ `shortlist/config.py` validate ด้วย pydantic (`extra="forbid"`) โดยโหลดใหม่ทุกครั้งที่ใช้ มีสามที่ที่เรียก `load_config()` ได้แก่ `api.py` (ตอนเริ่ม run และหน้ารายละเอียดหุ้น), `cli.py` (cron) และ `scripts/backtest_cdc.py`
- comment ใน YAML คือคำอธิบายเดียวของแต่ละค่าในตอนนี้ แต่ยังไม่มีคำอธิบายที่ UI นำไปแสดงได้
- liquidity เป็นตัวตัดสินว่าจะดึงงบของหุ้นตัวไหน (design D4 ของ `value-stock-shortlist`) ค่าใหม่จึงต้องรัน batch ใหม่ทั้งรอบ จะคำนวณ candidates ใหม่จากข้อมูลเดิมไม่ได้
- web คุยกับ engine ผ่าน HTTP เท่านั้น (D1) และใช้ server action กับ `useActionState` สำหรับฟอร์ม (`event-form.tsx`) tooltip ที่มีอยู่ (`Info`, `FailIcon` ใน `badges.tsx`) ใช้ `title` ของ browser ซึ่งไม่แสดงตอน focus ด้วยคีย์บอร์ด และแสดงข้อความยาวได้ไม่ดี

## Goals / Non-Goals

**Goals:**
- ข้อมูลของแต่ละช่อง (ชื่อ, คำอธิบาย, หน่วย, ช่วงค่า) อยู่ที่เดียวคือ `config.py` ส่วน web แสดงตามข้อมูลที่ engine ส่งมา โดยไม่มีรายชื่อช่องซ้ำอีกที่
- batch ทุกช่องทางใช้ config ชุดเดียวกัน

**Non-Goals:**
- เปลี่ยน tooltip เดิมที่ใช้ `title` บนหน้าอื่นมาใช้ component ใหม่ (ทำทีหลังถ้าต้องการ)
- auth: ยังใช้คนเดียวบน local ตาม `value-stock-shortlist`

## Decisions

### D1. เก็บเฉพาะค่าที่ต่างจาก default ในตาราง `settings` ของ SQLite

`config.yaml` ยังเป็นค่า default ส่วนตาราง `settings` เก็บแถวเดียว มี JSON ของค่าที่ผู้ใช้แก้ (key แบบ `quality.min_roe`) และ `updated_at` ตอนโหลดให้รวม override เข้ากับ YAML แล้วค่อย validate ทั้งก้อนด้วย model เดิม ค่าที่บันทึกเท่ากับ default จะไม่ถูกเก็บ ช่องที่ไม่เคยแก้จึงใช้ default ใหม่ทันทีเมื่อแก้ YAML (ตาม spec "default ใน config เปลี่ยนภายหลัง")

- ทางเลือกอื่น: เขียนกลับลง `config.yaml` ปฏิเสธเพราะ `yaml.safe_dump` ลบ comment ทั้งไฟล์ ต้องเพิ่ม `ruamel.yaml` ถึงจะเก็บ comment ไว้ได้ และ reset เป็น default ไม่ได้เพราะ default ถูกเขียนทับไปแล้ว
- ทางเลือกอื่น: ไฟล์ overlay `config.local.yaml` ใช้ได้เหมือนกัน แต่ engine เป็นเจ้าของข้อมูลใน SQLite อยู่แล้ว และตอนย้ายไป hosted DB จะไม่ต้องจัดการไฟล์บน serverless

### D2. Metadata ของแต่ละช่องอยู่ใน `Field()` ของ pydantic

ช่องที่แก้ได้ใช้ `Field(title=<ชื่อไทย>, description=<tooltip ไทย>, ge=..., le=..., json_schema_extra={"editable": True, "unit": "percent" | "million_baht" | ...})` ส่วน field ที่ไม่ได้ติด `editable` (สูตร CDC, sector การเงิน, catalyst, batch) จะไม่ขึ้นบนหน้า settings และ override ไม่ได้ engine ใช้ `model_fields` ทำรายการช่องให้ API โดยเรียงตามลำดับที่ประกาศ ตัวเลือกของ list (`enabled`, `accepted_states`) มาจาก `Literal` ที่มีอยู่แล้ว (`FairValueMethod`, `CdcState`) พร้อม label ไทยที่ map จากชื่อเดิม

- ทางเลือกอื่น: เก็บ metadata ไว้ใน TypeScript ปฏิเสธเพราะรายชื่อช่องจะซ้ำกับ `config.py` แล้วค่อยๆ ไม่ตรงกัน
- ทางเลือกอื่น: ส่ง `model_json_schema()` ทั้งก้อนให้ web แปลงเอง ปฏิเสธเพราะ web ต้องเข้าใจ `$defs` และ `anyOf` engine จึงส่งรายการแบบแบนที่มีแค่ข้อมูลที่ฟอร์มใช้
- comment ใน YAML ที่ซ้ำกับ description ให้ย่อเหลือแค่หน่วย เพื่อไม่ให้มีคำอธิบายสองชุด

### D3. API `/settings`

- `GET /settings` คืน `{fields: [{key, section, title, description, unit, type, options?, min?, max?, value, default}], updated_at, stale}`
- `PUT /settings` รับ `{key: value}` ของทุกช่องในฟอร์ม รวมกับ YAML แล้ว validate ถ้าผ่านก็บันทึก override ใหม่ทั้งชุดใน transaction เดียว ถ้าไม่ผ่านตอบ 422 `{"detail": {"errors": {key: ข้อความไทย}}}` และไม่เขียนอะไร key ที่ไม่ได้ติด `editable` ตอบ 422
- `DELETE /settings` ลบ override ทั้งหมดแล้วตั้ง `updated_at` เป็นเวลานั้น (reset ก็ทำให้ผลเดิมเป็นค่าเก่าได้)
- ข้อความ error ภาษาไทยมาจาก dict เล็กๆ ที่ map ชนิด error ของ pydantic (`greater_than_equal`, `less_than_equal`, `int_parsing`, `float_parsing`, `too_short`) เป็นข้อความไทย ส่วนเงื่อนไขที่ข้ามช่อง (`ocf_min_positive ≤ ocf_window`, `min_hold_months ≤ max_hold_months`) ใช้ `field_validator` ที่อ่านช่องที่ประกาศไว้ก่อนผ่าน `info.data` ให้ error ไปติดที่ช่องนั้นเลย ไม่ต้องใช้ `model_validator` ที่ไม่มีตำแหน่งช่อง

### D4. `load_config` ตัวเดียวสำหรับทุกช่องทาง

เพิ่ม `db.settings(conn)` ที่คืน override และให้ `load_config(path, overrides=None)` รวมค่าก่อน validate จุดที่รัน batch (`api.py` ทั้งสองที่, `cli.py`) ส่ง override จาก connection ที่เปิดอยู่แล้ว ส่วน `core/` ไม่ต้องแก้เพราะยังรับ `Config` เหมือนเดิม `scripts/backtest_cdc.py` ใช้ default ใน YAML ต่อไป เพื่อให้ผล backtest ใน README ทำซ้ำได้

override ที่ key ไม่มีแล้ว (เช่น ช่องถูกเอาออกจาก `editable` หรือเปลี่ยนชื่อ) ให้ข้ามพร้อม log แทนที่จะทำให้ batch ล้มเพราะ `extra="forbid"`

### D5. ป้าย "ผลใช้ค่าเก่า" เทียบ `settings.updated_at` กับ `started_at` ของ run สำเร็จล่าสุด

batch โหลด config ตอนเริ่ม จึงเทียบกับ `started_at` ไม่ใช่ `finished_at` ถ้าแก้ค่าระหว่างที่ batch กำลังรัน ผลของ run นั้นก็ยังนับว่าใช้ค่าเก่า `/candidates` และ `GET /settings` ส่ง `stale: bool` มาให้ web แสดงอย่างเดียว

- ทางเลือกอื่น: เก็บ snapshot ของ config ในทุก run ปฏิเสธเพราะยังไม่มีหน้าไหนต้องดูค่าย้อนหลัง (อยู่ใน non-goal ของ proposal)

### D6. หน้า web

- `app/settings/page.tsx` เป็น server component ที่โหลด `GET /settings` แล้วส่งให้ `settings-form.tsx` (client) ที่ใช้ `useActionState` แบบเดียวกับ `event-form.tsx` server action ใน `app/actions.ts` แปลงหน่วยแล้ว `PUT` และคืน error รายช่อง
- แปลงหน่วยใน `lib/format.ts` ด้วย `toDisplay` / `fromDisplay` ตาม `unit` (`percent` ×100, `million_baht` ÷1e6) ช่องตัวเลขใช้ `<input type="number" step="any">` ส่วนช่องที่เป็นรายการใช้ checkbox
- `Tooltip` ใน `badges.tsx` ทำด้วย CSS ล้วน: ปุ่ม ⓘ ที่ `aria-describedby` ชี้ไปที่ `role="tooltip"` และแสดงด้วย Tailwind `group-hover` / `group-focus-within` ไม่เพิ่ม library
- ปุ่ม reset ใช้ `window.confirm` ก่อนเรียก `DELETE`
- เพิ่มลิงก์ "ตั้งค่า" ใน header ของ `layout.tsx` และปุ่ม "ปรับเกณฑ์" ข้างปุ่มรัน batch บนหน้า candidates (เป็น `<Link>` ที่หน้าตาเป็นปุ่มรอง เพราะเป็นการเปลี่ยนหน้า ไม่ใช่ action) และป้ายเตือนเมื่อ `stale` ที่หน้า candidates พร้อมปุ่มรัน batch ที่มีอยู่แล้ว

## Risks / Trade-offs

- [ค่าจริงมาจากสองที่ (YAML + DB) แก้ YAML แล้วอาจงงว่าทำไมบางค่าไม่เปลี่ยน] → หน้า settings แสดงค่า default คู่กับค่าที่แก้ และทำเครื่องหมายช่องที่ override ไว้ README ของ engine บอกลำดับการรวมค่า
- [ลบ `shortlist.db` แล้ว override หายไปด้วย] → ยอมรับได้ ใช้คนเดียวและค่ามีไม่กี่ช่อง ถ้าต้องการเก็บไว้ให้ copy ค่าลง `config.yaml`
- [ลด liquidity มากๆ ทำให้ต้องดึงงบหลายตัว batch นานขึ้น (thaifin ~0.17 วินาที/ตัว ถ้าตั้ง 0 ก็ต้องดึง 930 ตัว ราว 3 นาที) และเสี่ยงโดน Finnomena จำกัดมากขึ้น] → tooltip ของ liquidity บอกผลข้อนี้ และ `min` ของช่องไม่ให้ต่ำกว่า 0
- [`stop_buffer`, `max_pe` และค่าอื่นที่ตั้งสุดขั้วยังผ่าน validate ได้ถ้าอยู่ในช่วง] → ช่วงค่าของแต่ละช่องตั้งให้กว้างพอแต่ตัดค่าที่ไม่มีความหมาย (เช่น % ต้องอยู่ระหว่าง 0–100) ที่เหลือเป็นการตัดสินใจของผู้ใช้
- [tooltip แบบ CSS อาจล้นจอบนมือถือ] → จำกัดความกว้างและให้ขึ้นบรรทัดใหม่ ตรวจบนจอแคบตอนทดสอบ
