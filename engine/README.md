# engine

Python engine: ดึงข้อมูล → ประเมิน → เก็บลง SQLite และเปิด HTTP API ให้ `web/`

```
shortlist/sources/  adapter ของ yfinance และ thaifin (แปลงเป็นรูปแบบกลาง)
shortlist/core/     pure function ของแต่ละ capability
shortlist/batch.py  ประกอบทุกส่วน
shortlist/api.py    FastAPI
scripts/            spike และ backtest
```

## ผลตรวจข้อมูล

### ROE และ PE ของ thaifin (task 2.4, 14 ต.ค. 2026)

เทียบ `roe` และ `price_earning_ratio` ของ thaifin กับค่าที่คำนวณจาก `net_profit`, `equity`, `earning_per_share` และ `close` รายไตรมาสของ PTT, CPALL, KBANK (1Q25–2Q26)

- **ROE = กำไรสุทธิไตรมาสนั้น × 4 / ส่วนผู้ถือหุ้นเฉลี่ยต้นและปลายไตรมาส** ตรงทุกไตรมาสทั้ง 3 ตัว เช่น PTT 2Q26 = 17.74% ทั้งสองทาง จึงเป็นค่า annualize จากไตรมาสเดียว ผันผวนตามไตรมาส (PTT 2Q26 แบบ TTM คือ 10.4% ไม่ใช่ 17.7%) quality gate จึงคำนวณ ROE TTM เอง (task 4.6)
- **PE ของ thaifin ใช้ทำ band ไม่ได้**: แถวเก่าคือ close / EPS สะสมตั้งแต่ต้นปี (PTT 1Q25 = 32 / 0.81 = 39.5, 2Q25 ≈ 30.5 / (0.81 + 0.76)) ส่วนแถวใหม่ใกล้ TTM แต่ไม่ตรง engine จึงคำนวณ PE = close / ผลรวม EPS 4 ไตรมาสเอง และ PBV = close / BVPS เอง
- ข้อจำกัด: ตัวเลขกำไรและส่วนผู้ถือหุ้นมาจาก thaifin เอง ยังไม่ได้เทียบกับไฟล์งบบน SET

### CDC เทียบกับ TradingView (task 3.2, 14 ต.ค. 2026)

เทียบกับ CDC ActionZone V3 2020 บน TradingView ที่ตั้งไว้ `close 12 26 1` (ราคาปิด, Fast 12, Slow 26, smoothing 1) ราคาเที่ยงวันเดียวกัน

| หุ้น | ราคาปิด | Fast engine / TradingView | Slow engine / TradingView |
|---|---:|---:|---:|
| ADVICE | 7.05 | 6.921107 / 6.921107 | 6.910085 / 6.910085 |
| OSP | 16.30 | 16.245682 / 16.245682 | 16.315701 / 16.315701 |
| PTT | 41.00 | 40.963941 / 40.963941 | 41.172002 / 41.172002 |

- ตรงกันทุกหลักทศนิยม จึงยืนยันว่าราคาจาก yfinance (ไม่ปรับปันผล) ตรงกับ TradingView และราคา 1 ปีพอให้ EMA ลู่เข้า
- สูตรเดิมใน spec (ราคาตั้งต้น ohlc4 และ AP = EMA 2) ต่างจาก chart ราว 0.2% จึงเปลี่ยน default เป็น `cdc.source: close` และ `cdc.ap_length: 1` (task 3.5) ถ้าอยากใช้สูตรเดิมให้ตั้ง `source: ohlc4` และ `ap_length: 2`

### Backtest CDC `bear-approaching` (task 3.3–3.5, 14 ต.ค. 2026)

`uv run python scripts/backtest_cdc.py` ใช้ราคา 3 ปี สูตร CDC แบบ close และ smoothing 1 และนับเฉพาะวันที่หุ้นผ่าน liquidity **ณ วันนั้น** (ไม่มี look-ahead) ได้ราคา 887 ตัว มี 389 ตัวที่เคยผ่าน liquidity ใช้เวลาราว 1.5 นาที (ถ้าโดน yfinance จำกัดอาจนานถึง 6 นาทีและได้หุ้นไม่ครบ)

| state | นับแบบ | จำนวน | % cross ใน 20 วัน | median return 20 วัน | median return 60 วัน |
|---|---|---:|---:|---:|---:|
| `bear-approaching` | ทุกวัน | 14,446 | 62.5% | −0.95% | −1.32% |
| `bear-approaching` | ครั้งที่เข้า | 2,913 | 59.9% | −1.20% | −1.95% |
| `bear-far` (baseline) | ทุกวัน | 41,949 | 33.1% | −1.60% | −2.87% |
| `bear-far` (baseline) | ครั้งที่เข้า | 3,638 | 38.4% | −1.35% | −3.07% |

- โอกาส cross ใน 20 วันสูงกว่า baseline ราว 2 เท่า จึง**คง CDC เป็น gate** (`candidates.accepted_states: [bear-approaching, just-crossed]`)
- แต่ **median return ติดลบทั้งคู่** `bear-approaching` ขาดทุนน้อยกว่าราว 0.7 จุดที่ 20 วัน และ 1.5 จุดที่ 60 วัน CDC จึงช่วยเรื่องจังหวะ (เงินแช่สั้นลง) ไม่ได้สร้างกำไรเอง กำไรต้องมาจากเกณฑ์พื้นฐานและ margin of safety
- ข้อจำกัด: ยังมี survivorship bias (yfinance ไม่มีหุ้นที่ถูกถอน), วันของหุ้นตัวเดียวกันไม่เป็นอิสระต่อกัน และยังไม่ได้เทียบกับผลตอบแทนของ SET ในช่วงเดียวกัน
- ผลรอบก่อน ๆ (สูตร ohlc4, มีและไม่มี look-ahead) ใกล้เคียงกัน ข้อสรุปจึงไม่เปลี่ยน

### Batch ทั้งตลาด (task 5.3, 14 ต.ค. 2026)

`uv run shortlist-batch` รอบแรกบนเครื่อง local (เน็ตบ้าน)

- ใช้เวลา **62 วินาที** สำหรับ 930 ตัว (ราคาทั้งตลาด + งบ 169 ตัวที่ผ่าน liquidity) ไม่โดน rate limit
- **fail 7 ตัว**: ไม่มีราคาจาก yfinance 4 ตัว (ACAP, BLISS, GSTEEL, WELL) และ thaifin ตอบ "not found" 3 ตัว (FLE, GST, TIPAK)
- funnel: ผ่าน liquidity 169 → ผ่าน quality 59 → median MoS ≥ 10% 32 → candidates 7
