"use server";

import { refresh } from "next/cache";

import { engine, EngineError, type Run } from "@/lib/engine";

export type ActionResult = { error: string | null };

export async function startRun(): Promise<ActionResult> {
  try {
    await engine("/runs", { method: "POST" });
    return { error: null };
  } catch (e) {
    return { error: e instanceof EngineError ? e.message : "เริ่ม batch ไม่ได้" };
  }
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
