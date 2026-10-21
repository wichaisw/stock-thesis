"use client";

import { useActionState } from "react";

import { addHolding, type ActionResult } from "@/app/actions";

const input = "rounded-md border border-zinc-300 bg-transparent px-2 py-1 dark:border-zinc-700";

export function HoldingForm() {
  const [state, action, pending] = useActionState<ActionResult, FormData>(addHolding, { error: null });
  return (
    <form action={action} className="flex flex-wrap items-end gap-2 text-sm">
      <label className="flex flex-col gap-1">
        Symbol
        <input name="symbol" required placeholder="เช่น PTT" className={`${input} w-32 uppercase placeholder:normal-case`} />
      </label>
      <label className="flex flex-col gap-1">
        ราคาต้นทุนเฉลี่ย (บาท)
        <input name="cost" type="number" required min="0.01" step="0.01" className={`${input} w-36`} />
      </label>
      <label className="flex flex-col gap-1">
        วันที่ซื้อ
        <input name="buy_date" type="date" required className={input} />
      </label>
      <button disabled={pending} className="rounded-md bg-zinc-900 px-3 py-1.5 text-white disabled:bg-zinc-400 dark:bg-zinc-100 dark:text-zinc-900">
        {pending ? "กำลังบันทึก…" : "เพิ่มหุ้นที่ถือ"}
      </button>
      {state.error && (
        <p role="alert" className="w-full text-red-600">
          {state.error}
        </p>
      )}
    </form>
  );
}
