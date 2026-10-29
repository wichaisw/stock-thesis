# Proposal

## Why

บางเกณฑ์ใน fair value panel ให้ตัวเลขที่ไม่เข้ากับธุรกิจของหุ้น เช่น BEM ได้ Peer PE 2.54 และ Justified PBV 2.56 ที่ราคา 6.35 (MoS −150%) เพราะ peer ใน sector Transportation & Logistics ส่วนใหญ่เป็นเรือ สายการบิน และ logistics ส่วน Justified PBV ด้วย r 10% และ g 3% เท่ากับให้ PE ราว 10–13 เท่ากับทุกหุ้น หน้ารายละเอียดแสดงตัวเลขพวกนี้เหมือนเป็นราคาเป้าหมายปกติ จึงอ่านผิดได้ง่าย

## What Changes

- หน้ารายละเอียดหุ้นติดป้าย "fair value ไม่เข้ากับหุ้นนี้" ที่แถวของเกณฑ์ที่ MoS < −100% ทั้งใน fair value panel และตาราง gate ด้าน fair value พร้อม tooltip อธิบายสาเหตุที่พบบ่อย
- ตัวเลข fair value และ MoS ยังแสดงเหมือนเดิม
- ไม่เปลี่ยน gate, candidate rule, การเรียง, target, สรุปของ panel หรือ `engine/config.yaml`

## Capabilities

### New Capabilities

ไม่มี

### Modified Capabilities

- `fair-value-panel`: เพิ่ม requirement ป้ายเกณฑ์ที่ fair value ไม่เข้ากับหุ้น

## Impact

- `web/lib/gates.ts` และ `web/lib/gates.test.ts`: ฟังก์ชันตัดสินว่าแถวไหนติดป้าย
- `web/app/stocks/[symbol]/page.tsx`: ป้ายในสองตาราง
- engine ไม่เปลี่ยน ป้ายคิดจาก MoS ที่ batch เก็บไว้อยู่แล้ว จึงใช้กับ run เก่าได้ทันทีโดยไม่ต้องรัน batch ใหม่

## Out of scope

- เปลี่ยนวิธีคำนวณ Peer PE, Justified PBV หรือการแบ่ง peer group
- ป้ายใน candidate list, หน้า holdings และ LLM export (stock-summary-export)
- เกณฑ์ fair value > 5× ราคาที่ stock-sanity-check ใช้ด้วย ผู้ใช้เลือกเฉพาะ MoS < −100%

## Dependencies

change `backtest-ex-banking-variant` ทำ task ครบแล้วแต่ยังไม่ archive ไม่ได้แตะไฟล์เดียวกัน จึงไม่ block กัน change OCF จาก yfinance ที่จะเสนอต่อก็ไม่แตะไฟล์เดียวกัน
