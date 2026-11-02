# Tasks

change นี้ไม่เปลี่ยนการประเมินหุ้นใน batch (gate ของ batch, config และผลที่เก็บไว้เหมือนเดิม) จึงไม่ต้องรัน batch ใหม่ แต่ตัวเลข target/RRR ที่คำนวณใหม่ต้อง spot-check กับหุ้นจริงใน run ล่าสุด (3.2)

## 1. Engine: คำนวณ list ใหม่ตาม gate ที่เลือก

- [x] 1.1 `core/risk_reward.py`: แยกส่วนที่รับ entry, stop, target, target_optimistic ออกจาก `evaluate` ตาม D3 และรองรับ target จาก median พร้อม `target_source` ตาม D4 ตรวจด้วย test ใน `tests/test_risk_reward.py` (scenario ปิด Peer PE ได้ RRR 7.57, ไม่มี gate ใช้ median 18.00, panel ว่าง N/A) และ `uv run pytest tests/test_risk_reward.py` ผ่านทุก test เดิม
- [x] 1.2 `core/candidates.py`: gate ว่างไม่เพิ่มเหตุผล "ไม่มี gate method ที่คำนวณได้" และ `sort_key` ใช้ symbol แทน `-mos` เมื่อ gate ว่าง ตาม D4 ตรวจด้วย test ใน `tests/test_candidates.py` (ปิดทั้งสอง gate แล้วหุ้น MoS −20%/−30% ผ่าน, AAA ก่อน BBB, quality ไม่ผ่านยังถูกตัด) และ test เดิมผ่าน
- [x] 1.3 ฟังก์ชันคำนวณผลหนึ่งตัวใหม่จาก evaluation ที่เก็บไว้กับชุด gate (gate → risk_reward → inclusion) แล้ว rank ใหม่และตั้ง `candidate_rank` ตาม D1 อ่าน field แบบ tolerate run เก่า ตรวจด้วย test ว่าส่ง gate เท่ากับของ batch แล้วได้ inclusion และลำดับเท่ากับ batch บน fixture ของ `tests/test_batch.py`
- [x] 1.4 `db.py` อ่านผลการประเมินทั้งหมดของ run และ `api.py` `GET /candidates` รับ `gates` ตาม D1, D2, D6 (ไม่ส่ง/เท่ากับ gate ของ run → แถวที่เก็บไว้ตรงๆ, `gates=` = ไม่มี gate, ค่าอื่นนอก peer_pe/justified_pbv → 422 ภาษาไทย, ไม่เขียน DB) และคืน gate ที่ใช้กับ gate ของ batch ใน response ตรวจด้วย test ใน `tests/test_api.py` ครบทุก scenario ของ "Toggle gate ด้าน fair value บนหน้า candidates" ที่ตรวจที่ API ได้ และ `uv run pytest` ผ่านทั้งชุด

## 2. Web: checkbox บนหน้า candidates

- [x] 2.1 `web/app/page.tsx` อ่าน `searchParams.gates` ส่งต่อ `/candidates` และแสดง checkbox Peer PE / Justified PBV (default ตาม gate ของ batch) ที่เปลี่ยน URL ตาม D5 แยก "ไม่ติ๊กอะไร" จาก "ไม่มี param" ได้ ตรวจด้วย `bun run lint` และ browser check: เปิด `/` ได้ list เท่าเดิม, เอา Peer PE ออกแล้ว URL เป็น `?gates=justified_pbv` และ list เปลี่ยน, เปิดลิงก์นั้นในแท็บใหม่ได้ checkbox ตรง
- [x] 2.2 แสดงข้อความเมื่อ gate ไม่ตรงกับ batch และเมื่อไม่ใช้ gate ด้าน fair value, ป้าย "target จาก median" ในคอลัมน์ RRR และข้อความ 422 แทน list ตาม D4, D6 พร้อม tooltip ภาษาไทยของ checkbox ว่า gate ชุดอื่นไม่เคย backtest ตรวจด้วย `bun run lint` และ browser check ทั้ง `?gates=` และ `?gates=pe_median`

## 3. ตรวจกับข้อมูลจริง

- [x] 3.1 กับ run ล่าสุดใน `engine/shortlist.db`: เทียบ `/candidates` ไม่มี param กับ `?gates=peer_pe,justified_pbv` ว่า JSON เท่ากันทุกตัวอักษร (`jq -S`) ตรวจด้วย `diff` ว่างเปล่า
- [x] 3.2 spot-check 2 หุ้นที่เข้า list เมื่อปิด Peer PE (เช่น BEM ถ้าผ่าน) และ 1 หุ้นที่เข้า list เมื่อปิดทั้งคู่: คำนวณ target/RRR ด้วยมือจาก fair value, entry, stop ในหน้ารายละเอียด แล้วเทียบกับค่าในหน้า candidates และตรวจว่าราคาปิด (entry) ตรงกับ TradingView ณ วันที่ของ run ตรวจด้วยตัวเลขตรงกันภายใน 0.01
- [x] 3.3 ตรวจว่าหน้ารายละเอียด, `/history` และ `/holdings` ไม่เปลี่ยนหลังเล่น toggle และ `git diff --quiet engine/config.yaml` ตรวจด้วย browser check และคำสั่ง git

## Workflow follow-up

- archive หลังผู้ใช้ตรวจ 3.2
- ถ้าผู้ใช้อยากใช้ gate ชุดใหม่เป็นค่าประจำ: backtest gate ชุดนั้นก่อน (change แยก) แล้วค่อยแก้ `candidates.gate_methods`
