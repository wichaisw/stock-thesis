import Link from "next/link";
import { Suspense } from "react";

import { FailIcon, StaleNotice, StateBadge, Tag, Tooltip } from "@/app/badges";
import { RunButton } from "@/app/run-button";
import { engine, type Evaluation, type Failure, type Run } from "@/lib/engine";
import { baht, pct, thaiDate, thaiDateTime } from "@/lib/format";
import { gateRows, gateTally } from "@/lib/gates";

const secondaryButton =
  "rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800";

type CandidatesResponse = { run: Run | null; candidates: Evaluation[]; failure_count: number; stale: boolean };

export default function Home() {
  return (
    <Suspense fallback={<p className="text-zinc-500">กำลังโหลด…</p>}>
      <CandidateList />
    </Suspense>
  );
}

async function CandidateList() {
  const [data, runs] = await Promise.all([
    engine<CandidatesResponse>("/candidates"),
    engine<{ latest: Run | null }>("/runs/latest"),
  ]);
  const { run, candidates, failure_count, stale } = data;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Candidates</h1>
          {run && (
            <p className="text-sm text-zinc-500">
              ราคาปิดวันที่ {thaiDate(run.price_date)} · batch รันเมื่อ {thaiDateTime(run.finished_at)} · ประเมิน{" "}
              {run.succeeded}/{run.total} ตัว
            </p>
          )}
          {run?.stale_count ? (
            <p role="status" className="text-sm text-amber-700 dark:text-amber-300">
              ราคา {run.stale_count}/{run.succeeded} ตัวเป็นวันที่ {thaiDate(run.stale_date)}
            </p>
          ) : null}
        </div>
        <div className="ml-auto">
          <RunButton initial={runs.latest}>
            <Link href="/investor-flow" className={secondaryButton}>
              ประเภทนักลงทุน
            </Link>
            <Link href="/settings" className={secondaryButton}>
              ปรับเกณฑ์
            </Link>
          </RunButton>
        </div>
      </div>
      {stale && run && <StaleNotice />}

      {!run ? (
        <p className="rounded-md border border-dashed border-zinc-300 p-8 text-center text-zinc-500 dark:border-zinc-700">
          ยังไม่มีข้อมูล กดปุ่ม &ldquo;รัน batch&rdquo; เพื่อดึงข้อมูลและประเมินหุ้นทั้งตลาด
        </p>
      ) : (
        <>
          {failure_count > 0 && <Failures count={failure_count} />}
          {candidates.length === 0 ? (
            <p className="text-zinc-500">วันนี้ไม่มีหุ้นที่ผ่านทุกเงื่อนไข</p>
          ) : (
            <CandidateTable candidates={candidates} />
          )}
        </>
      )}
    </div>
  );
}

async function Failures({ count }: { count: number }) {
  const { failures } = await engine<{ failures: Failure[] }>("/failures");
  return (
    <details className="rounded-md border border-amber-300 bg-amber-50 px-4 py-2 text-sm dark:border-amber-800 dark:bg-amber-950/30">
      <summary className="cursor-pointer">
        <FailIcon reason="กดเพื่อดูรายชื่อ" /> ดึงข้อมูลไม่ได้ {count} ตัว
      </summary>
      <ul className="mt-2 space-y-1">
        {failures.map((f) => (
          <li key={f.symbol}>
            <FailIcon reason={f.reason} />{" "}
            <Link href={`/stocks/${f.symbol}`} className="font-medium underline">
              {f.symbol}
            </Link>{" "}
            <span className="text-zinc-600 dark:text-zinc-400">{f.reason}</span>
          </li>
        ))}
      </ul>
    </details>
  );
}

function CandidateTable({ candidates }: { candidates: Evaluation[] }) {
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
            <th className={`${th} text-right`}>MoS ต่ำ / median / สูง</th>
            <th className={`${th} text-right`}>RRR</th>
            <th className={th}>ป้าย</th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((c) => {
            const fv = c.fair_value!.summary;
            const rr = c.risk_reward!;
            // the threshold text is not shown here, only the tally and failed reasons
            const gates = gateTally(gateRows(c, ""));
            return (
              <tr key={c.symbol} className="relative border-t border-zinc-200 dark:border-zinc-800">
                <td className="px-3 py-2 text-zinc-500">{c.candidate_rank}</td>
                <td className="px-3 py-2">
                  <Link href={`/stocks/${c.symbol}`} className="font-semibold underline-offset-2 hover:underline">
                    {c.symbol}
                  </Link>
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
                <td className="px-3 py-2 text-right">{baht(c.price)}</td>
                <td className="px-3 py-2">
                  <StateBadge state={c.cdc.state} />
                </td>
                <td className="px-3 py-2 text-right">{c.cdc.eta_days ?? "-"}</td>
                <td className="px-3 py-2">{fv.label}</td>
                <td className="px-3 py-2 text-right whitespace-nowrap">
                  {pct(fv.min_mos, 0)} / <b>{pct(fv.median_mos, 0)}</b> / {pct(fv.max_mos, 0)}
                </td>
                <td className="px-3 py-2 text-right" title={rr.reason ?? undefined}>
                  {rr.rrr ?? "N/A"}
                </td>
                <td className="space-x-1 px-3 py-2 whitespace-nowrap">
                  {c.quality?.inflection.flag && (
                    <Tag tone="violet" title={c.quality.inflection.reason ?? undefined}>
                      inflection
                    </Tag>
                  )}
                  {rr.low_rrr && <Tag tone="red">RRR ต่ำ</Tag>}
                  {rr.high_upside && <Tag tone="red">upside สูงผิดปกติ</Tag>}
                  {c.stale_price && <Tag tone="red">ราคาไม่อัปเดต</Tag>}
                  {c.fair_value!.structure_change.flag && (
                    <Tag tone="red" title={c.fair_value!.structure_change.reason ?? undefined}>
                      โครงสร้างทุนเปลี่ยน
                    </Tag>
                  )}
                  {c.fair_value!.history_gap?.flag && (
                    <Tag title={c.fair_value!.history_gap.reason ?? undefined}>ข้อมูลย้อนหลังไม่ครบ</Tag>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
