## 1. Engine: กฎคำตัดสิน

- [ ] 1.1 แยกสูตร stop ใน `risk_reward.py` เป็นฟังก์ชันที่รับราคาและ Slow (D3) ผล risk/reward เดิมไม่เปลี่ยน ตรวจ: `uv run pytest tests/test_risk_reward.py` ผ่านโดยไม่แก้ test เดิม
- [ ] 1.2 เพิ่มฟังก์ชัน ETA ฝั่ง bull ใน `cdc.py` (D4) โดยไม่แก้ `classify` ตรวจ: test ใน `tests/test_cdc.py` ครอบ gap แคบลง (ได้ ETA), gap กว้างขึ้น (ไม่มี ETA) และ evaluation ของ state bull ยังไม่มี `eta_days`
- [ ] 1.3 โมดูล pure `shortlist/core/exit.py` (D1, D3, D5): stop ณ วันที่ซื้อ, เคย bull นับจากวันที่ซื้อ, คำตัดสินตามลำดับ CUT > เตรียมขาย > รอ > ถือต่อ, `no_data`, เหตุผล และป้าย (กำไร/ขาดทุน %, ถือเกิน 63 วันทำการ, รอ CDC cross ครั้งแรก, ยังไม่มีงบ, ไม่มี gate method) ตรวจ: `tests/test_exit.py` มี test ต่อ scenario ของ requirement คำตัดสินทั้งหมดใน `specs/holding-exit/spec.md` (stop, CUT, ก่อน cross, เตรียมขาย, รอ/ถือต่อ, ป้าย, ไม่มีผลประเมิน, ยังไม่มีงบ)

## 2. Engine: ข้อมูลและ API

- [ ] 2.1 ตาราง `holdings` และ `add_holding`/`delete_holding`/`holdings` ใน `db.py` (D2) ตรวจ: test ใน `tests/test_db.py` ว่าเพิ่ม ลบ ซ้ำแล้วถูกปฏิเสธ และรายการคงอยู่หลัง `save_run`
- [ ] 2.2 `run()` ส่งหุ้นที่ถือเข้า `collect` และดึงงบให้หุ้นที่ถือนอก liquidity โดยดึงงบไม่ได้แล้วไม่ใส่ใน `failures` (D6) ตรวจ: test ใน `tests/test_batch.py` ด้วย fakes ว่าหุ้นที่ถือนอก liquidity มี `quality` และ `fair_value`, `liquidity.passed` ยังเป็น False, ไม่อยู่ใน candidate list, หุ้นไม่ผ่าน liquidity ที่ไม่ได้ถือยังไม่ถูกดึงงบ และดึงงบไม่ได้แล้วยังมี evaluation ที่มี CDC
- [ ] 2.3 endpoint `GET/POST /holdings` และ `DELETE /holdings/{symbol}` (D7) ตรวจ: test ใน `tests/test_api.py` ครอบ scenario ของ requirement เพิ่มและลบ (404 symbol ไม่มี, 409 ซ้ำ, 422 วันที่อนาคตหรือต้นทุน ≤ 0), การเรียงตามคำตัดสิน, `no_data` และเพิ่มหุ้นหลัง run แล้วได้คำตัดสินทันที แล้ว `uv run pytest` ผ่านทั้งหมด

## 3. Web

- [ ] 3.1 type และ client ใน `web/lib/engine.ts`, server action `addHolding`/`deleteHolding` ใน `actions.ts`, หน้า `web/app/holdings/page.tsx` พร้อมฟอร์มแบบ `EventForm` และลิงก์ "หุ้นที่ถือ" บนหน้า candidates (D7) ตรวจ: `bun run lint` ผ่าน และ browser check scenario ของ requirement หน้าหุ้นที่ถือ (ว่าง, เพิ่ม 3 ตัวแล้วเรียง CUT ก่อน, ข้อความว่ายังไม่ผ่าน backtest, วันที่ราคาของ run, error ภาษาไทยเมื่อ symbol ไม่มี, ลบได้, symbol ลิงก์ไปหน้ารายละเอียด)

## 4. ตรวจกับ batch จริงและเอกสาร

- [ ] 4.1 เพิ่มหุ้นที่ถือจริงอย่างน้อย 3 ตัว (หนึ่งตัวไม่ผ่าน liquidity) แล้วรัน batch บน DB จริง ตรวจ: candidate list และจำนวน candidate เท่ากับ run ก่อนหน้าที่ราคาเดียวกัน (ไม่มีหุ้นที่ถือนอก liquidity เข้า list), หุ้นนอก liquidity มี fair value และ quality, และสำหรับ 2 ตัว ตรวจ Fast/Slow ณ วันที่ซื้อและวันนี้, stop และ CDC state เทียบกับ TradingView (CDC ActionZone V3) หลังตลาดปิด
- [ ] 4.2 เพิ่มส่วนหุ้นที่ถือใน `engine/README.md` และ README หลัก: กฎคำตัดสิน, ว่ายังไม่ผ่าน backtest, ข้อจำกัด (สดเท่า run ล่าสุด, split หลังซื้อให้ลบแล้วเพิ่มใหม่ด้วยต้นทุนที่ปรับแล้ว, วันที่ซื้อเก่ากว่าราว 1 ปีไม่มี stop) ตรวจ: อ่านทวนว่าตรงกับ spec และ design

## Workflow follow-up

- archive change นี้หลัง 4.1 ผ่าน
- backtest กฎฝั่งขายเป็น change แยก
