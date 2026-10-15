import { Suspense } from "react";

import { Tag } from "@/app/badges";
import { FetchButton } from "@/app/investor-flow/fetch-button";
import { NetLineChart } from "@/app/investor-flow/line-chart";
import { engine, INVESTOR_TYPES, type InvestorFlowDay, type InvestorType, type MonthlyNetPoint } from "@/lib/engine";
import { thaiDate, thaiDateTime } from "@/lib/format";

// enough trading days for about a year of the daily chart; the table shows the newest TABLE_DAYS
const CHART_DAYS = 250;
const TABLE_DAYS = 60;

function shortDate(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("th-TH", { day: "numeric", month: "short", year: "2-digit" });
}

/** Oldest first, each type's buy − sell summed from the first day. */
function cumulativeNet(days: InvestorFlowDay[]) {
  const sum = Object.fromEntries(INVESTOR_TYPES.map((t) => [t, 0])) as Record<InvestorType, number>;
  return [...days].reverse().map((d) => {
    for (const t of INVESTOR_TYPES) sum[t] += d[`${t}_buy`] - d[`${t}_sell`];
    return { label: shortDate(d.date), values: { ...sum } };
  });
}

function thaiMonth(month: string): string {
  return new Date(`${month}-01T00:00:00`).toLocaleDateString("th-TH", { month: "short", year: "2-digit" });
}

const LABEL: Record<InvestorType, string> = {
  institution: "สถาบันในประเทศ",
  proprietary: "บัญชีบริษัทหลักทรัพย์",
  foreign: "ต่างชาติ",
  individual: "รายย่อยในประเทศ",
};

