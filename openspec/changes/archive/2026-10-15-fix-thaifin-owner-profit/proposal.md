# Proposal

## Why

spot-check ของ `backtest-fair-value` (task 3.2) พบว่า `net_profit` ของ thaifin ไม่ตรงกำไรส่วนของบริษัทใหญ่บน SET ในงบเก่า (PTT FY2022 +28.5%, FY2023 +10.6%, FY2024–2025 ตรง) ขณะที่ EPS ตรง SET ทุกปี วัดทั้ง cache ของ backtest (551 หุ้น) พบว่า 255 หุ้นมีอย่างน้อยหนึ่งไตรมาสที่ `net_profit` ต่างจาก EPS × จำนวนหุ้นเกิน 10% (14–24% ของไตรมาสก่อนปี 2024, 5–8% ตั้งแต่ 2025) PE ทุกตัวของ engine ใช้ `net_profit` จึงเพี้ยน: PE ปัจจุบันของหุ้นที่มีส่วนได้เสียที่ไม่มีอำนาจควบคุมต่ำเกินจริง, fair value ของ `peer_pe` สูงเกินจริง และ PE band เพี้ยนเมื่อสัดส่วนที่ต่างเปลี่ยนไปตามเวลา

## What Changes

- ตรวจ EPS และ `net_profit` ของ thaifin เทียบ SET และตรวจการปรับ EPS ตาม split ทั้งตลาด แล้วบันทึกใน `engine/README.md` (กฎของ project: ไม่เชื่อ field ใหม่จนกว่าจะเทียบแล้วบันทึก)
- ไม่เปลี่ยน code: ผลตรวจ (15 ต.ค. 2026) พบว่า `net_profit` ตรงกำไรส่วนของบริษัทใหญ่บน SET 33 จาก 37 ปี แต่ EPS ตรงแค่ 19 จาก 37 ปี และ 43 ไตรมาสใน 22 หุ้นไม่ถูกปรับตาม split ผู้ใช้จึงเลือกคง PE ระดับบริษัทจาก `net_profit` ไว้ (รายละเอียดใน design.md)
- ส่วนของผู้มีส่วนได้เสียที่ไม่มีอำนาจควบคุมใน `net_profit` งบเก่า (PTT FY2022–2023) เป็นข้อจำกัดที่รู้แล้ว

## Capabilities

### New Capabilities

ไม่มี

### Modified Capabilities

ไม่มี

## Impact

- `engine/README.md` (ผลตรวจ EPS และ `net_profit`) เท่านั้น ไม่มีผลต่อ code, spec, batch หรือ candidate list
