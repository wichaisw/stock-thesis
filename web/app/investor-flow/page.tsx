import { Suspense } from "react";

import { Tag } from "@/app/badges";
import { FetchButton } from "@/app/investor-flow/fetch-button";
import { engine, INVESTOR_TYPES, type InvestorFlowDay, type InvestorType } from "@/lib/engine";
import { thaiDate, thaiDateTime } from "@/lib/format";

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

export default function InvestorFlowPage() {
  return (
    <Suspense fallback={<p className="text-zinc-500">กำลังโหลด…</p>}>
      <FlowTable />
    </Suspense>
  );
}

async function FlowTable() {
  const days = await engine<InvestorFlowDay[]>("/investor-flow");
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
                  </td>
                  {INVESTOR_TYPES.map((t) => {
                    const net = d[`${t}_buy`] - d[`${t}_sell`];
                    const tone = net > 0 ? "text-green-700 dark:text-green-400" : net < 0 ? "text-red-700 dark:text-red-400" : "";
                    return [
                      <td key={`${t}-buy`} className={`${cell} border-l border-zinc-200 dark:border-zinc-800`}>
                        {million(d[`${t}_buy`])}
                      </td>,
                      <td key={`${t}-sell`} className={cell}>
                        {million(d[`${t}_sell`])}
                      </td>,
                      <td key={`${t}-net`} className={`${cell} font-medium ${tone}`}>
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
