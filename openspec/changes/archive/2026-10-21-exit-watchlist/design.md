# Design

## Context

ทุก run เก็บ evaluation ของหุ้นทุกตัวที่ได้ราคา (ราว 920 ตัว) ใน `evaluations` แต่เก็บเฉพาะ run ล่าสุด แต่ละ evaluation มีผล CDC (`state`, `fast`, `slow`, `gap_pct`, `eta_days` เฉพาะฝั่ง bear), `quality`, `fair_value.gate` (MoS gate) และ `risk_reward.stop` `prices_daily` เก็บราคา split-adjusted ย้อนหลังราว 1 ปี (`YahooPrices.period="1y"`) ของทุกตัว และถูกเขียนทับทุก run `collect()` ใน `batch.py` ดึงงบและ market cap เฉพาะหุ้นที่ผ่าน liquidity (`liquid`) หุ้นที่ดึงงบไม่ได้ไปอยู่ใน `failures` และไม่มี evaluation เลย ข้อมูลที่ผู้ใช้ใส่เองมีแบบอย่างแล้วคือ `manual_events` + `EventForm` + server action ใน `web/app/actions.ts`

`risk_reward.stop` ใช้ low 20 วันที่รวมวันนี้ ราคาปิดวันนี้จึงต่ำกว่า stop นั้นไม่ได้ ใช้เป็นเกณฑ์ cut loss ตรง ๆ ไม่ได้ (เหตุผลของ D3)

## Goals / Non-Goals

**Goals:** คำตัดสินฝั่งขายที่อ่านจาก run ล่าสุดและ `prices_daily` ได้ทันทีที่เพิ่มหุ้น โดยไม่เปลี่ยนรูป evaluation หรือ candidate list

**Non-Goals:** เก็บคำตัดสินย้อนหลัง, ปรับกฎตามผล backtest, แก้ปัญหาข้อมูล thaifin (D/E, OCF) ที่อาจทำให้ quality ไม่ผ่านผิด ๆ

## Decisions

### D1: คำนวณคำตัดสินตอนอ่าน (API) ไม่ใช่ใน batch
`GET /holdings` อ่านหุ้นที่ถือ, evaluation ของ run ล่าสุด และ `prices_daily` ของหุ้นนั้น แล้วเรียกโมดูล pure ใหม่ `shortlist/core/exit.py` ที่รับ evaluation, ราคา, ต้นทุน, วันที่ซื้อ และ config คืนคำตัดสินพร้อมเหตุผล
- ทางเลือกคำนวณใน batch และเก็บใน evaluation: หุ้นที่เพิ่มหลัง run ต้องรอ run ถัดไป และลบหรือแก้ต้นทุนแล้วผลเก่ายังค้าง ขัดกับ scenario "เพิ่มหุ้นระหว่าง run"
- ทางเลือกคำนวณใน web (TypeScript): ต้องเขียนสูตร EMA/CDC ซ้ำ ซึ่งตอนนี้ตรงกับ TradingView เพราะอยู่ที่เดียวใน Python

### D2: ตาราง `holdings (symbol PK, cost REAL, buy_date TEXT, created_at TEXT)`
หนึ่งแถวต่อหุ้น ไม่มี endpoint แก้ไข ลบแล้วเพิ่มใหม่แทน (เกิดไม่บ่อย) `save_run` ไม่แตะตารางนี้ ตรวจ symbol กับตาราง `stocks` ของ run ล่าสุดตอนเพิ่ม
- ทางเลือกเก็บแต่ละรอบที่ซื้อ (lots): ผู้ใช้เลือกเก็บต้นทุนเฉลี่ย และการเฉลี่ยหลาย lot ไม่มีผลกับกฎใด
- ทางเลือกเพิ่ม endpoint แก้ไข: ยังไม่มีความต้องการ เพิ่มเมื่อใช้จริงแล้วลำบาก

