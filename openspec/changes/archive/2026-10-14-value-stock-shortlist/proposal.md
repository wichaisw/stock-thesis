# Proposal

## Why

การหาหุ้น SET ที่ "พื้นฐานดี + ราคาต่ำกว่า fair value + CDC ActionZone ใกล้ cross" ตอนนี้ต้องทำมือทีละตัว เพราะ CDC เป็น indicator ที่ดูได้ทีละหุ้น เอามา screen ทั้งตลาดไม่ได้ แล้วยังต้องเอาไปจับคู่กับงบการเงินและ thesis เองอีก screener ที่ใช้อยู่ (SET Streaming, TradingView ตัวฟรี) export ไม่ได้และ screen CDC ไม่ได้ change นี้จึงสร้าง pipeline ที่ออกรายการ candidates รายวันให้อัตโนมัติ ส่วนการคุมวินัยตาม thesis (ไม่ให้เงินหลักแสนแช่เกิน 1 ไตรมาส) แยกไปทำใน change ถัดไป

## What Changes

- **Daily batch** หลังตลาดปิด (ไม่ real-time) และมีปุ่ม trigger แบบ manual หุ้นแต่ละตัว fail ได้โดยไม่ล้มทั้ง batch
- **Universe + liquidity filter**: ตัดหุ้นที่ traded value ต่ำ เพราะหุ้นสภาพคล่องต่ำมักไม่มีแรงซื้อมา re-rate ได้เร็ว ทำให้เงินแช่นานเกิน ซึ่งคือค่าเสียโอกาส (ไม่ใช่เรื่องหาคนซื้อตอนจะขาย)
- **Quality gate** ตัดสินแบบผ่าน/ไม่ผ่าน (ROE, D/E, OCF, แนวโน้มกำไร) พร้อม inflection flag
  - ต้องมีงบอย่างน้อย 12 ไตรมาส เพื่อให้ margin of safety มาจากหุ้นที่มั่นคง
  - หุ้นการเงิน (ธนาคาร, finance, ประกัน) ข้ามเกณฑ์ D/E แล้วใช้ ROE + กำไรสม่ำเสมอแทน
- **Fair value panel**: แสดงเป็นรายการตามเกณฑ์ (PE band, PBV band, dividend yield band, peer PE) พร้อม margin of safety รายเกณฑ์ ไม่สรุปเป็นค่าเดียว
- **CDC proximity** บน timeframe daily: จัด state (`bear-far` / `bear-approaching` / `just-crossed` / `bull`), คำนวณ gap% และ ETA ถึงจุด cross
- **Catalyst watch** (ไม่ใช้เป็น gate ใน candidate list)
  - **Catalyst hints**: แนะนำ catalyst และ lead indicator ที่น่าจับตาตาม sector ของหุ้น (เช่น โรงแรม → ยอด booking, จำนวนนักท่องเที่ยว; รับเหมา → backlog, การประมูลงานภาครัฐ; สัมปทาน → ผลประมูล) เพื่อให้ผู้ใช้เอาไปเช็คต่อกับ LLM เอง
  - **Event calendar** ภายในกรอบ 6 เดือน (เผื่อตลาด buy on rumor): วันประกาศงบที่ประมาณจากกำหนดของตลาด (45 วันหลังจบไตรมาส, 60 วันสำหรับงบปี) และ SET50/100 review ส่วน XD ให้ใส่ manual
- **RRR + reward/เดือน** (entry, stop, target จาก fair value panel) สะท้อนว่าไม่อยากให้เงินแช่นาน
- **Candidate list**: รวมผลแบบ gate + sort (เรียงตาม CDC ETA และ MoS) ไม่ใช้ weighted score
- **ค่า default เริ่มต้น** ปรับได้ใน config ทั้งหมด

  | เรื่อง | default |
  |---|---|
  | Liquidity | avg traded value 20 วัน ≥ 10 ลบ./วัน |
  | Quality gate | ROE TTM ≥ 10%, D/E ≤ 1.5 (ยกเว้นการเงิน), OCF > 0 อย่างน้อย 3 ใน 4 ไตรมาสล่าสุด, ไม่ขาดทุนใน 4 ไตรมาสล่าสุด, งบ ≥ 12 ไตรมาส |
  | CDC | `bear-approaching` = ETA ≤ 20 วันทำการ, `just-crossed` = cross ภายใน 5 วัน |
  | Stop | min(swing low 20 วัน, slow EMA − 3%) |
  | Target ใน RRR | median ของ fair value panel (แสดง max ด้วย) |
  | Peer PE | หุ้นใน sector เดียวกันตาม thaifin |
  | Valuation band | median 5 ปีระดับบริษัท (market cap จากราคาจริงและจำนวนหุ้นของ yfinance ÷ กำไรหรือส่วนผู้ถือหุ้น) PE band มีเส้น median − 1SD และตัด PE > 100 |

