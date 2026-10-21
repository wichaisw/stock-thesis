import Link from "next/link";
import { Suspense } from "react";

import { FailIcon, StaleNotice } from "@/app/badges";
import { CandidateTable } from "@/app/candidate-table";
import { RunButton } from "@/app/run-button";
import { engine, type Evaluation, type Failure, type Run } from "@/lib/engine";
import { thaiDate, thaiDateTime } from "@/lib/format";

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
            <Link href="/history" className={secondaryButton}>
              ประวัติ candidate
            </Link>
            <Link href="/holdings" className={secondaryButton}>
              หุ้นที่ถือ
            </Link>
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
            <CandidateTable candidates={candidates} linkSymbols />
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
