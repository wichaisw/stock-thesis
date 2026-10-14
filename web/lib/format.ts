import type { SettingUnit } from "@/lib/engine";

export function pct(x: number | null | undefined, digits = 1): string {
  return x == null ? "N/A" : `${x > 0 ? "+" : ""}${(x * 100).toFixed(digits)}%`;
}

export function baht(x: number | null | undefined): string {
  return x == null ? "N/A" : x.toLocaleString("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function thaiDate(iso: string | null | undefined): string {
  if (!iso) return "-";
  return new Date(iso.length === 10 ? `${iso}T00:00:00` : iso).toLocaleDateString("th-TH", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function thaiDateTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("th-TH", { dateStyle: "medium", timeStyle: "short" });
}

// the engine keeps ratios as decimals and traded value in baht; the settings form shows % and million baht
const DISPLAY_SCALE: Partial<Record<SettingUnit, number>> = { percent: 100, million_baht: 1e-6 };

export function toDisplay(value: number, unit: SettingUnit): number {
  // round away float noise such as 0.07 * 100 = 7.000000000000001
  return Number((value * (DISPLAY_SCALE[unit] ?? 1)).toPrecision(12));
}

export function fromDisplay(value: number, unit: SettingUnit): number {
  return Number((value / (DISPLAY_SCALE[unit] ?? 1)).toPrecision(12));
}

export const UNIT_LABEL: Record<SettingUnit, string> = {
  percent: "%",
  million_baht: "ล้านบาท/วัน",
  days: "วันทำการ",
  quarters: "ไตรมาส",
  months: "เดือน",
  times: "เท่า",
  stocks: "ตัว",
  choice: "",
};
