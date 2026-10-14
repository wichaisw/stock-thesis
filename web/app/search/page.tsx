import Link from "next/link";
import { Suspense } from "react";

import { FailIcon } from "@/app/badges";
import { engine, type StockInfo } from "@/lib/engine";

type SearchResult = StockInfo & { failure: string | null };

export default function SearchPage({ searchParams }: PageProps<"/search">) {
  return (
    <Suspense fallback={<p className="text-zinc-500">กำลังค้นหา…</p>}>
      <Results searchParams={searchParams} />
    </Suspense>
  );
}

async function Results({ searchParams }: Pick<PageProps<"/search">, "searchParams">) {
  const raw = (await searchParams).q;
  const q = (Array.isArray(raw) ? raw[0] : raw)?.trim() ?? "";
  const results = q ? await engine<SearchResult[]>(`/stocks/search?q=${encodeURIComponent(q)}`) : [];

  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">ผลค้นหา &ldquo;{q.toUpperCase()}&rdquo;</h1>
      {results.length === 0 ? (
        <p className="text-zinc-500">ไม่พบหุ้น (หรือยังไม่เคยรัน batch)</p>
      ) : (
        <ul className="divide-y divide-zinc-200 rounded-md border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
          {results.map((s) => (
            <li key={s.symbol} className="flex items-center gap-3 px-4 py-2">
              <Link href={`/stocks/${s.symbol}`} className="w-20 font-semibold hover:underline">
                {s.symbol}
              </Link>
              {s.failure && <FailIcon reason={s.failure} />}
              <span className="text-sm text-zinc-600 dark:text-zinc-400">
                {s.name} · {s.sector} · {s.market}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
