# Tasks

change นี้ไม่เปลี่ยนการประเมินหุ้นใน engine จึงไม่ต้องรัน batch ใหม่ ป้ายคิดจาก evaluation ที่เก็บไว้แล้ว

## 1. ป้ายในหน้ารายละเอียดหุ้น

- [ ] 1.1 เพิ่มฟังก์ชันตัดสินป้ายใน `web/lib/gates.ts` ตาม D1 (ค่าคงที่ −1 พร้อม comment ว่าตรงกับ `ABNORMAL_MOS`) ตรวจด้วย test ใน `web/lib/gates.test.ts` (−150% ติดป้าย, −100% ไม่ติด, null ไม่ติด, +20% ไม่ติด) และ `bun test lib/gates.test.ts` ผ่าน
- [ ] 1.2 แสดง `Tag` "fair value ไม่เข้ากับหุ้นนี้" พร้อม `Tooltip` ตาม D2 ในแถวของ fair value panel และตาราง gate ใน `web/app/stocks/[symbol]/page.tsx` ตรวจด้วย `bun run lint` ผ่าน และ browser check ด้วย skill `orca-browser-check` ที่หน้า BEM: แถว Peer PE และ Justified PBV ติดป้ายทั้งสองตาราง ตัวเลข 2.54 / 2.56 และ MoS ยังแสดง แถว PE band (MoS +22.7%) ไม่ติดป้าย และผล gate กับ MoS gate เท่าเดิม

## Workflow follow-up

- archive change นี้หลังผู้ใช้ดูหน้า BEM แล้ว
