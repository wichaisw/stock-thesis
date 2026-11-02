# Design

## Context

- batch คำนวณ gate (`fair_value.gate`, `batch.py:327`), `candidates.inclusion` (`:332`), `risk_reward.evaluate` และ `candidates.rank` (`:267`) แล้วเก็บผลทั้งก้อนเป็น JSON ใน `evaluations.result` ของทุกหุ้นที่ประเมินได้ ไม่ใช่เฉพาะ candidates
- ผลที่เก็บมี `fair_value.items` (MoS และ fair value ของทุกเกณฑ์ที่เปิดใน `fair_value.enabled`), `fair_value.summary.median_fair_value`, `risk_reward.entry`, `risk_reward.stop` (ปัดทศนิยม 2 ตำแหน่ง), `liquidity`, `quality`, `cdc`
- `GET /candidates` อ่านเฉพาะแถวที่ `candidate_rank IS NOT NULL` (`db.candidates`)
- `candidates.sort_key` ใช้ `-gate.mos` เป็นตัวตัดสินสุดท้าย ซึ่งเป็น None เมื่อไม่มี gate
- `risk_reward.evaluate` รับ prices มาหา entry/stop ตอน batch และตั้งใจไม่ fallback ไป median (design D6 เดิม)

## Goals / Non-Goals

**Goals:**
- toggle gate บนหน้า candidates คำนวณ list ใหม่จากผลที่เก็บไว้ ไม่ดึงข้อมูลใหม่
- ไม่ส่ง `gates` หรือส่งเท่ากับ config ได้ผลเหมือน batch ทุกตัวอักษร

**Non-Goals:**
- เปลี่ยน batch, config, settings, history, หน้ารายละเอียด หรือ holdings
- gate จากเกณฑ์อื่นนอก Peer PE และ Justified PBV

## Decisions

### D1: คำนวณใหม่ที่ API ตอนอ่าน ไม่ใช่ที่ batch
`GET /candidates?gates=peer_pe,justified_pbv` อ่านผลการประเมินทั้งหมดของ run ล่าสุด แล้วเรียก `fair_value.gate`, `candidates.inclusion`, risk_reward และ `candidates.rank` ชุดเดิมกับ `Candidates` config ที่แทน `gate_methods` ด้วยค่าที่เลือก (`cfg.candidates.model_copy(update=...)`) และตั้ง `candidate_rank` ใหม่ ไม่เขียน DB
- ทางเลือก: ให้ gate editable ในหน้า settings แล้วรอ batch ถัดไป → ผู้ใช้เลือกไม่เอาแล้ว ช้า และเปลี่ยน history ด้วย
- ทางเลือก: กรองที่ web ด้วย TypeScript → ต้องเขียน inclusion/sort/RRR ซ้ำเป็นภาษาที่สอง สองชุดจะเพี้ยนจากกันได้

### D2: gate เท่ากับ config → คืนแถวที่เก็บไว้ตรงๆ
เมื่อ `gates` ไม่ส่งมาหรือเป็นเซตเดียวกับ `candidates.gate_methods` ของ config ปัจจุบัน API ใช้ `db.candidates` ตามเดิม เพื่อไม่ให้ entry/stop ที่ปัดแล้วทำให้ RRR ต่างจาก batch ในหลักสุดท้าย และไม่ต้องอ่านทั้ง run
- ทางเลือก: คำนวณใหม่ทุกครั้ง → RRR อาจต่าง 0.01 จาก batch และหน้าเปิดช้าลงโดยไม่จำเป็น
- ข้อสังเกต: ถ้าแก้ `gate_methods` ใน config หลัง run ค่า default ของ checkbox จะเปลี่ยนตาม config แต่แถวที่เก็บไว้ใช้ gate เดิม กรณีนี้เทียบกับ `fair_value.gate.methods` ที่เก็บไว้ในผลแทน config (ผลเก็บ gate ของ run นั้นไว้แล้ว)

### D3: แยกส่วนคำนวณ RRR จาก prices
แยก `risk_reward.evaluate` เป็น `stop_level` (มีอยู่แล้ว) + ฟังก์ชันใหม่ที่รับ entry, stop, target, target_optimistic แล้วคืน dict เดิม batch เรียกผ่าน `evaluate` เหมือนเดิม API เรียกฟังก์ชันใหม่ด้วย entry/stop ที่เก็บไว้
- ทางเลือก: เก็บ prices ไว้คำนวณใหม่ → ไม่มีใน DB ต่อหุ้นแบบพร้อมใช้ และไม่จำเป็นเพราะ entry/stop ไม่ขึ้นกับ gate

