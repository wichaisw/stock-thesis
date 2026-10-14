# Tasks

## 1. Metadata ของ config

- [x] 1.1 เพิ่ม `Field(title, description, ge/le, json_schema_extra={"editable": True, "unit": ...})` ให้ทุกช่องที่ spec ให้แก้ได้ใน `shortlist/config.py` (design D2) เขียน tooltip ภาษาไทยที่บอกว่าค่านี้ใช้ทำอะไร และเพิ่มหรือลดแล้วผลเปลี่ยนอย่างไร แล้วย่อ comment ใน `config.yaml` ที่ซ้ำกับ description ตรวจด้วย test ว่าทุกช่องที่ `editable` มี title, description และ unit และสูตร CDC, `financial_sectors`, `catalyst`, `batch` ไม่ได้ติด `editable`
- [x] 1.2 เพิ่ม `field_validator` ของ `ocf_min_positive ≤ ocf_window` และ `min_hold_months ≤ max_hold_months` และ `min_length=1` ของ `enabled` / `accepted_states` ตรวจด้วย test ว่า error ติดที่ช่องที่ถูกต้อง และ `test_loads_defaults` เดิมยังผ่าน
- [x] 1.3 ให้ `load_config(path, overrides=None)` รวม override แบบ key `section.field` ก่อน validate และข้าม key ที่ไม่ได้ `editable` หรือไม่มีแล้วพร้อม log (design D4) ตรวจด้วย test: override ROE เป็น 0.08 แล้วได้ 0.08, key ที่ไม่มีถูกข้าม และช่องที่ไม่ override ใช้ default ใน YAML ไฟล์ทดสอบ

## 2. เก็บค่าและ API

- [x] 2.1 เพิ่มตาราง `settings` และฟังก์ชัน `db.settings`, `db.save_settings`, `db.reset_settings`, `db.settings_stale` (design D1, D5) ตรวจด้วย test บน DB ชั่วคราว: บันทึกแล้วอ่านกลับได้, ค่าที่เท่ากับ default ไม่ถูกเก็บ, reset ลบ override และเปลี่ยน `updated_at`, `stale` เป็นจริงเมื่อ `updated_at` อยู่หลัง `started_at` ของ run สำเร็จล่าสุด
- [x] 2.2 เพิ่ม `GET/PUT/DELETE /settings` ใน `api.py` พร้อมข้อความ error ภาษาไทยรายช่อง และเพิ่ม `stale` ใน `/candidates` (design D3, D5) ตรวจด้วย test ใน `tests/test_api.py` ทุก scenario ของ requirement "Validate ก่อนบันทึก" และ "Reset กลับเป็น default" รวมถึง key ที่ไม่ได้ `editable` ตอบ 422
- [x] 2.3 ให้ `POST /runs`, การรันใน background, หน้ารายละเอียดหุ้น และ `cli.py` ใช้ `load_config` พร้อม override จาก DB ตรวจด้วย test ใน API: บันทึก liquidity ให้สูงจน AAA ไม่ผ่าน แล้วรัน batch และดูว่า AAA ไม่ผ่าน liquidity และป้าย `stale` หายหลังรันเสร็จ จากนั้นรัน `uv run pytest` ให้ผ่านทั้งหมด
- [x] 2.4 อธิบายใน `engine/README.md` ว่าค่าจริงมาจาก `config.yaml` รวมกับค่าที่แก้บนเว็บที่เก็บใน `shortlist.db` และช่องไหนแก้ได้เฉพาะใน YAML ตรวจว่าคำอธิบายตรงกับ test ใน 1.3
- [ ] 2.5 ให้ batch ที่เริ่มจาก `POST /runs` ส่ง `log` ให้ `batch.execute` ด้วย logger ของ engine เพื่อให้ funnel (ผ่าน liquidity, candidates, fail) ขึ้นใน log ของ engine เหมือน CLI ตรวจด้วย test ใน `tests/test_api.py` ที่ใช้ `caplog` ว่ารัน batch ผ่าน API แล้วมีบรรทัด "ผ่าน liquidity"

## 3. หน้า settings บนเว็บ

- [x] 3.1 เพิ่ม type ของ `/settings` ใน `lib/engine.ts` และ `toDisplay` / `fromDisplay` ใน `lib/format.ts` (design D6) ตรวจด้วย `bun run lint` และ `bunx tsc --noEmit` ผ่าน
- [x] 3.2 เพิ่ม `Tooltip` แบบ CSS ใน `app/badges.tsx` ที่แสดงตอน hover และ focus และใช้ `aria-describedby` ตรวจในเบราว์เซอร์ด้วย skill `orca-browser-check` ว่า hover และกด Tab แล้ว tooltip ขึ้น และไม่ล้นจอที่ความกว้าง 375px
- [x] 3.3 ทำ `app/settings/page.tsx` และ `settings-form.tsx` ที่แสดงทุกช่องแบ่งตามหมวด, ค่า default, เครื่องหมายช่องที่แก้แล้ว, checkbox ของ `enabled` / `accepted_states`, error รายช่อง และปุ่ม reset ที่ถามยืนยันก่อน เพิ่ม server action `saveSettings` / `resetSettings` ใน `app/actions.ts` ตรวจในเบราว์เซอร์: แก้ liquidity เป็น 3 แล้วบันทึก, reload แล้วค่ายังเป็น 3, กรอก D/E เป็น −1 แล้วเห็น error ที่ช่อง D/E และไม่มีค่าใดถูกบันทึก
- [x] 3.4 เพิ่มลิงก์ "ตั้งค่า" ใน header ของ `app/layout.tsx` และป้ายเตือน `stale` พร้อมปุ่มรัน batch บนหน้า candidates และหน้า settings ตรวจในเบราว์เซอร์ว่าป้ายขึ้นหลังบันทึก และหายหลังรัน batch สำเร็จ
- [ ] 3.5 เพิ่มปุ่ม "ปรับเกณฑ์" ที่เป็น `Link` ไป `/settings` ข้างปุ่มรัน batch บนหน้า candidates ตรวจในเบราว์เซอร์ว่ากดแล้วไปหน้า settings, focus ด้วยคีย์บอร์ดได้ และที่ความกว้าง 375px ปุ่มทั้งสองไม่ล้นจอ
- [ ] 3.6 แก้ส่วน "แก้เกณฑ์" ใน `README.md` ที่ root ให้บอกว่าเกณฑ์กรองหุ้นแก้ได้ที่หน้า settings ของเว็บ (ค่าเก็บใน `shortlist.db`) ส่วน `config.yaml` เป็นค่า default และที่แก้สูตร CDC, sector การเงิน, catalyst และ batch ตรวจว่าตรงกับ `engine/README.md` ส่วน "ค่าเกณฑ์มาจากไหน"

## 4. ตรวจทั้งระบบ

- [ ] 4.1 ลด liquidity บนเว็บแล้วรัน batch จริงจาก UI ตรวจว่า funnel ใน log ของ engine มีหุ้นผ่าน liquidity มากกว่า 169 ตัว (ผลรอบที่ใช้ 10 ลบ./วัน ใน `engine/README.md`) แล้วรัน `uv run shortlist-batch` และดูว่า CLI ใช้ค่าเดียวกัน จากนั้นให้ผู้ใช้อ่าน tooltip ทุกช่องและยืนยันว่าเข้าใจได้