### D3: stop คำนวณใหม่ทุกครั้งจากราคาที่ ≤ วันที่ซื้อ
แยกสูตร stop ใน `risk_reward.py` เป็นฟังก์ชันที่รับราคาและ Slow (ฝั่ง candidate ใช้ต่อแบบเดิม) แล้ว `exit.py` เรียกด้วยราคาที่ตัดถึงแท่งสุดท้าย ≤ วันที่ซื้อ และ Slow ของแท่งนั้นจาก `cdc.lines` ที่คำนวณบนราคาทั้งชุด (EMA ต้องการช่วง warm-up ก่อนหน้า) ต้องมีอย่างน้อย `cdc.min_days` แท่งถึงวันที่ซื้อ ไม่อย่างนั้น stop เป็น N/A
- ทางเลือกบันทึก stop ตอนเพิ่มหุ้น: ถ้าหุ้น split หลังซื้อ stop ที่บันทึกไว้จะไม่ถูกปรับ แต่ราคาใน `prices_daily` ถูกปรับ คำนวณใหม่จากราคาที่ปรับแล้วจึงถูกเสมอ
- ทางเลือก trailing stop: ผู้ใช้เลือก stop ณ วันที่ซื้อ (trailing whipsaw มากกว่า)
- ทางเลือกผู้ใช้กรอก stop เอง: ผู้ใช้ไม่เลือก

### D4: ETA ฝั่ง bull เป็นฟังก์ชันแยก ไม่แก้ `cdc.classify`
ฟังก์ชันใหม่ใน `cdc.py` รับ Fast/Slow คืน ETA ที่ Fast จะตัดลงใต้ Slow: gap_bull = (Fast − Slow) / Slow, speed = (gap_bull เมื่อ N วันก่อน − gap_bull วันนี้) / N, ETA = gap_bull / speed เมื่อ speed > 0 ใช้ `cdc.speed_window` และ `cdc.approaching_eta_days` เดียวกับฝั่ง bear (ผู้ใช้เลือก)
- ทางเลือกใส่ `eta_days` ให้ state bull ใน `classify`: evaluation ของ candidate `just-crossed` จะมี ETA ซึ่งหน้า candidates แสดงเป็น ETA ของการ cross ขึ้นผิดความหมาย และเปลี่ยนรูป evaluation ที่ candidate_history เก็บไว้
- ทางเลือก config ใหม่สำหรับฝั่งขาย: ผู้ใช้เลือกใช้ค่าเดียวกัน

### D5: "เคย bull นับจากวันที่ซื้อ" ดูจาก Fast > Slow บนราคาใน `prices_daily`
ใช้ `cdc.lines` บนราคาทั้งชุด แล้วดูว่ามีแท่งตั้งแต่วันที่ซื้อที่ Fast > Slow หรือไม่ วันที่ซื้อเก่ากว่าข้อมูลราคาให้นับจากแท่งแรก
- ทางเลือกใช้ state ตอนซื้อที่บันทึกไว้: ไม่รู้ว่าระหว่างนั้น cross ขึ้นแล้วหรือยัง

### D6: batch ดึงงบให้หุ้นที่ถือนอก liquidity
`run()` อ่าน symbol ใน `holdings` แล้วส่งเข้า `collect(..., held=set)` ลูปดึงงบวนบน `liquid` ต่อด้วยหุ้นที่ถือที่ได้ราคาแต่ไม่อยู่ใน `liquid` liquidity result ไม่เปลี่ยน (ยัง `passed=False`) `candidates.inclusion` จึงตัดออกเอง สำหรับหุ้นที่ถือนอก liquidity ที่ดึงงบหรือ market cap ไม่ได้ ให้ log และประเมินต่อโดยไม่มีงบ (เหมือนหุ้นไม่ผ่าน liquidity ทั่วไป) แทนการใส่ใน `failures` เพื่อไม่ให้หุ้นนั้นเสีย CDC และ stop ไปด้วย error ของงบ ยังนับเข้า `guard.record` ตามปกติ
- ทางเลือกดึงงบใน API ตอนเพิ่มหุ้น: API เรียก network และต้องคำนวณ fair value (ต้องใช้ peer PE ของทั้งตลาด) นอก batch
- ทางเลือกใส่ใน `failures` แบบหุ้นที่ผ่าน liquidity: หุ้นที่ถือจะเป็น "ไม่มีข้อมูล" ทั้งที่มีราคาครบ

