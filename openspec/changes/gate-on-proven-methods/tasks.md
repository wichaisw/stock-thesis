# Tasks

ก่อนเริ่ม: batch รวมที่ค้าง (`simplify-risk-reward` 4.1, `add-fair-value-methods` 5.x, `prefer-yfinance-statements` 3.x) ต้องเสร็จก่อน และเก็บ snapshot candidate list ของ run ล่าสุดไว้เทียบใน 5.1

## 1. Engine: config และ gate

- [ ] 1.1 ใน `shortlist/config.py` เปลี่ยนชื่อ `Candidates.min_median_mos` เป็น `min_gate_mos` (editable, ชื่อ/คำอธิบายภาษาไทยตาม requirement "เกณฑ์ MoS ของ gate") เพิ่ม `gate_methods: list[FairValueMethod]` แบบไม่ editable (D3) และแก้ `config.yaml` (`gate_methods: [peer_pe, justified_pbv]`, `min_gate_mos: 0.10`) แก้ tooltip ของ `fair_value.enabled` ให้บอกว่าตัวไหนเป็น gate ตรวจด้วย `uv run pytest tests/test_config.py` ที่มี test ว่า override `candidates.min_median_mos` ถูกข้ามพร้อม log เตือน และ `gate_methods` ไม่อยู่ใน `editable_fields()`
- [ ] 1.2 เพิ่ม validator ระดับ `Config` ที่ห้าม `fair_value.enabled` ไม่มี gate method เหลือ (D4) และให้ API แสดง error ที่ช่อง `fair_value.enabled` ตรวจด้วย test ใน `tests/test_config.py` (ปิดทั้งสองตัว → error, ปิดตัวเดียว → ผ่าน) และ `tests/test_api.py` (PUT settings ที่ปิดทั้งสองตัวได้ 422 ที่ key `fair_value.enabled` และค่าเดิมไม่เปลี่ยน)
- [ ] 1.3 เพิ่ม pure function gate ใน `shortlist/core/fair_value.py` ตาม D1/D2 ตรวจด้วย test ใน `tests/test_fair_value.py`: สองตัวคำนวณได้ (mos/fair_value/method เป็นตัวต่ำกว่า), ตัวเดียวคำนวณได้, ไม่มีตัวที่คำนวณได้ (None ทั้งหมด พร้อมเหตุผลของแต่ละตัว), method ที่ถูกปิดใน `enabled` นับเป็นคำนวณไม่ได้

## 2. Engine: candidate, ลำดับ และ target

- [ ] 2.1 `batch.evaluate_stock` เก็บผล gate ที่ `ev["fair_value"]["gate"]` แล้วให้ `candidates.inclusion` ใช้ rule ใหม่และเหตุผลภาษาไทยต่อ method (เช่น "MoS ของ Justified PBV 4.0% ต่ำกว่าเกณฑ์ 10%", "ไม่มี gate method ที่คำนวณได้") และ `sort_key` ใช้ MoS gate ตรวจด้วย `uv run pytest tests/test_candidates.py tests/test_batch.py` ที่ครอบทุก scenario ของ "เงื่อนไขการเข้า candidate list" และ "การเรียงลำดับ" (รวม median −5% แต่ผ่าน และ ETA เท่ากันเรียงตาม MoS gate ไม่ใช่ median)
- [ ] 2.2 `risk_reward.evaluate` ใช้ fair value ของ gate เป็น target, คง `target_optimistic` = fair value สูงสุดของ panel และเหตุผล N/A "ไม่มี gate method ที่คำนวณได้" (D6) ตรวจด้วย `uv run pytest tests/test_risk_reward.py` ตาม scenario ของ "Entry, stop และ target" และ "กรณีคำนวณ RRR ไม่ได้" และ `uv run pytest` ทั้งชุดผ่าน
- [ ] 2.3 แก้ `engine/README.md`, `docs/batch-flow.md` และ `docs/data-sources.md` ส่วนที่อธิบาย candidate rule และ target ให้เป็น gate methods ตรวจด้วย `rg -n "min_median_mos|median MoS" engine/README.md docs/batch-flow.md docs/data-sources.md` เหลือเฉพาะที่พูดถึง panel หรือผล backtest เก่า

## 3. Backtest

