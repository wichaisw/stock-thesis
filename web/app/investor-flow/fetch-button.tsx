"use client";

import { useState, useTransition } from "react";

import { fetchInvestorFlow } from "@/app/actions";

export function FetchButton() {
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  return (
    <div className="ml-auto flex max-w-md flex-col items-end gap-1 text-sm">
      <button
        type="button"
        onClick={() => startTransition(async () => setError((await fetchInvestorFlow()).error))}
        disabled={pending}
        className="rounded-md bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-zinc-400"
      >
        {pending ? "กำลังดึงข้อมูล…" : "ดึงข้อมูลตอนนี้"}
      </button>
      <p aria-live="polite" className="text-right text-red-600">{error}</p>
    </div>
  );
}
