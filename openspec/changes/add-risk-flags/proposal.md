# Proposal

## Why

ป้ายใน candidate list ตอนนี้ครอบคุณภาพข้อมูลราคาและ band (ราคาไม่อัปเดต, ข้อมูลย้อนหลังไม่ครบ, ส่วนผู้ถือหุ้นเปลี่ยน) และรูปของ trade (RRR ต่ำ, upside สูงผิดปกติ) แต่ยังไม่บอกเมื่อผลของ gate อาจเปราะ กำไรที่กระโดดขึ้นครั้งเดียวทำให้ ROE TTM สูงและ PE TTM ต่ำ จึงดัน fair value ของทั้ง Justified PBV และ peer PE พร้อมกัน หุ้นแบบนี้ผ่าน gate ได้โดยไม่มีป้ายเตือน กำไรที่สองแหล่งข้อมูลไม่ตรงกัน (เช่น PTT ที่รวมส่วนของผู้ถือหุ้นส่วนน้อย) ก็ไม่ถูกบอก และการซื้อก่อนงบออกไม่กี่วันมีความเสี่ยงราคา gap ที่ผู้ใช้ควรเห็นในหน้า list

## What Changes

- ป้าย **กำไรกระโดด**: กำไรสุทธิ TTM ≥ 1.5 เท่าของ TTM เมื่อปีก่อน (4 ไตรมาสเดียวกันของปีก่อน) และทั้งสองค่าเป็นบวก ค่า 1.5 อยู่ใน `engine/config.yaml`
- ป้าย **แหล่งข้อมูลไม่ตรงกัน**: กำไรสุทธิไตรมาสล่าสุดของ thaifin กับ yfinance ต่างกันเกิน 15% เมื่อทั้งสองแหล่งมีค่า
- ป้าย **งบใกล้ออก**: กำหนดส่งงบที่ประมาณของไตรมาสถัดไปที่ยังไม่มีในข้อมูล อยู่ภายใน 14 วันนับจากวันที่ราคาของ run
- ทั้งสามป้ายแสดงใน candidate list และหน้ารายละเอียด **ไม่ตัดหุ้นออก ไม่เปลี่ยนลำดับ และไม่เปลี่ยน gate**
- backtest วัดป้ายกำไรกระโดด: excess 63 วันของ candidate ที่ติดป้ายเทียบกับที่ไม่ติด แยกสองช่วงเหมือนตาราง variant อีกสองป้ายวัดย้อนหลังไม่ได้ (backtest ใช้งบ thaifin อย่างเดียว และวันที่ทดสอบเป็นสิ้นไตรมาสซึ่งห่างกำหนดส่งงบ 45–60 วันเสมอ)

## Capabilities

### New Capabilities

(ไม่มี)

### Modified Capabilities

- `quality-gate`: เพิ่มป้ายกำไรกระโดด (ไม่ใช้คัดหุ้นออก เหมือน inflection)
- `market-data`: เก็บกำไรสุทธิของแหล่งงบไว้เทียบเมื่อใช้ค่าจากแหล่งราคา และติดป้ายแหล่งข้อมูลไม่ตรงกัน
- `catalyst-watch`: เพิ่มป้ายงบใกล้ออก
- `candidate-list`: candidate list และหน้ารายละเอียดแสดงป้ายใหม่ทั้งสาม
- `fair-value-backtest`: ตารางเทียบ candidate ที่ติดป้ายกำไรกระโดดกับที่ไม่ติด

## Out of scope

- ป้าย gate ผ่านด้วย method เดียว (ผู้ใช้ไม่เลือก)
- ป้ายปันผลพิเศษ, book value ติดลบ, gate methods ให้ค่าห่างกัน
- เทียบ D/E และ OCF ระหว่างสองแหล่ง (ผู้ใช้เลือกเทียบแค่กำไรสุทธิ)
- ป้ายงบเลยกำหนดส่ง (กำหนดส่งผ่านไปแล้วแต่ยังไม่มีงบ)
- ใช้ป้ายใดในการคัดหุ้นออกหรือเรียงลำดับ ถ้าผล backtest บอกว่าป้ายกำไรกระโดดมีข้อมูล การเปลี่ยน gate เป็น change แยก
- แก้ค่า 1.5 / 15% / 14 วันบนหน้า settings (อยู่ใน `config.yaml` เท่านั้น)
- ใส่ป้ายใหม่ในข้อความ copy ให้ LLM (spec `stock-summary-export`) เป็น change เล็กแยก

## Dependencies

- ไม่ block และไม่ถูก block โดย `throttle-price-download` (0/5) และ `investor-type-flow` (11/12) แต่ task ที่ต้องรัน batch ควรรันนอกช่วงหลังตลาดปิด (Yahoo จำกัด rate) เหมือนที่เคยตกลงไว้

## Impact

- engine: `core/quality.py` (กำไรกระโดด), `core/catalyst.py` (งบใกล้ออก), `sources/preferred.py` (เก็บค่าที่ไม่ตรงกัน), `batch.py` (ใส่ผลลง evaluation), `config.py` + `config.yaml`, `backtest.py`
- web: `lib/engine.ts` (type), `app/candidate-table.tsx`, `app/stocks/[symbol]/page.tsx`
- evaluation JSON มี field ใหม่แบบ optional run เก่ายังแสดงได้ ไม่มี migration ของ DB
- `docs/backtests/` ไฟล์ผลใหม่, `engine/README.md`, skill `fair-value-backtest`