นอกขอบเขตของ change นี้:
- **Change ถัดไป `thesis-tracking`** (Phase 2): watchlist ที่ต้องมี thesis, kill criteria (invalidation price, deadline default 90 วัน), milestone day 30/60 และ alert เมื่อ cross, โดน stop, งบออก หรือเกิน deadline ทำหลัง change นี้ใช้งานได้จริงแล้ว
- **Phase 3**: post-mortem analytics, LLM devil's advocate, การดึง catalyst อัตโนมัติ (ประกาศบน SET, backlog จาก MD&A, lead indicator ราย sector)

## Capabilities

### New Capabilities
- `market-data`: ดึงและเก็บ OHLCV รายวันกับงบการเงินรายไตรมาสของหุ้น SET/mai แบบ daily batch และ manual trigger
- `quality-gate`: เกณฑ์พื้นฐานแบบผ่าน/ไม่ผ่าน, liquidity filter, จำนวนไตรมาสขั้นต่ำ, เกณฑ์พิเศษของหุ้นการเงิน และ earnings inflection flag
- `fair-value-panel`: fair value และ margin of safety แยกตามแต่ละเกณฑ์ valuation
- `cdc-proximity`: คำนวณ CDC ActionZone, state, gap% และ ETA ถึงจุด cross
- `catalyst-watch`: catalyst/lead indicator hints ตาม sector และ event calendar ภายใน 6 เดือน
- `risk-reward`: entry/stop/target, RRR และ reward ต่อเดือน
- `candidate-list`: รวม gate ทั้งหมดแล้วเรียงเป็นรายการ candidates รายวัน

### Modified Capabilities
- (ไม่มี เป็นโปรเจกต์ใหม่)

## Impact

- **Stack**: frontend เป็น Next.js (TypeScript), backend เป็น Python เพราะ yfinance และ thaifin เป็น Python library (thaifin เวอร์ชันล่าสุดต้องใช้ Python ≥ 3.11)
- **ผู้ใช้และลำดับการ deploy**: ใช้คนเดียว ทำและใช้งานบน **local ก่อน** การ deploy ขึ้น Vercel เป็น**ขั้นสุดท้าย** หลังจากใช้งานจริงแล้วได้ผล ตอนนั้นต้องคิดเรื่องเหล่านี้
  - batch ทั้งตลาดใช้ราว 3 นาที ต้องแบ่ง batch ให้พอดี time limit ของ Vercel Cron / serverless function
  - ต้องใช้ hosted DB แทนไฟล์ local
  - IP ของ Vercel อาจถูกบล็อกจาก Yahoo/Finnomena ทางเลือกคือรัน data batch นอก Vercel (เครื่อง local หรือ GitHub Action) แล้วเขียนผลลง hosted DB ให้ Vercel อ่านอย่างเดียว
