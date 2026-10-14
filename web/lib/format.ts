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
