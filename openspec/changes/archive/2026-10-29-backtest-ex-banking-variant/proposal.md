# Proposal

## Why

ผลแยกตาม sector จาก cache ของ backtest 2026-10-19 พบว่า edge ของกลุ่ม candidate (+1.7%, t 3.25) พึ่งหุ้นธนาคาร 7 ตัว (KTB, BAY, TCAP, BBL, KKP, KBANK, SCB) เมื่อไม่นับ Banking เหลือ +1.0% (t 1.93) และช่วง 2024 เป็นต้นไปเหลือ +0.9% (t 0.96) ถ้าแบงก์ไทยหมดรอบ rerate แล้ว candidate rule อาจไม่มี edge เหลือ ไฟล์ผลตอนนี้ไม่แสดงเรื่องนี้ จึงต้องมีตัววัดที่ตั้งเกณฑ์ไว้ก่อน และเห็นได้ทุกครั้งที่รัน backtest

## What Changes

- ไฟล์ผล backtest มีตารางใหม่ที่แยกกลุ่ม candidate เป็นหุ้นใน sector Banking และหุ้นนอก Banking แยกสองช่วงเดียวกับตาราง variant (2021Q1–2023Q4 และ 2024Q1 ขึ้นไป) พร้อมผลทั้งช่วง
- ตารางบอกว่า "edge นอกธนาคาร: มี" เมื่อ excess เฉลี่ย 63 วันของ candidate นอก Banking เป็นบวกทั้งสองช่วง และขอบล่างของ 95% CI ทั้งช่วงมากกว่า 0 ไม่ต้องชนะกลุ่ม candidate
- เป็นตัววัดใน backtest เท่านั้น ไม่เปลี่ยน candidate rule, batch หรือ `engine/config.yaml`

## Capabilities

### New Capabilities

ไม่มี

### Modified Capabilities

- `fair-value-backtest`: เพิ่ม requirement ตารางแยก candidate ใน Banking และนอก Banking พร้อมเกณฑ์ "edge นอกธนาคาร" ที่ตั้งไว้ล่วงหน้า

## Impact

- `engine/shortlist/backtest.py`: แถวที่ประเมินแต่ละแถวมี sector เพิ่ม ฟังก์ชันใหม่สำหรับตารางนี้ และส่วนใหม่ในรายงาน
- `engine/tests/test_backtest.py`: test ของเกณฑ์ตัดสินและการแยกกลุ่ม
- `.agents/skills/fair-value-backtest/SKILL.md`: วิธีอ่านตารางใหม่
- ตัวเลขของกลุ่มเดิมทุกตารางต้องไม่เปลี่ยน

## Out of scope

- เปลี่ยน candidate rule หรือ gate method ตามผลของตารางนี้ (ถ้าจะเปลี่ยน ต้องทำเป็น change แยกที่ผู้ใช้ตัดสินเอง)
- แบ่ง peer group ของ Transportation & Logistics ใหม่ ผลแยก sector พบว่า candidate ใน sector นี้ได้ excess ใกล้ 0 (+0.4% ต่อ pick) จึงแทบไม่กระทบผลรวม
- การแสดง fair value ที่ MoS ต่ำกว่า −100% เช่น BEM ในหน้า UI
- ตรวจ OCF ติดลบของหุ้นสัมปทาน (BEM) ที่อาจมาจาก TFRIC 12
- การวัดแยกตาม sector อื่นนอกจาก Banking

## Dependencies

ไม่มี change อื่นที่ยังทำไม่เสร็จ change นี้ไม่ได้ block และไม่ถูก block
