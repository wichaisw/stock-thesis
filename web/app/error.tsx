"use client";

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="space-y-3 rounded-md border border-red-300 bg-red-50 p-6 dark:border-red-800 dark:bg-red-950/30">
      <p className="font-medium text-red-700 dark:text-red-300">
        โหลดข้อมูลจาก engine ไม่ได้ ตรวจว่า engine รันอยู่ (ดู README)
      </p>
      {/* production builds redact server error messages, so this only helps in dev */}
      <p className="text-sm text-red-600">{error.message}</p>
      <button type="button" onClick={reset} className="rounded-md border border-red-300 px-3 py-1.5 text-sm">
        ลองใหม่
      </button>
    </div>
  );
}
