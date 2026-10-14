"use client";

import { useActionState, useTransition } from "react";

import { resetSettings, saveSettings, type SettingsResult } from "@/app/actions";
import { Tooltip } from "@/app/badges";
import type { SettingField } from "@/lib/engine";
import { toDisplay, UNIT_LABEL } from "@/lib/format";

const INITIAL: SettingsResult = { errors: {}, message: null, values: null };

export function SettingsForm({ fields }: { fields: SettingField[] }) {
  const [state, action, saving] = useActionState(saveSettings, INITIAL);
  const [resetting, startReset] = useTransition();
  const sections = Map.groupBy(fields, (f) => f.section);

  function onReset() {
    if (!window.confirm("คืนค่าเกณฑ์ทั้งหมดเป็นค่า default ใน config.yaml?")) return;
    startReset(() => resetSettings());
  }

  return (
    <form action={action} className="space-y-6">
      {[...sections.values()].map((group) => (
        <fieldset key={group[0].section} className="rounded-md border border-zinc-200 p-4 dark:border-zinc-800">
          <legend className="px-1 font-semibold">{group[0].section_title}</legend>
          <div className="grid gap-4 md:grid-cols-2">
            {group.map((f) => (
              <Field key={f.key} field={f} error={state.errors[f.key]} typed={state.values?.[f.key]} />
            ))}
          </div>
        </fieldset>
      ))}

      <div className="flex flex-wrap items-center gap-3">
        <button
          disabled={saving || resetting}
          className="rounded-md bg-zinc-900 px-4 py-2 font-medium text-white disabled:bg-zinc-400 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {saving ? "กำลังบันทึก…" : "บันทึก"}
        </button>
        <button
          type="button"
          onClick={onReset}
          disabled={saving || resetting}
          className="rounded-md border border-zinc-300 px-4 py-2 hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
        >
          {resetting ? "กำลังคืนค่า…" : "คืนค่า default ทั้งหมด"}
        </button>
        <p aria-live="polite" className="text-sm text-red-600">
          {state.message}
        </p>
      </div>
    </form>
  );
}

function Field({ field: f, error, typed }: { field: SettingField; error?: string; typed?: string | string[] }) {
  const changed = JSON.stringify(f.value) !== JSON.stringify(f.default);
  const errorId = `error-${f.key}`;
  // kept outside the <label>/<legend> so the field's accessible name is just its title
  const extras = (
    <>
      <Tooltip id={`tip-${f.key}`} text={f.description} label={f.title} />
      {changed && (
        <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-xs font-normal text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
          แก้จาก default
        </span>
      )}
    </>
  );

  return (
    <div className="relative space-y-1 text-sm">
      {f.type === "choice" ? (
        <fieldset aria-describedby={error ? errorId : undefined}>
          <legend className="float-left font-medium">{f.title}</legend>
          {extras}
          <div className="clear-left mt-1 space-y-1">
            {f.options!.map((o) => (
              <label key={o.value} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  name={f.key}
                  value={o.value}
                  defaultChecked={(Array.isArray(typed) ? typed : (f.value as string[])).includes(o.value)}
                />
                {o.label}
              </label>
            ))}
          </div>
          <p className="text-xs text-zinc-500">
            default: {(f.default as string[]).map((v) => f.options!.find((o) => o.value === v)?.label ?? v).join(", ")}
          </p>
        </fieldset>
      ) : (
        <>
          <div>
            <label htmlFor={f.key} className="font-medium">
              {f.title}
            </label>
            {extras}
          </div>
          <div className="flex items-center gap-2">
            <input
              id={f.key}
              name={f.key}
              type="number"
              step="any"
              inputMode="decimal"
              defaultValue={typeof typed === "string" ? typed : toDisplay(f.value as number, f.unit)}
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? errorId : undefined}
              className={`w-32 rounded-md border bg-transparent px-2 py-1 ${error ? "border-red-500" : "border-zinc-300 dark:border-zinc-700"}`}
            />
            <span className="text-zinc-500">{UNIT_LABEL[f.unit]}</span>
          </div>
          <p className="text-xs text-zinc-500">
            default: {toDisplay(f.default as number, f.unit).toLocaleString("th-TH")} {UNIT_LABEL[f.unit]}
          </p>
        </>
      )}
      {error && (
        <p id={errorId} className="text-red-600">
          {error}
        </p>
      )}
    </div>
  );
}
