# Proposal

## Why

ป้ายใน candidate list ตอนนี้ครอบคุณภาพข้อมูลราคาและ band (ราคาไม่อัปเดต, ข้อมูลย้อนหลังไม่ครบ, ส่วนผู้ถือหุ้นเปลี่ยน) และรูปของ trade (RRR ต่ำ, upside สูงผิดปกติ) แต่ยังไม่บอกเมื่อผลของ gate อาจเปราะ กำไรที่กระโดดขึ้นครั้งเดียวทำให้ ROE TTM สูงและ PE TTM ต่ำ จึงดัน fair value ของทั้ง Justified PBV และ peer PE พร้อมกัน หุ้นแบบนี้ผ่าน gate ได้โดยไม่มีป้ายเตือน และการซื้อก่อนงบออกไม่กี่วันมีความเสี่ยงราคา gap ที่ผู้ใช้ควรเห็นในหน้า list

## What Changes

- ป้าย **กำไรกระโดด**: กำไรสุทธิ TTM ≥ 1.5 เท่าของ TTM เมื่อปีก่อน (4 ไตรมาสเดียวกันของปีก่อน) และทั้งสองค่าเป็นบวก ค่า 1.5 อยู่ใน `engine/config.yaml`
- ป้าย **งบใกล้ออก**: กำหนดส่งงบที่ประมาณของไตรมาสถัดไปที่ยังไม่มีในข้อมูล อยู่ภายใน 14 วันนับจากวันที่ราคาของ run
- ทั้งสองป้ายแสดงใน candidate list และหน้ารายละเอียด **ไม่ตัดหุ้นออก ไม่เปลี่ยนลำดับ และไม่เปลี่ยน gate**
- backtest วัดป้ายกำไรกระโดด: excess 63 วันของ candidate ที่ติดป้ายเทียบกับที่ไม่ติด แยกสองช่วงเหมือนตาราง variant ป้ายงบใกล้ออกวัดย้อนหลังไม่ได้ เพราะวันที่ทดสอบเป็นสิ้นไตรมาสซึ่งห่างกำหนดส่งงบ 45–60 วันเสมอ

## Capabilities

### New Capabilities

(ไม่มี)

### Modified Capabilities

- `quality-gate`: เพิ่มป้ายกำไรกระโดด (ไม่ใช้คัดหุ้นออก เหมือน inflection)
- `catalyst-watch`: เพิ่มป้ายงบใกล้ออก
- `candidate-list`: candidate list และหน้ารายละเอียดแสดงป้ายใหม่ทั้งสอง
- `fair-value-backtest`: ตารางเทียบ candidate ที่ติดป้ายกำไรกระโดดกับที่ไม่ติด

## Out of scope

- ป้าย gate ผ่านด้วย method เดียว (ผู้ใช้ไม่เลือก)
- ป้ายปันผลพิเศษ, book value ติดลบ, gate methods ให้ค่าห่างกัน
- ป้ายแหล่งข้อมูลไม่ตรงกัน: ตัดออกระหว่าง apply (19 ต.ค. 2026) เพราะกำไรสุทธิของ thaifin กับ yfinance ตรงกันทุกไตรมาสที่เทียบ (ต่างมากสุด 0.13%) สองแหล่งไม่เป็นอิสระต่อกัน ป้ายจึงไม่มีวันติด การตรวจที่เป็นอิสระต้องเทียบกับ SET (change แยก)
- เทียบ D/E, OCF หรือส่วนผู้ถือหุ้นระหว่างสองแหล่ง
- ป้ายงบเลยกำหนดส่ง (กำหนดส่งผ่านไปแล้วแต่ยังไม่มีงบ)
- ใช้ป้ายใดในการคัดหุ้นออกหรือเรียงลำดับ ถ้าผล backtest บอกว่าป้ายกำไรกระโดดมีข้อมูล การเปลี่ยน gate เป็น change แยก
- แก้ค่า 1.5 / 15% / 14 วันบนหน้า settings (อยู่ใน `config.yaml` เท่านั้น)
- ใส่ป้ายใหม่ในข้อความ copy ให้ LLM (spec `stock-summary-export`) เป็น change เล็กแยก

## Dependencies

- ไม่ block และไม่ถูก block โดย `throttle-price-download` (0/5) และ `investor-type-flow` (11/12) แต่ task ที่ต้องรัน batch ควรรันนอกช่วงหลังตลาดปิด (Yahoo จำกัด rate) เหมือนที่เคยตกลงไว้

## Impact

- engine: `core/quality.py` (กำไรกระโดด), `core/catalyst.py` (งบใกล้ออก), `batch.py` (ใส่ผลลง evaluation), `config.py` + `config.yaml`, `backtest.py`
- web: `lib/engine.ts` (type), `app/candidate-table.tsx`, `app/stocks/[symbol]/page.tsx`
- evaluation JSON มี field ใหม่แบบ optional run เก่ายังแสดงได้ ไม่มี migration ของ DB
- `docs/backtests/` ไฟล์ผลใหม่, `engine/README.md`, skill `fair-value-backtest`
