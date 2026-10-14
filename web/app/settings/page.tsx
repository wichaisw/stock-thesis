import type { Metadata } from "next";
import { Suspense } from "react";

import { StaleNotice } from "@/app/badges";
import { RunButton } from "@/app/run-button";
import { SettingsForm } from "@/app/settings/settings-form";
import { engine, type Run, type Settings } from "@/lib/engine";
import { thaiDateTime } from "@/lib/format";

export const metadata: Metadata = { title: "ตั้งค่าเกณฑ์ · Value stock shortlist" };

export default function SettingsPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">ตั้งค่าเกณฑ์</h1>
        <p className="text-sm text-zinc-500">
          ค่าที่บันทึกมีผลกับ batch ครั้งถัดไป ทั้งปุ่มรัน batch และ cron ส่วนสูตร CDC, sector การเงิน และ catalyst แก้ได้ใน
          engine/config.yaml
        </p>
      </div>
      <Suspense fallback={<p className="text-zinc-500">กำลังโหลด…</p>}>
        <Form />
      </Suspense>
    </div>
  );
}

async function Form() {
  const [settings, runs] = await Promise.all([
    engine<Settings>("/settings"),
    engine<{ latest: Run | null }>("/runs/latest"),
  ]);
  return (
    <>
      {settings.stale && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <StaleNotice />
          <RunButton initial={runs.latest} />
        </div>
      )}
      {settings.updated_at && <p className="text-sm text-zinc-500">แก้ล่าสุดเมื่อ {thaiDateTime(settings.updated_at)}</p>}
      {/* remount on every save or reset so the inputs pick up the new saved values */}
      <SettingsForm key={settings.updated_at ?? "default"} fields={settings.fields} />
    </>
  );
}
