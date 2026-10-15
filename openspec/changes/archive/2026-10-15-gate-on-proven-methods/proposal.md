# Proposal

## Why

backtest ที่มีช่วงความเชื่อมั่น (`strengthen-fair-value-backtest`, 15 ต.ค. 2026) พบว่า candidate rule ปัจจุบัน (ผ่าน quality และ median MoS ≥ 10%) ไม่มี edge ที่ 63 วัน (excess +0.5%, t 0.90) เพราะ median เจือจาง 2 method ที่มี edge จริง (peer_pe t 3.47, justified_pbv t 3.04) ด้วย 3 method ที่เป็น noise สัดส่วน candidate จึงไหลจาก 6% ถึง 56% ของหุ้นที่ประเมินได้ spike ด้วยข้อมูลชุดเดียวกันพบว่า gate "ทุก method ที่คำนวณได้ใน peer_pe และ justified_pbv มี MoS ≥ 10%" ให้ excess +1.7% (95% CI +0.7% ถึง +2.8%, t 3.25, placebo −0.1%) ผ่านทั้งช่วง 2021–2023 (t 2.17) และ 2024–2026 (t 2.46) และเมื่อไม่นับค่าผิดปกติ (t 3.30) สัดส่วน candidate อยู่ที่ 8–26%

ข้อควรระวัง: 2 method นี้ถูกเลือกจาก 22 วันที่เดียวกัน ผลจึงเป็น in-sample บางส่วน จึงต้องเก็บ rule เดิมเป็นแถวเทียบใน backtest และรัน backtest ซ้ำทุกไตรมาส

## What Changes

- **BREAKING (ผลลัพธ์)** candidate gate ด้าน fair value เปลี่ยนจาก median MoS ≥ เกณฑ์ เป็น: ทุก method ใน `candidates.gate_methods` (default `peer_pe`, `justified_pbv`) ที่คำนวณได้มี MoS ≥ เกณฑ์ และต้องคำนวณได้อย่างน้อย 1 ตัว ถ้าไม่มีตัวไหนคำนวณได้ หุ้นไม่เป็น candidate พร้อมเหตุผลภาษาไทย ยังเป็น gate ผ่าน/ไม่ผ่าน ไม่ใช่ weighted score
- `candidates.gate_methods` อยู่ใน `config.yaml` และไม่แก้บนเว็บ เพื่อให้การเปลี่ยน method ต้องมีผล backtest รองรับ
- **BREAKING (config)** เปลี่ยนชื่อ `candidates.min_median_mos` เป็น `candidates.min_gate_mos` (default 10%) ค่าเดิมที่บันทึกบนเว็บถูกข้ามพร้อม log เตือน (loader ข้าม key ที่ไม่รู้จักอยู่แล้ว)
- **BREAKING (ผลลัพธ์)** target ของ risk/reward และตัวเรียงลำดับ MoS (ลำดับที่ 3 หลัง CDC และ ETA) ใช้ fair value ที่ต่ำกว่าของ gate methods ที่คำนวณได้ แทน median fair value candidate จึงไม่มี upside ติดลบเพราะ median ต่ำกว่าราคา
- fair value panel ยังแสดงครบทุก method พร้อม median, MoS ต่ำสุด สูงสุด และ "x/y undervalued" เหมือนเดิม panel เป็นมุมมอง ไม่ใช่ gate
- หน้า candidate list, หน้ารายละเอียด, หน้า settings และข้อความที่คัดลอกให้ LLM เปลี่ยนคำว่า median MoS ในส่วน gate และ target ให้ตรงกับ rule ใหม่
- backtest: กลุ่ม `candidate` ใช้ rule ใหม่ และเพิ่มแถวเทียบ `candidate (median)` ที่ใช้ rule เดิม
- รัน batch แล้วเทียบ candidate list ก่อน/หลัง และ spot-check หุ้นจริงเทียบ SET หรือ TradingView

นอกขอบเขต:
- relative gate (20% บน) ไม่ทำ (ทั้งแบบ median และแบบ min ของ 2 method ไม่ผ่านใน spike) แถว `candidate (relative)` ใน backtest คงไว้เป็นค่าอ้างอิง
- การตัด method ออกจาก panel หรือเปลี่ยนสูตรของ method ใด (รวม r, g ของ justified_pbv)
- การเปลี่ยน CDC state ที่รับ, quality gate หรือ liquidity filter
- การทำ backtest ซ้ำทุกไตรมาสแบบอัตโนมัติ (ใช้ skill `fair-value-backtest` ด้วยมือ)
- เกณฑ์ MoS ขั้นสูงสุด (เช่นตัด MoS ≥ 30%) แม้ bucket สูงจะให้ผลแย่ เพราะยังไม่ได้ทดสอบแยก

ความสัมพันธ์กับ change อื่น:
- ถูกบล็อกโดย batch รวมที่ค้าง (`simplify-risk-reward` 4.1, `add-fair-value-methods` 5.x, `prefer-yfinance-statements` 3.x) change นี้เปลี่ยน candidate list และ target ถ้าลงก่อน ผลเทียบของ batch รวมจะอธิบายไม่ได้ จึง implement หลัง batch รวมเสร็จ
- `simplify-risk-reward` ป้าย "upside สูงผิดปกติ" อ่าน target เดิม change นี้เปลี่ยน target จึงต้องลงหลัง 4.1 ของ change นั้น
- `relax-quality-gate` 3.x ใช้ batch รวมเดียวกัน ไม่บล็อกกันในแง่ code
- ต่อจาก `strengthen-fair-value-backtest` (commit fc03308 ยังไม่ archive) ซึ่งเพิ่มแถว `candidate (relative)` ใน spec `fair-value-backtest` ควร archive change นั้นก่อนเพื่อให้ delta ของ change นี้อิง main spec ล่าสุด

## Capabilities

### New Capabilities

ไม่มี

### Modified Capabilities

- `candidate-list`: เงื่อนไขด้าน fair value ของ candidate และตัวเรียงลำดับ MoS ใช้ gate methods แทน median
- `risk-reward`: target ใช้ fair value ที่ต่ำกว่าของ gate methods แทน median fair value
- `filter-settings`: เกณฑ์ `min_median_mos` เปลี่ยนชื่อและคำอธิบายเป็น `min_gate_mos`
- `stock-summary-export`: ข้อความให้ LLM บอก rule ของ gate และ target ใหม่
- `fair-value-backtest`: กลุ่ม candidate ใช้ rule ใหม่ และมีแถวเทียบ candidate (median)

## Impact

- `engine/shortlist/core/candidates.py`, `engine/shortlist/core/risk_reward.py`, `engine/shortlist/config.py`, `engine/config.yaml`, `engine/shortlist/backtest.py` และ test ที่เกี่ยวข้อง
- `web/app/page.tsx`, `web/app/stocks/[symbol]/page.tsx`, `web/lib/engine.ts`, `web/lib/llm-export.ts` และ test
- candidate list และ target เปลี่ยนตั้งแต่ batch ถัดไป ไม่มี migration ของ DB (evaluation เก็บแค่ run ล่าสุด)
