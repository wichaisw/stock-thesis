# Proposal

## Why

thaifin บางครั้งมีไตรมาสล่าสุดที่มีแค่ EPS แต่ยังไม่มีกำไรสุทธิและส่วนผู้ถือหุ้น (น่าจะเพราะเก็บ EPS จากประกาศผลก่อนงบเต็ม) engine นับไตรมาสที่มี EPS เป็นไตรมาสที่รายงานแล้ว ไตรมาสครึ่งๆ นี้จึงเข้าไปอยู่ใน 4 ไตรมาสล่าสุด ROE TTM ตกเพราะ "ข้อมูลไม่ครบ" และไม่ขาดทุนเหลือ 3/4 ทั้งที่ 4 ไตรมาสก่อนหน้าครบและมีกำไรทุกไตรมาส

พบใน run 35–36 (15 ต.ค. 2026) 4 ตัวที่ผ่าน liquidity: AEONTS (2026Q3, 4 ไตรมาสก่อนหน้า ROE ≈ 11.5%), DIF (2026Q1), RBF (2026Q2), TURBO (2026Q3) สามตัวหลังไม่ผ่าน quality gate อยู่ตอนนี้ ภายใต้ rule เดิมที่ห้ามตกเกณฑ์ (ก่อน `relax-quality-gate`) AEONTS ถูกตัดผิด

## What Changes

- ไตรมาสสุดท้ายที่มี EPS มากกว่า 0 แต่ไม่มีกำไรสุทธิหรือส่วนผู้ถือหุ้น ขณะที่ไตรมาสก่อนหน้ามีครบ ถูกถือว่ายังไม่รายงาน quality gate (ROE TTM, D/E, OCF, ไม่ขาดทุน, จำนวนไตรมาส, inflection) และ fair value panel (TTM, band, Justified PBV) ใช้ไตรมาสก่อนหน้าเป็นไตรมาสล่าสุด
- EPS ของไตรมาสนั้น ≤ 0 ไม่ตัด (หุ้นอาจขาดทุน ให้ตกเกณฑ์ ROE แบบเดิมดีกว่าผ่านด้วยงบเก่า)
- ตัดแค่ไตรมาสสุดท้ายไตรมาสเดียว ไตรมาสที่ขาดตรงกลาง หรือหุ้นที่ไม่มีกำไรสุทธิเลย (เช่นกองทุน 3BBIF) ยังเป็นแบบเดิม: ROE ไม่ผ่านเพราะข้อมูลไม่ครบ และระบบไม่เดาค่าแทน
- เหตุผลของเกณฑ์จำนวนไตรมาสบอกไตรมาสที่ไม่นับ เช่น "มีงบ 55 ไตรมาส (ไม่นับ 2026Q3 ที่ยังมีแค่ EPS)" จึงเห็นได้ในหน้ารายละเอียดและข้อความที่คัดลอกให้ LLM โดยไม่ต้องแก้ UI
- backtest และ skill `stock-sanity-check` ใช้นิยามไตรมาสที่รายงานแล้วตัวเดียวกัน

นอกขอบเขต:
- ดึงกำไรสุทธิหรือส่วนผู้ถือหุ้นของไตรมาสนั้นจาก yfinance หรือแหล่งอื่น (yfinance ทับได้เฉพาะไตรมาสที่ thaifin มีอยู่แล้ว ตาม `prefer-yfinance-statements`)
- แก้ D/E และ OCF ของ thaifin ที่ไม่ตรง SET (AURA, SCGP ในผลตรวจ 15 ต.ค.) แยกเป็นเรื่องอื่นถ้าผู้ใช้ต้องการ
- ป้ายหรือคอลัมน์ใหม่บนหน้าเว็บ

ความสัมพันธ์กับ change อื่น:
- แก้ `core/quality.py` และ `core/fair_value.py` ซึ่ง `gate-on-proven-methods` (ทำครบแล้ว ยังไม่ commit) แก้อยู่ ให้ commit change นั้นก่อน apply change นี้
- ไม่บล็อกและไม่ถูกบล็อกโดย `candidate-history`, `throttle-price-download` และ `investor-type-flow` 4.1

## Capabilities

### New Capabilities

ไม่มี

### Modified Capabilities

- `quality-gate`: เพิ่ม requirement ว่าไตรมาสสุดท้ายที่งบยังไม่ครบไม่นับเป็นไตรมาสที่รายงานแล้ว ทั้งใน quality gate และ fair value panel

## Impact

- `engine/shortlist/core/quality.py` (helper ไตรมาสที่รายงานแล้ว, เหตุผลของ min_quarters), `engine/shortlist/core/fair_value.py`, `.agents/skills/stock-sanity-check/sanity.py` และ test
- candidate list อาจเพิ่มหุ้นที่เคยตกเพราะไตรมาสครึ่งๆ (DIF, RBF, TURBO ถ้าผ่านเกณฑ์อื่น) ตั้งแต่ batch ถัดไป ไม่มี migration ของ DB
