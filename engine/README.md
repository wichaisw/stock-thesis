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

### Backtest CDC `bear-approaching` (task 3.3 และ 3.4, 14 ต.ค. 2026)

`uv run python scripts/backtest_cdc.py` ใช้ราคา 3 ปี และนับเฉพาะวันที่หุ้นผ่าน liquidity **ณ วันนั้น** (ไม่มี look-ahead) รอบล่าสุดได้ราคา 731 ตัว (รอบก่อนได้ 926 ตัว และรอบนี้ใช้เวลา 6 นาทีแทน 50 วินาที น่าจะโดน yfinance จำกัด) มี 317 ตัวที่เคยผ่าน liquidity

| state | นับแบบ | จำนวน | % cross ใน 20 วัน | median return 20 วัน | median return 60 วัน |
|---|---|---:|---:|---:|---:|
| `bear-approaching` | ทุกวัน | 11,665 | 63.5% | −0.74% | −1.35% |
| `bear-approaching` | ครั้งที่เข้า | 2,145 | 62.6% | −0.83% | −1.85% |
| `bear-far` (baseline) | ทุกวัน | 33,807 | 32.7% | −1.41% | −2.07% |
| `bear-far` (baseline) | ครั้งที่เข้า | 2,663 | 36.9% | −0.93% | −2.70% |

- โอกาส cross ใน 20 วันสูงกว่า baseline ราว 2 เท่าแม้ตัด look-ahead แล้ว จึง**คง CDC เป็น gate** (`candidates.accepted_states: [bear-approaching, just-crossed]`)
- แต่ **median return ติดลบทั้งคู่** `bear-approaching` แค่ขาดทุนน้อยกว่าราว 0.7 จุด CDC จึงช่วยเรื่องจังหวะ (เงินแช่สั้นลง) ไม่ได้สร้างกำไรเอง กำไรต้องมาจากเกณฑ์พื้นฐานและ margin of safety
- ข้อจำกัด: ยังมี survivorship bias (yfinance ไม่มีหุ้นที่ถูกถอน), วันของหุ้นตัวเดียวกันไม่เป็นอิสระต่อกัน และยังไม่ได้เทียบกับผลตอบแทนของ SET ในช่วงเดียวกัน
- ผลรอบแรก (task 3.3 ใช้ liquidity ของวันนี้) คือ 62.8% เทียบ 34.0% ใกล้เคียงกัน look-ahead จึงไม่ได้ทำให้ข้อสรุปเปลี่ยน

### Batch ทั้งตลาด (task 5.3, 14 ต.ค. 2026)

`uv run shortlist-batch` รอบแรกบนเครื่อง local (เน็ตบ้าน)

- ใช้เวลา **62 วินาที** สำหรับ 930 ตัว (ราคาทั้งตลาด + งบ 169 ตัวที่ผ่าน liquidity) ไม่โดน rate limit
- **fail 7 ตัว**: ไม่มีราคาจาก yfinance 4 ตัว (ACAP, BLISS, GSTEEL, WELL) และ thaifin ตอบ "not found" 3 ตัว (FLE, GST, TIPAK)
- funnel: ผ่าน liquidity 169 → ผ่าน quality 59 → median MoS ≥ 10% 32 → candidates 7
