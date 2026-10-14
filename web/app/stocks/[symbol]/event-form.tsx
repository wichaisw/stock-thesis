"use client";

import { useActionState } from "react";

import { addEvent, type ActionResult } from "@/app/actions";

export function EventForm({ symbol }: { symbol: string }) {
  const [state, action, pending] = useActionState<ActionResult, FormData>(addEvent.bind(null, symbol), {
    error: null,
  });
  return (
    <form action={action} className="flex flex-wrap items-end gap-2 text-sm">
      <label className="flex flex-col gap-1">
        วันที่
        <input type="date" name="date" required className="rounded-md border border-zinc-300 bg-transparent px-2 py-1 dark:border-zinc-700" />
      </label>
      <label className="flex flex-1 flex-col gap-1">
        รายละเอียด
        <input
          name="text"
          required
          maxLength={200}
          placeholder="เช่น XD 0.50 บาท"
          className="rounded-md border border-zinc-300 bg-transparent px-2 py-1 dark:border-zinc-700"
        />
      </label>
      <button disabled={pending} className="rounded-md bg-zinc-900 px-3 py-1.5 text-white disabled:bg-zinc-400 dark:bg-zinc-100 dark:text-zinc-900">
        {pending ? "กำลังบันทึก…" : "เพิ่ม event"}
      </button>
      {state.error && <p className="w-full text-red-600">{state.error}</p>}
    </form>
  );
}