function million(x: number, signed = false): string {
  const s = (x / 1e6).toLocaleString("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return signed && x > 0 ? `+${s}` : s;
}

function netTone(x: number): string {
  return x > 0 ? "text-green-700 dark:text-green-400" : x < 0 ? "text-red-700 dark:text-red-400" : "";
}

export default function InvestorFlowPage() {
  return (
    <Suspense fallback={<p className="text-zinc-500">กำลังโหลด…</p>}>
      <FlowTable />
    </Suspense>
  );
}

async function FlowTable() {
  const [history, monthly] = await Promise.all([
    engine<InvestorFlowDay[]>(`/investor-flow?limit=${CHART_DAYS}`),
    engine<MonthlyNetPoint[]>("/investor-flow/monthly"),
  ]);
  const days = history.slice(0, TABLE_DAYS);
  const th = "px-3 py-2 font-medium";
  const cell = "px-3 py-2 text-right whitespace-nowrap";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">มูลค่าซื้อขายตามประเภทนักลงทุน</h1>
          <p className="text-sm text-zinc-500">ตลาด SET หน่วยล้านบาท สุทธิ = ซื้อ − ขาย</p>
        </div>
        <FetchButton />
      </div>

      {monthly.length === 0 ? (
        <p className="rounded-md border border-dashed border-zinc-300 p-8 text-center text-zinc-500 dark:border-zinc-700">
          ยังไม่มีข้อมูลกราฟรายเดือน กราฟจะแสดงหลังดึงข้อมูลประเภทนักลงทุนสำเร็จครั้งแรก
        </p>
      ) : (
        <NetLineChart
          title="มูลค่าสุทธิสะสมรายเดือน ย้อนหลัง 1 ปี"
          ariaLabel="กราฟเส้นมูลค่าสุทธิสะสมรายเดือน"
          labels={LABEL}
          points={monthly.map((p) => ({
            label: thaiMonth(p.month),
            values: Object.fromEntries(INVESTOR_TYPES.map((t) => [t, p[`${t}_net`]])) as Record<InvestorType, number>,
          }))}
          caption={
            <>
              มูลค่าสะสมสุทธิ (ซื้อ − ขาย) รายเดือนย้อนหลัง 1 ปี นับสะสมจากเดือนแรกของกราฟ หน่วยล้านบาท
              จุดเดือนล่าสุดคือค่าถึงวันที่ดึง · ที่มา SET · ดึงเมื่อ {thaiDateTime(monthly[0].fetched_at)}
            </>
          }
        />
      )}

      {history.length < 2 ? (
        <p className="rounded-md border border-dashed border-zinc-300 p-8 text-center text-zinc-500 dark:border-zinc-700">
          ข้อมูลรายวันยังไม่พอวาดกราฟ (ต้องมีอย่างน้อย 2 วัน)
        </p>
      ) : (
        <NetLineChart
          title="มูลค่าสุทธิสะสมรายวัน"
          ariaLabel="กราฟเส้นมูลค่าสุทธิสะสมรายวัน"
          labels={LABEL}
          points={cumulativeNet(history)}
          caption={
            <>
              มูลค่าสะสมสุทธิ (ซื้อ − ขาย) รายวัน นับสะสมจาก {thaiDate(history[history.length - 1].date)} ถึง{" "}
              {thaiDate(history[0].date)} ({history.length.toLocaleString("th-TH")} วันทำการ) หน่วยล้านบาท
              นับเฉพาะวันที่มีข้อมูล วันที่ขาดไม่ถูกรวม
            </>
          }
        />
      )}

      {days.length === 0 ? (
        <p className="rounded-md border border-dashed border-zinc-300 p-8 text-center text-zinc-500 dark:border-zinc-700">
          ยังไม่มีข้อมูล ข้อมูลจะเริ่มสะสมเมื่อรัน batch หลังตลาดปิด (SET ให้เฉพาะวันล่าสุด จึงย้อนหลังไม่ได้)
        </p>
      ) : (
        <div className="overflow-x-auto rounded-md border border-zinc-200 dark:border-zinc-800">
          <table className="w-full text-sm">
            <thead className="bg-zinc-50 text-zinc-600 dark:bg-zinc-900 dark:text-zinc-400">
              <tr>
                <th rowSpan={2} className={`${th} text-left`}>
                  วันที่
                </th>
                {INVESTOR_TYPES.map((t) => (
                  <th key={t} colSpan={3} className={`${th} border-l border-zinc-200 text-center dark:border-zinc-800`}>
                    {LABEL[t]}
                  </th>
                ))}
              </tr>
              <tr>
                {INVESTOR_TYPES.map((t) => (
                  <SideHeaders key={t} th={th} />
                ))}
              </tr>
            </thead>
            <tbody>
              {days.map((d) => (
                <tr key={d.date} className="border-t border-zinc-200 dark:border-zinc-800">
                  <td className="px-3 py-2 whitespace-nowrap">
                    {thaiDate(d.date)}{" "}
                    {d.intraday && (
                      <Tag title={`ดึงเมื่อ ${thaiDateTime(d.fetched_at)} ก่อนตลาดปิด`}>ระหว่างวัน</Tag>
                    )}
                    {d.source === "infoquest" && (
                      <Tag title="เติมย้อนหลังจากข่าวสรุปรายวันของ InfoQuest ตรวจกับข้อมูลจาก SET แล้ว">InfoQuest</Tag>
                    )}
                  </td>
                  {INVESTOR_TYPES.map((t) => {
                    const net = d[`${t}_buy`] - d[`${t}_sell`];
                    return [
                      <td key={`${t}-buy`} className={`${cell} border-l border-zinc-200 dark:border-zinc-800`}>
                        {million(d[`${t}_buy`])}
                      </td>,
                      <td key={`${t}-sell`} className={cell}>
                        {million(d[`${t}_sell`])}
                      </td>,
                      <td key={`${t}-net`} className={`${cell} font-medium ${netTone(net)}`}>
                        {million(net, true)}
                      </td>,
                    ];
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function SideHeaders({ th }: { th: string }) {
  return (
    <>
      <th className={`${th} border-l border-zinc-200 text-right dark:border-zinc-800`}>ซื้อ</th>
      <th className={`${th} text-right`}>ขาย</th>
      <th className={`${th} text-right`}>สุทธิ</th>
    </>
  );
}
