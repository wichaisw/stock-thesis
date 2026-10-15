# Where the data comes from

Almost all data comes in through the **batch**. It runs on weekdays at 17:30 (after SET closes at 16:30), or when you press "รัน batch". The web pages read only what is saved in `engine/shortlist.db`. One thing bypasses the batch: the investor flow fetch button.

For the step-by-step code view, see [batch-flow.md](batch-flow.md).

## 1. The big picture

```mermaid
flowchart LR
    subgraph outside["Outside sources (unofficial, cross-checked in engine/README.md)"]
        TF["thaifin<br/>(Finnomena data)"]
        YF["yfinance<br/>(Yahoo Finance)"]
        SET["set.or.th<br/>(opened in a hidden browser)"]
    end

    YOU(["You"])

    TF -->|"stock list<br/>quarterly statements"| BATCH
    YF -->|"daily prices<br/>share count, dividends<br/>net income, equity"| BATCH
    SET -->|"today's buy/sell by investor type<br/>1-year monthly net chart"| BATCH
    SET -.->|"or the fetch button<br/>on the investor flow page"| DB

    BATCH["Batch<br/>fetch → check → score"] --> DB[("shortlist.db")]
    YOU -->|"settings page<br/>(thresholds)"| DB
    YOU -->|"your own events<br/>(stock page)"| DB

    DB --> API["Engine API :8000"] --> WEB["Web pages :3000<br/>candidates · stock detail<br/>investor flow · settings"]
```

## 2. What the batch fetches, in order

Each step only works on the stocks that made it through the step before, which keeps the slow fetches small.

```mermaid
flowchart TD
    S1["① Ask thaifin: which stocks are listed?<br/>SET + mai, about 930 stocks"]
    S2["② Ask yfinance: last 1 year of daily prices<br/>for every stock, 100 at a time"]
    S2x["No prices → listed as a failed stock"]
    S3{"③ Traded enough?<br/>average traded value over 20 days<br/>≥ your liquidity setting"}
    S3no["Not liquid: no statements fetched.<br/>Only CDC is shown on its page"]
    S4["④ For each liquid stock, fetch statements:<br/>• thaifin: every quarter it has<br/>(EPS, net profit, equity, D/E, OCF, BVPS…)<br/>• yfinance: last 5–6 quarters of<br/>net income + equity, which replace<br/>thaifin's numbers for the same quarters"]
    S5["⑤ For each liquid stock, ask yfinance:<br/>6 years of prices, share count, splits, dividends<br/>→ market cap at each quarter end"]
    S5x["Can't get statements or market cap<br/>→ listed as a failed stock"]
    S6["⑥ Compute everything from the saved numbers<br/>(no more fetching)"]
    S7["⑦ Save to shortlist.db<br/>(the previous run's results are replaced)"]
    S8["⑧ Ask set.or.th: today's buy/sell<br/>by investor type<br/>(if this fails, the run still counts)"]

    S1 --> S2
    S2 --> S2x
    S2 --> S3
    S3 -- no --> S3no --> S6
    S3 -- yes --> S4 --> S5 --> S6
    S4 --> S5x
    S5 --> S5x
    S6 --> S7 --> S8
```

## 3. Where each number on the screen comes from

```mermaid
flowchart LR
    subgraph raw["Raw data"]
        P["Daily close<br/>(yfinance)"]
        Q["Quarterly statements<br/>(thaifin + yfinance)"]
        M["Market cap per quarter<br/>(yfinance)"]
        D["Cash dividends<br/>(yfinance)"]
    end

    P --> CDC["CDC state + ETA<br/>EMA 12 vs EMA 26"]
    P --> LIQ["Liquidity gate"]
    P --> RR["Entry, stop, RRR"]
    P --> STALE["'ราคาไม่อัปเดต' tag<br/>(latest bar older than other stocks)"]
    Q --> GATE["Quality gate<br/>ROE TTM, D/E, OCF, no loss"]
    Q --> FV
    M --> FV["Fair value panel<br/>PE band, PBV band, dividend yield band,<br/>peer PE, justified PBV<br/>→ median MoS"]
    D --> FV
    FV --> RR

    LIQ & GATE & FV & CDC --> LIST["Candidate list<br/>liquid, quality gate passed, MoS ≥ 10%,<br/>CDC bear-approaching or just-crossed"]
```

## Things worth knowing

- **Prices are from yfinance, not SET.** If the batch runs before Yahoo has today's bar, some stocks show an older date. Those stocks get the "ราคาไม่อัปเดต" tag and a warning line on the candidate list.
- **yfinance overrides thaifin only for recent quarters.** yfinance has just 5–6 quarters, so the 5-year PE/PBV bands still use thaifin's history. Stocks that report in a currency other than THB (for example, PTTEP in USD) keep thaifin's numbers.
- **SET blocks normal downloads.** The engine opens its page in a hidden browser and reads the data from inside the page.
- **Only the latest run's results are kept.** Prices and statements are overwritten on every run. To compare two runs, save the candidate list before running again.
- **Every new source or field is cross-checked first.** It's compared against SET or TradingView, and the result is recorded in `engine/README.md`, before the app relies on it.
