import Link from "next/link";
import { Suspense } from "react";

import { FailIcon, StaleNotice } from "@/app/badges";
import { CandidateTable } from "@/app/candidate-table";
import { GateToggle } from "@/app/gate-toggle";
import { RunButton } from "@/app/run-button";
import { engine, EngineError, type Evaluation, type Failure, type Run } from "@/lib/engine";
import { thaiDate, thaiDateTime } from "@/lib/format";

const secondaryButton =
  "rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800";

type CandidatesResponse = {
  run: Run | null;
  candidates: Evaluation[];
  failure_count: number;
  stale: boolean;
  // gates applied to this list and the batch's own; absent before candidate-gate-toggle
  gates?: string[] | null;
  batch_gates?: string[] | null;
};

export default function Home({ searchParams }: PageProps<"/">) {
  return (
    <Suspense fallback={<p className="text-zinc-500">กำลังโหลด…</p>}>
      <CandidateList searchParams={searchParams} />
    </Suspense>
  );
}

async function CandidateList({ searchParams }: Pick<PageProps<"/">, "searchParams">) {
  const raw = (await searchParams).gates;
  const gates = Array.isArray(raw) ? raw[0] : raw;
  const [{ data, gateError }, runs] = await Promise.all([
    candidatesFor(gates),
    engine<{ latest: Run | null }>("/runs/latest"),
  ]);
  const { run, candidates, failure_count, stale } = data;
  const applied = data.gates ?? [];
  const batchGates = data.batch_gates ?? [];
  const differs = applied.length !== batchGates.length || applied.some((g) => !batchGates.includes(g));

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
      {run && data.gates && <GateToggle gates={applied} />}
      {gateError && (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          {gateError} ·{" "}
          <Link href="/" className="underline">
            ใช้ gate ของ batch
          </Link>
        </p>
      )}
      {run && !gateError && differs && (
        <p role="status" className="text-sm text-amber-700 dark:text-amber-300">
          {applied.length === 0
            ? "ไม่ได้ใช้ gate ด้าน fair value: list ไม่กรองด้วย MoS และ target มาจาก median ของ panel"
            : "ใช้ gate ต่างจาก batch"}{" "}
          หน้ารายละเอียด ประวัติ และหุ้นที่ถือยังใช้ gate ของ batch ·{" "}
          <Link href="/" className="underline">
            กลับไปใช้ gate ของ batch
          </Link>
        </p>
      )}

      {!run ? (
        <p className="rounded-md border border-dashed border-zinc-300 p-8 text-center text-zinc-500 dark:border-zinc-700">
          ยังไม่มีข้อมูล กดปุ่ม &ldquo;รัน batch&rdquo; เพื่อดึงข้อมูลและประเมินหุ้นทั้งตลาด
        </p>
      ) : (
        <>
          {failure_count > 0 && <Failures count={failure_count} />}
          {gateError ? null : candidates.length === 0 ? (
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

// an unknown gate in the URL shows the engine's message instead of a list (candidate-gate-toggle D6)
async function candidatesFor(gates: string | undefined): Promise<{ data: CandidatesResponse; gateError: string | null }> {
  if (gates === undefined) return { data: await engine<CandidatesResponse>("/candidates"), gateError: null };
  try {
    return { data: await engine<CandidatesResponse>(`/candidates?gates=${encodeURIComponent(gates)}`), gateError: null };
  } catch (e) {
    if (!(e instanceof EngineError) || e.status !== 422) throw e;
    return { data: await engine<CandidatesResponse>("/candidates"), gateError: e.message };
  }
}
