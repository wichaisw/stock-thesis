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

- **ROE = กำไรสุทธิไตรมาสนั้น × 4 / ส่วนผู้ถือหุ้นเฉลี่ยต้นและปลายไตรมาส** ตรงทุกไตรมาสทั้ง 3 ตัว เช่น PTT 2Q26 = 17.74% ทั้งสองทาง จึงเป็นค่า annualize จากไตรมาสเดียว ใช้กับเกณฑ์ ROE ≥ 10% ได้ แต่ผันผวนตามไตรมาส (PTT 2Q26 แบบ TTM คือ 10.4% ไม่ใช่ 17.7%)
- **PE ของ thaifin ใช้ทำ band ไม่ได้**: แถวเก่าคือ close / EPS สะสมตั้งแต่ต้นปี (PTT 1Q25 = 32 / 0.81 = 39.5, 2Q25 ≈ 30.5 / (0.81 + 0.76)) ส่วนแถวใหม่ใกล้ TTM แต่ไม่ตรง engine จึงคำนวณ PE = close / ผลรวม EPS 4 ไตรมาสเอง และ PBV = close / BVPS เอง
- ข้อจำกัด: ตัวเลขกำไรและส่วนผู้ถือหุ้นมาจาก thaifin เอง ยังไม่ได้เทียบกับไฟล์งบบน SET

### Backtest CDC `bear-approaching` (task 3.3, 14 ต.ค. 2026)

`uv run python scripts/backtest_cdc.py` ใช้ราคา 3 ปีของหุ้นที่ผ่าน liquidity ณ วันนี้ 169 ตัว (จาก 926 ตัวที่มีราคา) ใช้เวลาราว 50 วินาที

| state | วัน | % วันที่ cross ภายใน 20 วันทำการ | ครั้งที่เข้า state | % ครั้ง |
|---|---:|---:|---:|---:|
| `bear-approaching` | 14,946 | 62.8% | 2,572 | 61.5% |
| `bear-far` (baseline) | 41,122 | 34.0% | 2,743 | 37.8% |

- `bear-approaching` cross จริงบ่อยกว่า baseline ราว 1.8 เท่า จึง**คงค่า default ให้ CDC เป็น gate** (`candidates.accepted_states: [bear-approaching, just-crossed]`) ถ้าอยากใช้ CDC เป็นตัวเรียงอย่างเดียว ให้ใส่ทั้ง 4 state
- ราว 37% ของสัญญาณยังไม่ cross ใน 20 วัน
- มี look-ahead bias: คัดหุ้นด้วยสภาพคล่องของวันนี้ ไม่ใช่ของวันในอดีต
