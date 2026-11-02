"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

import { Tooltip } from "@/app/badges";
import { METHOD_SHORT } from "@/lib/gates";

// same list as engine candidates.TOGGLEABLE; the engine rejects anything else
const GATES = ["peer_pe", "justified_pbv"];

// the choice lives in the URL only, so a fresh visit is the batch list again (candidate-gate-toggle D5)
export function GateToggle({ gates }: { gates: string[] }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function toggle(method: string) {
    const next = GATES.filter((g) => (g === method ? !gates.includes(g) : gates.includes(g)));
    // "gates=" keeps "none chosen" apart from "no param" (= the batch's gates)
    startTransition(() => router.replace(`/?gates=${next.join(",")}`, { scroll: false }));
  }

  return (
    <fieldset className="relative flex flex-wrap items-center gap-x-4 gap-y-1 text-sm" aria-busy={pending}>
      <legend className="float-left mr-2 text-zinc-600 dark:text-zinc-400">
        gate ด้าน fair value
        <Tooltip
          id="gate-toggle-help"
          label="gate ด้าน fair value"
          text="เลือกว่าใช้ gate ไหนกรอง candidate คำนวณใหม่จาก batch ล่าสุดโดยไม่ดึงข้อมูลใหม่ และไม่ถูกบันทึก ชุดอื่นนอกจาก Peer PE + Justified PBV ไม่เคย backtest ไม่เลือกเลย = ไม่กรองด้วย MoS และ target ใช้ median ของ panel"
        />
      </legend>
      {GATES.map((g) => (
        <label key={g} className="inline-flex items-center gap-1.5">
          <input type="checkbox" checked={gates.includes(g)} onChange={() => toggle(g)} disabled={pending} />
          {METHOD_SHORT[g]}
        </label>
      ))}
      {pending && <span className="text-zinc-500">กำลังคำนวณ…</span>}
    </fieldset>
  );
}
