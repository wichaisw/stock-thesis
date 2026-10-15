import Link from "next/link";
import { Suspense } from "react";

import { CandidateTable } from "@/app/candidate-table";
import { engine, EngineError, type Evaluation } from "@/lib/engine";
import { thaiDate } from "@/lib/format";

type HistoryDate = { price_date: string; count: number };
type HistoryDay = { price_date: string; run_id: number; candidates: Evaluation[] };

export default function HistoryPage({ searchParams }: PageProps<"/history">) {
  return (
    <Suspense fallback={<p className="text-zinc-500">กำลังโหลด…</p>}>
      <History searchParams={searchParams} />
    </Suspense>
  );
}

async function History({ searchParams }: Pick<PageProps<"/history">, "searchParams">) {
  const raw = (await searchParams).date;
  const dates = await engine<HistoryDate[]>("/candidates/history");
  const picked = (Array.isArray(raw) ? raw[0] : raw) ?? dates[0]?.price_date;
  const day = picked ? await historyDay(picked) : null;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">ประวัติ candidate</h1>
        <p className="text-sm text-zinc-500">
          ค่าตามที่ batch ของวันนั้นประเมินไว้ด้วยเกณฑ์ตอนนั้น ชื่อหุ้นไม่ลิงก์เพราะหน้ารายละเอียดแสดงข้อมูลวันนี้ ·{" "}
          <Link href="/" className="underline">
            กลับหน้า candidates
          </Link>
        </p>
      </div>
      {dates.length === 0 ? (
        <p className="text-zinc-500">ยังไม่มีประวัติ ประวัติเริ่มเก็บจาก batch ที่สำเร็จ</p>
      ) : (
        <div className="flex flex-col gap-4 md:flex-row">
          <ul className="shrink-0 space-y-1 text-sm md:w-48">
            {dates.map((d) => (
              <li key={d.price_date}>
                <Link
                  href={`/history?date=${d.price_date}`}
                  className={d.price_date === picked ? "font-semibold" : "text-zinc-600 underline dark:text-zinc-400"}
                >
                  {thaiDate(d.price_date)}
                </Link>{" "}
                <span className="text-zinc-500">{d.count} ตัว</span>
              </li>
            ))}
          </ul>
          <div className="min-w-0 flex-1 space-y-2">
            {!day ? (
              <p className="text-zinc-500">ไม่มีประวัติของวันที่ {picked}</p>
            ) : (
              <>
                <p className="text-sm text-zinc-500">
                  ราคาปิดวันที่ {thaiDate(day.price_date)} · run {day.run_id} · {day.candidates.length} ตัว
                </p>
                {day.candidates.length === 0 ? (
                  <p className="text-zinc-500">วันนั้นไม่มีหุ้นที่ผ่านทุกเงื่อนไข</p>
                ) : (
                  <CandidateTable candidates={day.candidates} linkSymbols={false} />
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

async function historyDay(date: string): Promise<HistoryDay | null> {
  try {
    return await engine<HistoryDay>(`/candidates/history/${encodeURIComponent(date)}`);
  } catch (e) {
    if (e instanceof EngineError && e.status === 404) return null;
    throw e;
  }
}