- **ข้อมูล**: ใช้ yfinance (`.BK`) สำหรับ OHLCV และ market cap ย้อนหลัง (ราคาจริง × จำนวนหุ้นย้อนหลัง) และ thaifin สำหรับงบการเงินรายไตรมาส ทั้งสองเป็น unofficial จึงต้องแยก data source ไว้หลัง interface เพื่อเปลี่ยนเป็น SETSMART API ได้ถ้า thaifin พัง
- **ข้อจำกัดของ API** (ไม่มี SLA หรือ rate limit ที่ประกาศไว้ทั้งคู่)
  - **yfinance** ([docs](https://ranaroussi.github.io/yfinance), [GitHub](https://github.com/ranaroussi/yfinance))
    - ไม่ได้เป็นของ Yahoo และ README ระบุว่า "The Yahoo! finance API is intended for personal use only" ([Yahoo terms](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html))
    - rate limit ไม่ได้ประกาศไว้ ถ้าเกินจะได้ `YFRateLimitError`
    - Yahoo มักจำกัดหรือบล็อก IP ของ datacenter
    - พังได้เมื่อ Yahoo เปลี่ยน endpoint ภายใน
    - แถวล่าสุดอาจมี `Close = NaN` และบางหุ้นไม่มีข้อมูล
  - **thaifin** ([docs](https://circleoncircles.github.io/thaifin/thaifin.html), [PyPI](https://pypi.org/project/thaifin/))
    - ไม่มีข้อมูลของตัวเอง งบการเงินดึงจาก API ภายในของ Finnomena (`finnomena.com/market-info/api/public`) ส่วนรายชื่อหุ้นและ sector ดึงจาก GitHub repo `lumduan/thai-securities-data` ที่มีผู้ดูแลคนเดียว
    - ยังไม่ได้ตรวจ terms ของ Finnomena ว่าอนุญาตให้ดึงอัตโนมัติหรือไม่ ต้องเช็คก่อนเปิดให้คนอื่นใช้
    - retry 3 ครั้งแบบ backoff 4–10 วินาที และ cache ใน memory 24 ชม. ซึ่งไม่ข้ามรอบ serverless จึงต้องเก็บข้อมูลลง DB เอง
    - error ทุกแบบถูกห่อเป็น `ValueError` แยก "ไม่พบ" กับ "โดนบล็อก" ไม่ได้
    - ต้องใช้ Python ≥ 3.11 ถ้าใช้ Python เก่ากว่าจะลง 0.2.2 ซึ่ง API ต่างกันโดยไม่เตือน
    - มีผู้ดูแลคนเดียว release ล่าสุด ก.ค. 2025
  - **ผลต่อแผน**: ใช้คนเดียวบน local ตรงกับเจตนาของทั้งสอง library ถ้าจะเปิดให้หลายคนใช้หรือใช้เชิงพาณิชย์ ต้องย้ายไป SETSMART ผ่าน data source interface
- **ผล POC** (ทดสอบ PTT, CPALL, KBANK, BH, หุ้น mai และสุ่ม 40 ตัว):
  - A1 ✅ EPS, BVPS, dividend yield รายไตรมาสย้อนหลัง 5 ปีขึ้นไปสำหรับหุ้นใหญ่ แต่ PE ของ thaifin ในแถวเก่าใช้ EPS สะสมตั้งแต่ต้นปี จึงใช้ทำ band ไม่ได้ และราคา, EPS, BVPS ต่อหุ้นย้อนหลังไม่ได้ปรับตามการแตกพาร์อย่างสม่ำเสมอ จึงต้องคำนวณ band ระดับบริษัทจาก market cap เอง ไม่มี DPS แต่คำนวณจาก yield × close ได้ บางไตรมาสมีช่องว่าง
  - A2 ✅ มี ROE, D/E, OCF (ตรวจแล้ว ROE ของ thaifin = กำไรไตรมาสเดียว × 4 ÷ ส่วนผู้ถือหุ้นเฉลี่ย จึงผันผวนตามไตรมาส quality gate จึงใช้ ROE TTM ที่คำนวณเอง)
  - A3 ⚠️ thaifin มีแถวไตรมาสล่วงหน้าที่มีแค่ราคา ต้องใช้ "ไตรมาสล่าสุดที่มี EPS" ไม่ใช่แถวล่าสุด ส่วนความช้าของงบยังวัดไม่ได้จนกว่างบ Q3 จะออก
  - A4 ✅ yfinance มี OHLCV รายวัน แต่แถวล่าสุดอาจมี Close เป็น NaN ต้องตัดแถวที่ไม่สมบูรณ์ทิ้งก่อนคำนวณ CDC
  - A5 ✅ thaifin ~0.17 วินาที/ตัว (930 ตัว ≈ 3 นาที), yfinance แบบ batch 40 ตัว ≈ 1.7 วินาที ยังไม่ได้ทดสอบทั้งตลาด จึงยังไม่รู้เรื่อง rate limit
  - A6 ⚠️ thaifin พังกับบางตัว (ValueError), yfinance ไม่มีบางตัว, หุ้น mai เล็กๆ มีงบไม่กี่ไตรมาส แก้ด้วย per-stock error handling, liquidity filter และเกณฑ์ ≥ 12 ไตรมาส
- **Phase 0 spike ต้องทำก่อน**: backtest บน SET ว่า `bear-approaching` กลายเป็น cross จริงภายใน 20 วันทำการกี่ % (นับเฉพาะวันที่หุ้นผ่าน liquidity ณ วันนั้น) และ median return 20/60 วันหลังเข้า state เทียบกับ `bear-far` ถ้าต่ำ ให้ใช้ CDC proximity เป็นตัว sort ไม่ใช่ gate
