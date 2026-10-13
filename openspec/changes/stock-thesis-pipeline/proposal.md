# Proposal

## Why

การหาหุ้น SET ที่ "พื้นฐานดี + ราคาต่ำกว่า fair value + CDC ActionZone ใกล้ cross" ตอนนี้ต้องทำมือทีละตัว เพราะ CDC เป็น indicator ที่ดูได้ทีละหุ้น เอามา screen ทั้งตลาดไม่ได้ แล้วยังต้องเอาไปจับคู่กับงบการเงินและ thesis เองอีก screener ที่ใช้อยู่ (SET Streaming, TradingView ตัวฟรี) export ไม่ได้และ screen CDC ไม่ได้ จึงต้องมี app ที่ทำ pipeline นี้อัตโนมัติ และคุมวินัยตาม thesis เพื่อไม่ให้เงินหลักแสนแช่เกิน 1 ไตรมาส

## What Changes

- **Daily batch** หลังตลาดปิด (ไม่ real-time) และมีปุ่ม trigger แบบ manual
- **Universe + liquidity filter**: ตัดหุ้นที่ traded value ต่ำ เพราะหุ้นสภาพคล่องต่ำมักไม่มีแรงซื้อมา re-rate ได้เร็ว ทำให้เงินแช่นานเกิน ซึ่งคือค่าเสียโอกาส (ไม่ใช่เรื่องหาคนซื้อตอนจะขาย) threshold ปรับได้
- **Quality gate** ตัดสินแบบผ่าน/ไม่ผ่าน (ROE, D/E, OCF, แนวโน้มกำไร) พร้อม inflection flag
- **Fair value panel**: แสดงเป็นรายการตามเกณฑ์ (PE band, PBV band, dividend yield band, peer PE) พร้อม margin of safety รายเกณฑ์ ไม่สรุปเป็นค่าเดียว
- **CDC proximity** บน timeframe daily: จัด state (`bear-far` / `bear-approaching` / `just-crossed` / `bull`), คำนวณ gap% และ ETA ถึงจุด cross
- **Catalyst window 6 เดือน** (เผื่อตลาด buy on rumor): auto (วันประกาศงบ, XD, SET50/100 review) และให้ใส่ manual ได้
- **RRR + reward/เดือน** (entry, stop, target จาก fair value panel) สะท้อนว่าไม่อยากให้เงินแช่นาน
- **Candidate list**: รวมผลแบบ gate + sort (เรียงตาม CDC ETA และ MoS) ไม่ใช้ weighted score
- **Thesis card + tracker**: watchlist ที่ต้องมี thesis, kill criteria (invalidation price, deadline default 90 วัน), milestone day 30/60 และ alert เมื่อ cross, โดน stop, งบออก หรือเกิน deadline

นอกขอบเขตของ change นี้ (phase 3): post-mortem analytics, LLM devil's advocate, การดึง catalyst อัตโนมัติขั้นสูง

## Capabilities

### New Capabilities
- `market-data`: ดึงและเก็บ OHLCV รายวันกับงบการเงินรายไตรมาสของหุ้น SET/mai แบบ daily batch และ manual trigger
- `quality-gate`: เกณฑ์พื้นฐานแบบผ่าน/ไม่ผ่าน, liquidity filter และ earnings inflection flag
- `fair-value-panel`: fair value และ margin of safety แยกตามแต่ละเกณฑ์ valuation
- `cdc-proximity`: คำนวณ CDC ActionZone, state, gap% และ ETA ถึงจุด cross
- `catalyst-window`: catalyst ที่เกิดภายใน 6 เดือน ทั้งแบบ auto และ manual
- `risk-reward`: entry/stop/target, RRR และ reward ต่อเดือน
- `candidate-list`: รวม gate ทั้งหมดแล้วเรียงเป็นรายการ candidates รายวัน
- `thesis-tracking`: watchlist, thesis card, kill criteria, milestone และ alert

### Modified Capabilities
- (ไม่มี เป็นโปรเจกต์ใหม่)

## Impact

- **ผู้ใช้**: ตอนนี้ใช้คนเดียวแบบ local ถ้าใช้ได้ผลจะ deploy frontend/backend ขึ้น Vercel ซึ่งกระทบ design ดังนี้
  - batch ต้องทำงานได้ภายใต้ time limit ของ serverless function / Vercel Cron
  - ต้องใช้ hosted DB แทนไฟล์ local
  - IP ของ Vercel อาจถูกบล็อกถ้าดึงข้อมูลแบบ scrape
- **ข้อมูล (ยังไม่ตัดสินใจ, Phase 0 spike)**: OHLCV หาได้ง่าย ส่วนงบการเงินไทยคือความเสี่ยงหลัก ตัวเลือกที่ต้อง spike คือ thaifin (unofficial), SETSMART API (official, เสียเงิน), Settrade Open API (ต้องมีบัญชี broker), EODHD (เสียเงิน)
- **Phase 0 spike ต้องทำก่อน**: backtest บน SET ว่า `bear-approaching` กลายเป็น cross จริงภายใน 20 วันทำการกี่ % ถ้าต่ำ ให้ใช้ CDC proximity เป็นตัว sort ไม่ใช่ gate
