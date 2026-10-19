import Link from "next/link";

import { StateBadge, Tag, Tooltip } from "@/app/badges";
import type { Evaluation } from "@/lib/engine";
import { baht, pct } from "@/lib/format";
import { gateRows, gateTally, mosGate } from "@/lib/gates";

// history rows keep the evaluation of their day, so every nested read tolerates fields added later (candidate-history D5)
export function CandidateTable({ candidates, linkSymbols }: { candidates: Evaluation[]; linkSymbols: boolean }) {
  const th = "px-3 py-2 text-left font-medium";
  return (
    <div className="overflow-x-auto rounded-md border border-zinc-200 dark:border-zinc-800">
      <table className="w-full text-sm">
        <thead className="bg-zinc-50 text-zinc-600 dark:bg-zinc-900 dark:text-zinc-400">
          <tr>
            <th className={th}>#</th>
            <th className={th}>Symbol</th>
            <th className={th}>Sector</th>
            <th className={th}>Gates</th>
            <th className={`${th} text-right`}>ราคา</th>
            <th className={th}>CDC</th>
            <th className={`${th} text-right`}>ETA (วัน)</th>
            <th className={th}>Fair value panel</th>
            <th className={`${th} text-right`}>MoS gate</th>
            <th className={`${th} text-right`}>MoS ต่ำ / median / สูง</th>
            <th className={`${th} text-right`}>RRR</th>
            <th className={th}>ป้าย</th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((c) => {
            const fv = c.fair_value?.summary;
            const rr = c.risk_reward;
            // the threshold text is not shown here, only the tally and failed reasons
            const gates = gateTally(gateRows(c, ""));
            return (
              <tr key={c.symbol} className="relative border-t border-zinc-200 dark:border-zinc-800">
                <td className="px-3 py-2 text-zinc-500">{c.candidate_rank}</td>
                <td className="px-3 py-2">
                  {linkSymbols ? (
                    <Link href={`/stocks/${c.symbol}`} className="font-semibold underline-offset-2 hover:underline">
                      {c.symbol}
                    </Link>
                  ) : (
                    <span className="font-semibold">{c.symbol}</span>
                  )}
                </td>
                <td className="px-3 py-2">{c.sector}</td>
                <td className="px-3 py-2 whitespace-nowrap">
                  {gates.passed}/{gates.evaluated}
                  {gates.failed.length > 0 && (
                    <Tooltip
                      id={`tip-gates-${c.symbol}`}
                      text={`ไม่ผ่าน: ${gates.failed.map((g) => g.reason).join(", ")}`}
                      label={`เกณฑ์ที่ไม่ผ่านของ ${c.symbol}`}
                    />
                  )}
                </td>
                <td className="px-3 py-2 text-right">{c.price == null ? "-" : baht(c.price)}</td>
                <td className="px-3 py-2">
                  {c.cdc?.state ? <StateBadge state={c.cdc.state} /> : "-"}
                </td>
                <td className="px-3 py-2 text-right">{c.cdc?.eta_days ?? "-"}</td>
                <td className="px-3 py-2">{fv?.label ?? "-"}</td>
                <td className="px-3 py-2 text-right font-semibold whitespace-nowrap">{mosGate(c)}</td>
                <td className="px-3 py-2 text-right whitespace-nowrap text-zinc-500">
                  {fv ? `${pct(fv.min_mos, 0)} / ${pct(fv.median_mos, 0)} / ${pct(fv.max_mos, 0)}` : "-"}
                </td>
                <td className="px-3 py-2 text-right" title={rr?.reason ?? undefined}>
                  {rr ? (rr.rrr ?? "N/A") : "-"}
                </td>
                <td className="space-x-1 px-3 py-2 whitespace-nowrap">
                  {c.quality?.inflection?.flag && (
                    <Tag tone="violet" title={c.quality.inflection.reason ?? undefined}>
                      inflection
                    </Tag>
                  )}
                  {rr?.low_rrr && <Tag tone="red">RRR ต่ำ</Tag>}
                  {rr?.high_upside && <Tag tone="red">upside สูงผิดปกติ</Tag>}
                  {c.stale_price && <Tag tone="red">ราคาไม่อัปเดต</Tag>}
                  {c.fair_value?.structure_change?.flag && (
                    <Tag tone="red" title={c.fair_value?.structure_change?.reason ?? undefined}>
                      โครงสร้างทุนเปลี่ยน
                    </Tag>
                  )}
                  {c.fair_value?.history_gap?.flag && (
                    <Tag title={c.fair_value?.history_gap?.reason ?? undefined}>ข้อมูลย้อนหลังไม่ครบ</Tag>
                  )}
                  {c.quality?.profit_jump?.flag && (
                    <Tag tone="red" title={c.quality.profit_jump.reason ?? undefined}>
                      กำไรกระโดด
                    </Tag>
                  )}
                  {c.earnings_due?.flag && <Tag title={c.earnings_due.reason ?? undefined}>งบใกล้ออก</Tag>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
