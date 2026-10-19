# Proposal

## Why

gate ด้าน fair value ปัจจุบัน (`peer_pe` และ `justified_pbv` ทุกตัวที่คำนวณได้มี MoS ≥ 10%) ถูกเลือกจาก backtest ช่วง 2021–2026 ทั้งช่วง แล้ววัดผลบนข้อมูลชุดเดียวกัน (in-sample) ตอนนี้มีข้อเสนอให้เปลี่ยน gate และ quality gate (Doc 2: Option A/B, D/E 2.0, ทุกเกณฑ์ต้องผ่าน) แต่ไม่มีหลักฐานรองรับ ก่อนจะเปลี่ยน default ใดๆ ต้องรู้ก่อนว่า rule ปัจจุบันผลคงที่ในแต่ละช่วงเวลาหรือไม่ และ variant ที่เสนอดีกว่าจริงหรือแค่ได้ candidate มากขึ้น

นอกจากนี้ หลักที่ว่า CDC ต้องแยกจาก fundamental ทั้งหมดยังไม่มี test ยืนยัน มีแค่โครงสร้าง import ที่บังเอิญถูก

## What Changes

- backtest วัดกลุ่ม variant ของ candidate rule เพิ่ม ทุก variant เปลี่ยนจาก rule ปัจจุบันทีละอย่าง:
  - min MoS ของ gate 15%, 20%, 25% (10% คือ rule ปัจจุบัน = baseline)
  - Option A ของ Doc 2: gate method ตัวหนึ่ง MoS ≥ 15% และอีกตัว ≥ −10% ถ้าคำนวณได้ตัวเดียว ต้อง ≥ 12%
  - Option B ของ Doc 2: ค่าเฉลี่ย MoS ของสอง gate method ≥ 8% และไม่มีตัวไหน < −15%
  - quality: ทุกเกณฑ์ต้องผ่าน (`max_failed_checks` 0) และทุกเกณฑ์ต้องผ่านพร้อม D/E ≤ 2.0
- ไฟล์ผล backtest มีตาราง variant แยกสองช่วง (2021–2023 และ 2024–2026Q2) พร้อมจำนวน candidate ต่อวันที่ และคอลัมน์ว่า variant ผ่านเกณฑ์ที่ตั้งไว้ล่วงหน้าหรือไม่: excess เฉลี่ยสูงกว่า rule ปัจจุบันในทั้งสองช่วง และช่วงความเชื่อมั่น 95% ของ excess ทั้งช่วงไม่คร่อม 0
- เพิ่ม test ว่าการเปลี่ยนค่า CDC ไม่เปลี่ยนผล quality gate, fair value panel และ MoS gate ของหุ้นตัวเดียวกัน และการเปลี่ยนค่า fair value ไม่เปลี่ยนผล CDC
- รัน backtest แล้วรายงานผลให้ผู้ใช้ตัดสินใจ change นี้ **ไม่เปลี่ยน default ใน `engine/config.yaml` และไม่เปลี่ยน batch หรือ candidate list**

## Capabilities

### New Capabilities

(ไม่มี)

### Modified Capabilities

- `fair-value-backtest`: เพิ่มกลุ่ม variant ของ candidate rule, ตารางแยกสองช่วงเวลา และเกณฑ์ตัดสิน variant ที่ตั้งไว้ล่วงหน้า
- `cdc-proximity`: เพิ่ม requirement ว่า CDC กับ quality/fair value ไม่มีผลต่อกัน

## Out of scope

- เปลี่ยน default ของ gate, quality หรือ stop ใดๆ (ถ้า variant ผ่านเกณฑ์ เป็น change แยกที่ผู้ใช้ตัดสินใจ)
- weekly CDC และการจำลองการเทรดพร้อมค่าธรรมเนียม slippage stop (change ถัดไป ตามผล change นี้)
- รายงาน forward out-of-sample จาก `candidate_history` (change แยกราว ม.ค. 2027 เมื่อครบ 63 วันทำการ)
- สถานะ gate แบบ `REVIEW_REQUIRED` / `INSUFFICIENT_DATA`, watchlist vs eligible, valuation registry ตาม business type, bear/base/bull ของ Justified PBV
- ป้าย data integrity จาก Doc 2 (book value ติดลบ, ปันผลพิเศษ, สองแหล่งต่างกัน > 15%) เป็น change เล็กแยก
- stop = entry × 0.94 ของ Doc 2 (backtest ยังไม่จำลอง stop)

## Dependencies

- ไม่ block และไม่ถูก block โดย `throttle-price-download` (0/5) และ `investor-type-flow` (11/12) เพราะ backtest ใช้ cache ของตัวเองใน `engine/.cache/fv-backtest/` ไม่ใช้ batch หรือ DB

## Impact

- `engine/shortlist/backtest.py`: variant flags ใน `evaluate_date`, กลุ่มใน `groups`, ตารางสองช่วงใน `report`
- `engine/tests/test_backtest.py`, `engine/tests/test_batch.py` (test ความเป็นอิสระของ CDC)
- `.agents/skills/fair-value-backtest/SKILL.md`: วิธีอ่านตาราง variant
- `docs/backtests/fair-value-<date>.md` ไฟล์ผลใหม่, สรุปใน `engine/README.md`
- ไม่มี migration ไม่แตะ web