- [ ] 3.1 ใน `shortlist/backtest.py` เพิ่มแถว method `gate`, flag `candidate` (rule ใหม่) และ `candidate_median` (rule เดิมกับ `min_gate_mos`) และกลุ่ม `candidate (median)` ในทุกตารางตาม D5 แก้ข้อความค่าเกณฑ์ในไฟล์ผลให้บอก rule ทั้งสอง ตรวจด้วย `uv run pytest tests/test_backtest.py` ที่มี test: candidate ใช้แถว gate (hit วัดกับ fair value ของ gate), gate ผิดปกติตัดออกจาก candidate ในตาราง clean, median ผิดปกติตัดออกจาก candidate (median), ตารางต่อวันที่มีจำนวนและสัดส่วนของทั้งสาม candidate group
- [ ] 3.2 แก้ skill `fair-value-backtest` (คำอธิบายกลุ่ม candidate และแถวเทียบ) แล้วรัน backtest ด้วย cache เดิม ตรวจว่าแถว `candidate (median)` เท่ากับแถว `candidate` ของไฟล์ผล 2026-10-15 ใน git HEAD, method เดิมทุกแถวไม่เปลี่ยน และแถว `candidate` ใกล้ผล spike (63 วัน excess ≈ +1.7%, t ≈ 3.25) ถ้าต่างกันมากให้หยุดและหาสาเหตุก่อนทำ 4.x แล้วอัปเดตสรุปใน README

## 4. Web

- [ ] 4.1 เพิ่ม `gate?` (optional) ใน type `FairValue` ของ `web/lib/engine.ts` และคอลัมน์ "MoS gate" (ค่า + ชื่อ method, N/A เมื่อไม่มี `gate`) ใน `app/page.tsx` โดยเลิกเน้น median ในคอลัมน์ panel ตรวจด้วย `bun run lint` และเปิด candidate list ใน browser ว่าคอลัมน์แสดงถูกและ run เก่าไม่พัง
- [ ] 4.2 หน้ารายละเอียด `app/stocks/[symbol]/page.tsx` แสดง gate methods แต่ละตัว (MoS หรือคำนวณไม่ได้พร้อมเหตุผล เทียบเกณฑ์) ในส่วน gate และเปลี่ยนป้าย "Target (median fair value)" เป็นป้ายที่บอกว่ามาจาก gate methods ตรวจด้วย `bun run lint` และเปิดใน browser หุ้นที่ผ่าน 1 ตัว และหุ้นที่ไม่มี gate method ที่คำนวณได้
- [ ] 4.3 หน้า settings ระบุว่าเกณฑ์ไหนเป็น gate method ในตัวเลือก fair value และแสดง error ภาษาไทยเมื่อปิดทั้งสองตัว ตรวจด้วย `bun run lint` และใน browser: ปิดทั้งสองตัวแล้วบันทึกไม่ได้, ปิด PBV band บันทึกได้, ช่อง MoS ขั้นต่ำของ gate method แสดง default 10% (ใช้ `orca eval` `form.requestSubmit()` ตามที่บันทึกไว้)
- [ ] 4.4 `lib/llm-export.ts` เพิ่มบรรทัดอธิบาย gate, gate methods และ MoS gate ของหุ้น และเปลี่ยนป้าย target ตาม requirement "คำอธิบายวิธีคิด" ตรวจด้วย `bun test lib/llm-export.test.ts` ที่ครอบ scenario "อธิบาย gate และ target" และ run เก่าที่ไม่มี `gate`

## 5. Integration

- [ ] 5.1 reset `candidates.*` และ `fair_value.enabled` บนเว็บให้เป็น default (หรือยืนยันว่าเป็น default อยู่แล้ว) restart engine API แล้วรัน batch เทียบ candidate list กับ snapshot ก่อน change: จำนวน, หุ้นที่เข้าและหลุดพร้อมเหตุผล และสัดส่วนต่อหุ้นที่ประเมินได้ (คาด 8–26%) ตรวจด้วย skill `stock-sanity-check` ไม่มี outlier ใหม่จาก target
- [ ] 5.2 spot-check หุ้น candidate อย่างน้อย 3 ตัวและหุ้นที่หลุดเพราะ rule ใหม่ 2 ตัว: ราคาปิดตรงกับ SET/TradingView, MoS gate และ target ตรงกับ fair value ของ peer PE / Justified PBV ในหน้ารายละเอียด และเหตุผลที่หลุดอ่านเข้าใจ บันทึกผลใน `engine/README.md`

## Workflow follow-up

- archive `strengthen-fair-value-backtest` ก่อน archive change นี้ ไม่อย่างนั้น delta ของ `fair-value-backtest` (MODIFIED "ผลรวมแบบไม่นับค่าผิดปกติ" และ "candidate แบบ relative") จะหา header ไม่เจอ ตรวจด้วย `openspec validate gate-on-proven-methods` ที่ไม่มีข้อความ "Archive would refuse"
- ตอน archive แก้ Purpose ของ `openspec/specs/candidate-list/spec.md` ถ้ายังพูดถึง median
- รัน skill `fair-value-backtest` ทุกไตรมาส และเทียบแถว `candidate` กับ `candidate (median)`
