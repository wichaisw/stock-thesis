"use server";

import { refresh } from "next/cache";

import { engine, EngineError, type Run, type Settings } from "@/lib/engine";
import { fromDisplay } from "@/lib/format";

export type ActionResult = { error: string | null };

export async function startRun(): Promise<ActionResult> {
  try {
    await engine("/runs", { method: "POST" });
    return { error: null };
  } catch (e) {
    return { error: e instanceof EngineError ? e.message : "เริ่ม batch ไม่ได้" };
  }
}

export async function fetchInvestorFlow(): Promise<ActionResult> {
  try {
    await engine("/investor-flow", { method: "POST" });
  } catch (e) {
    return { error: e instanceof EngineError ? e.message : "ดึงข้อมูลไม่ได้" };
  }
  refresh();
  return { error: null };
}

export async function latestRun(): Promise<Run | null> {
  return (await engine<{ latest: Run | null }>("/runs/latest")).latest;
}

export async function refreshPage(): Promise<void> {
  refresh();
}

export async function addEvent(symbol: string, _prev: ActionResult, form: FormData): Promise<ActionResult> {
  try {
    await engine(`/stocks/${encodeURIComponent(symbol)}/events`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ date: form.get("date"), text: form.get("text") }),
    });
  } catch (e) {
    return { error: e instanceof EngineError && e.status !== 422 ? e.message : "กรอกวันที่และข้อความให้ครบ" };
  }
  refresh();
  return { error: null };
}

export async function deleteEvent(id: number): Promise<void> {
  await engine(`/events/${id}`, { method: "DELETE" });
  refresh();
}

export async function addHolding(_prev: ActionResult, form: FormData): Promise<ActionResult> {
  try {
    await engine("/holdings", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ symbol: form.get("symbol"), cost: form.get("cost"), buy_date: form.get("buy_date") }),
    });
  } catch (e) {
    // the engine's own checks send Thai text; a missing or malformed field comes back as pydantic's list
    if (e instanceof EngineError && typeof e.detail === "string") return { error: e.message };
    return { error: e instanceof EngineError && e.status === 422 ? "กรอก symbol ราคาต้นทุน และวันที่ซื้อให้ครบ" : "บันทึกไม่ได้" };
  }
  refresh();
  return { error: null };
}

export async function deleteHolding(symbol: string): Promise<void> {
  await engine(`/holdings/${encodeURIComponent(symbol)}`, { method: "DELETE" });
  refresh();
}

export type SettingsResult = {
  errors: Record<string, string>;
  message: string | null;
  // what the user typed, so React's form reset after the action does not wipe it on a failed save
  values: Record<string, string | string[]> | null;
};

export async function saveSettings(_prev: SettingsResult, form: FormData): Promise<SettingsResult> {
  const typed: Record<string, string | string[]> = {};
  const payload: Record<string, unknown> = {};
  try {
    const { fields } = await engine<Settings>("/settings");
    for (const f of fields) {
      if (f.type === "choice") {
        payload[f.key] = typed[f.key] = form.getAll(f.key).map(String);
      } else {
        const raw = String(form.get(f.key) ?? "").trim();
        typed[f.key] = raw;
        // a blank or non-numeric box goes to the engine as-is so the error lands on that field
        payload[f.key] = raw === "" || Number.isNaN(Number(raw)) ? raw : fromDisplay(Number(raw), f.unit);
      }
    }
    await engine("/settings", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (e) {
    const errors = e instanceof EngineError ? (e.detail as { errors?: Record<string, string> } | undefined)?.errors : undefined;
    if (errors) return { errors, message: "ยังไม่ได้บันทึก มีค่าที่ต้องแก้", values: typed };
    return { errors: {}, message: e instanceof EngineError ? e.message : "บันทึกไม่ได้", values: typed };
  }
  refresh();
  return { errors: {}, message: null, values: null };
}

export async function resetSettings(): Promise<void> {
  await engine("/settings", { method: "DELETE" });
  refresh();
}