### D4: ไม่มี gate → ผ่านทุกตัว, เรียงด้วย symbol, target = median ของ panel
`fair_value.gate` กับ methods ว่างคืน `mos=None` ซึ่ง `inclusion` ตอนนี้ตีเป็น "ไม่มี gate method ที่คำนวณได้" จึงต้องแยกกรณี "ไม่ได้เลือก gate" (methods ว่าง → ไม่เพิ่มเหตุผล) จาก "เลือกแต่คำนวณไม่ได้" `sort_key` ใช้ symbol เป็นตัวตัดสินสุดท้ายแทน `-mos` เมื่อ gate ว่าง target ใช้ `summary.median_fair_value` และ risk_reward เพิ่ม `target_source: "median"` ให้หน้าแสดงว่าที่มาไม่ใช่ gate
- ทางเลือก: target = N/A เมื่อไม่มี gate (ตาม D6 เดิม) → ผู้ใช้เลือกให้ใช้ median เพื่อยังเห็น RRR
- ทางเลือก: เรียงด้วย median MoS → ผู้ใช้ไม่ได้ขอ และ project หลีกเลี่ยง median เป็นตัวตัดสิน symbol เป็นตัวตัดสินที่เป็นกลางและคงที่

### D5: ค่าอยู่ใน URL เท่านั้น
`/?gates=justified_pbv`, `/?gates=` = ไม่มี gate, ไม่มี param = default checkbox เป็น form GET (`<form>` + checkbox name `gates`) หรือ client component ที่ `router.replace` ให้หน้า server component อ่าน `searchParams` แล้วส่งต่อให้ engine
- ทางเลือก: localStorage หรือ setting ใน DB → ผู้ใช้ไม่ได้ขอให้จำ และจะทำให้หน้าเปิดมาแล้ว list ไม่ตรงกับ batch โดยไม่รู้ตัว
- form GET ต้องแยก "ไม่ติ๊กอะไร" (browser ไม่ส่ง `gates` เลย) จาก "เปิดหน้าครั้งแรก" จึงใช้ hidden input เป็นตัวบอกว่า form ถูกส่ง หรือใช้ client component เขียน `gates=` เอง เลือกตอน implement ตามแบบของ `web/app/history` และ `search`

### D6: validate `gates` ที่ API
รับเฉพาะ `peer_pe` และ `justified_pbv` ค่าอื่นตอบ 422 พร้อมข้อความภาษาไทย หน้าเว็บแสดงข้อความนั้นแทน list และ method ที่ไม่อยู่ใน `fair_value.enabled` ของ run (ไม่มีใน items) ใช้ได้แต่ `fair_value.gate` คืนแถวเหตุผล "ปิดเกณฑ์นี้อยู่" ตามเดิม
- ทางเลือก: ทิ้งค่าที่ไม่รู้จักเงียบๆ → ลิงก์พิมพ์ผิดจะให้ list ที่ไม่ใช้ gate โดยผู้ใช้ไม่รู้

## Risks / Trade-offs

- **worst case: ผู้ใช้ปิด gate แล้วลืม เข้าซื้อหุ้นที่แพง** list ไม่มี gate รวมหุ้น MoS ติดลบมาก ป้องกันด้วยข้อความบนหน้าเมื่อ gate ไม่ตรง batch, ค่าไม่ถูกจำ (เปิดหน้าใหม่ไม่มี param = default) และ target จาก median มีป้ายบอกที่มา
- **ผล toggle ไม่ตรงกับหน้ารายละเอียดและ history** หน้ารายละเอียดยังแสดง gate และ target ของ batch ผู้ใช้อาจเห็น RRR สองค่า ยอมรับเพราะอยู่นอก scope แสดงบนหน้า candidates ว่า "ใช้ gate ต่างจาก batch" ชัดเจน
- **ไม่เคย backtest gate ชุดอื่น** หุ้นที่ได้จาก Justified PBV ตัวเดียวหรือไม่มี gate ไม่มีหลักฐานว่าดีกว่า ระบุใน tooltip ของ checkbox
- **อ่านทั้ง run ทุกครั้งที่ toggle** ~900 แถว JSON ต่อ request ยอมรับได้สำหรับผู้ใช้คนเดียวบนเครื่อง (`# ponytail:` ถ้าช้าค่อยเก็บ cache ต่อ run id)
- **run เก่าที่ไม่มี `fair_value.gate` หรือ entry/stop** อ่านแบบ tolerate (ตาม candidate-history D5) หุ้นที่ขาดค่าได้ RRR N/A