### D7: API และ web
`GET /holdings` คืน `{price_date, run_id, holdings: [...]}` เรียงตามคำตัดสิน แต่ละแถวมี `verdict` (`cut` | `prepare` | `wait` | `hold` | `no_data`), `reasons` (คำตัดสินละรายการ ข้อความไทยพร้อมค่าจริง), `tags` (ป้ายข้อมูล), `pnl`, `stop` `POST /holdings` (pydantic: cost > 0, buy_date ≤ วันนี้) คืน 404 เมื่อไม่พบ symbol และ 409 เมื่อมีอยู่แล้ว `DELETE /holdings/{symbol}` หน้า `web/app/holdings/page.tsx` เป็น server component ฟอร์มเป็น client component แบบ `EventForm` ใช้ server action `addHolding`/`deleteHolding` ใน `actions.ts` ลิงก์ "หุ้นที่ถือ" เพิ่มข้าง "ประวัติ candidate" ใน `page.tsx`
- ทางเลือกรวมไว้ในหน้า candidates: หน้าแรกยาวขึ้นและปนสองคำถาม (ซื้ออะไร vs ขายอะไร)

## Risks / Trade-offs

- **กรณีแย่สุด: หน้าบอกถือต่อหรือรอ ขณะที่ราคา gap หลุด stop ไปแล้ว** คำตัดสินสดเท่ากับ run ล่าสุด (cron 17:30) ไม่ใช่ราคาระหว่างวัน และไม่มีการแจ้งเตือน ถ้า batch fail หลายวันคำตัดสินจะค้าง → หน้าแสดงวันที่ราคาของ run ที่ใช้ทุกครั้ง ผู้ใช้ต้องดู TradingView เองระหว่างวัน
- **กฎยังไม่ผ่าน backtest** คำตัดสินอาจดูน่าเชื่อเท่า candidate list ทั้งที่ backtest พิสูจน์แค่ gate ฝั่งเข้า และบันทึกเดิมบอกว่า CDC ช่วยจังหวะ ไม่ใช่กำไร → ข้อความบนหน้า และ backtest ฝั่งขายเป็น change แยก
- **ETA ฝั่ง bull แกว่ง** แบบเดียวกับฝั่ง bear (III ETA 24.4 → 9.9 วันจากราคาขยับ −0.4%) คำตัดสินเตรียมขายจะเปิดปิดสลับวัน → แสดงค่า ETA ในป้ายให้เห็นว่ากระชั้นแค่ไหน
- **CUT ผิดจาก quality** ข้อมูล thaifin บางตัวต่างจาก SET (D/E ของ AURA 2.81 vs 2.36, ผลรวม OCF) อาจทำให้ไม่ผ่าน quality ทั้งที่ SET ผ่าน → ป้ายแสดงเกณฑ์และค่าจริง ให้ผู้ใช้ตรวจกับ SET ก่อนขาย
- **split หลังซื้อ** ราคาใน `prices_daily` ถูกปรับแต่ต้นทุนที่ผู้ใช้กรอกไม่ถูกปรับ กำไร/ขาดทุน % และคำตัดสินรอ (เทียบต้นทุน) จะผิด stop ไม่ผิด (D3) → บันทึกใน README ให้ลบแล้วเพิ่มใหม่ด้วยต้นทุนที่ปรับแล้ว
- **วันที่ซื้อเก่ากว่าราว 1 ปี** ไม่มีราคา ณ วันที่ซื้อ stop เป็น N/A และกฎ CUT เหลือ CDC กับ quality → แสดงเหตุผลบนแถว
- **batch ช้าขึ้น** เท่าจำนวนหุ้นที่ถือที่ไม่ผ่าน liquidity (ราว 1 วินาทีต่อตัว) ไม่มีผลกับเพดาน 20 นาที
