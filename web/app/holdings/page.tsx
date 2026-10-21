import Link from "next/link";
import { Suspense } from "react";

import { deleteHolding } from "@/app/actions";
import { Tag } from "@/app/badges";
import { HoldingForm } from "@/app/holdings/holding-form";
import { engine, type HoldingsResponse, type Verdict } from "@/lib/engine";
import { baht, pct, thaiDate } from "@/lib/format";

const VERDICT: Record<Verdict, { label: string; tone: "red" | "violet" | "zinc" }> = {
  cut: { label: "CUT", tone: "red" },
  prepare: { label: "เตรียมขาย", tone: "violet" },
  wait: { label: "รอ", tone: "zinc" },
  hold: { label: "ถือต่อ", tone: "zinc" },
  no_data: { label: "ไม่มีข้อมูล", tone: "zinc" },
};

export default function HoldingsPage() {
  return (
    <Suspense fallback={<p className="text-zinc-500">กำลังโหลด…</p>}>
      <Holdings />
    </Suspense>
  );
}

async function Holdings() {
  const { price_date, holdings } = await engine<HoldingsResponse>("/holdings");
  const th = "px-3 py-2 text-left font-medium";

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">หุ้นที่ถือ</h1>
        <p className="text-sm text-zinc-500">
          คำตัดสินจากราคาปิดวันที่ {thaiDate(price_date)} (batch ล่าสุดที่สำเร็จ) ไม่ใช่ราคาระหว่างวัน ·{" "}
          <Link href="/" className="underline">
            กลับหน้า candidates
          </Link>
        </p>
      </div>
      <p role="note" className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
        กฎฝั่งขายยังไม่ผ่าน backtest ใช้เป็นสัญญาณเตือน ไม่ใช่คำสั่งขาย ตรวจราคาและงบกับ TradingView หรือ SET ก่อนตัดสินใจ
      </p>
      <HoldingForm />
      {holdings.length === 0 ? (
        <p className="text-zinc-500">ยังไม่มีหุ้นที่ถือ</p>
      ) : (
        <div className="overflow-x-auto rounded-md border border-zinc-200 dark:border-zinc-800">
          <table className="w-full text-sm">
            <thead className="bg-zinc-50 text-zinc-600 dark:bg-zinc-900 dark:text-zinc-400">
              <tr>
                <th className={th}>Symbol</th>
                <th className={th}>คำตัดสิน</th>
                <th className={`${th} text-right`}>ต้นทุน</th>
                <th className={th}>วันที่ซื้อ</th>
                <th className={`${th} text-right`}>ราคา</th>
                <th className={`${th} text-right`}>กำไร/ขาดทุน</th>
                <th className={`${th} text-right`}>Stop</th>
                <th className={th}>เหตุผล</th>
                <th className={th}>
                  <span className="sr-only">ลบ</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((h) => (
                <tr key={h.symbol} className="border-t border-zinc-200 align-top dark:border-zinc-800">
                  <td className="px-3 py-2">
                    <Link href={`/stocks/${h.symbol}`} className="font-semibold underline-offset-2 hover:underline">
                      {h.symbol}
                    </Link>
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    <Tag tone={VERDICT[h.verdict].tone}>{VERDICT[h.verdict].label}</Tag>
                  </td>
                  <td className="px-3 py-2 text-right">{baht(h.cost)}</td>
                  <td className="px-3 py-2 whitespace-nowrap">{thaiDate(h.buy_date)}</td>
                  <td className="px-3 py-2 text-right">{baht(h.price)}</td>
                  <td className={`px-3 py-2 text-right ${h.pnl != null && h.pnl < 0 ? "text-red-600" : ""}`}>{pct(h.pnl)}</td>
                  <td className="px-3 py-2 text-right">{baht(h.stop)}</td>
                  <td className="px-3 py-2">
                    <ul className="space-y-1">
                      {h.reasons.map((r) => (
                        <li key={r}>{r}</li>
                      ))}
                    </ul>
                    {h.tags.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {h.tags.map((t) => (
                          <Tag key={t}>{t}</Tag>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <form action={deleteHolding.bind(null, h.symbol)}>
                      <button className="text-red-600 hover:underline" aria-label={`ลบ ${h.symbol}`}>
                        ลบ
                      </button>
                    </form>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
