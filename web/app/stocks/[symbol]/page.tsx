import { notFound } from "next/navigation";
import { Suspense } from "react";

import { deleteEvent } from "@/app/actions";
import { FailIcon, StateBadge, Tag, Tooltip } from "@/app/badges";
import { CopyButton } from "@/app/stocks/[symbol]/copy-button";
import { EventForm } from "@/app/stocks/[symbol]/event-form";
import { engine, EngineError, type Evaluation, type StockDetail } from "@/lib/engine";
import { baht, pct, thaiDate } from "@/lib/format";
import { gateRows, gateTally, METHOD_SHORT, mosGate } from "@/lib/gates";
import { toLlmMarkdown } from "@/lib/llm-export";

// METHOD_NOTES_EN in lib/llm-export.ts is the English twin of these two: change both together
const FAIR_VALUE_HELP: Record<string, string> = {
  pe_median:
    "median PE 5 ปีของหุ้นเอง × EPS TTM คือราคาถ้าตลาดให้ PE เท่าปกติของมัน ราคาต่ำกว่าแปลว่าถูกเมื่อเทียบกับอดีตของตัวเอง เหมาะกับหุ้นที่กำไรสม่ำเสมอ ไม่เหมาะกับหุ้นวัฏจักรหรือกำไรเพิ่งพลิก",
  pe_minus_1sd:
    "(median PE − 1SD) × EPS TTM คือราคาถ้าตลาดมองแง่ร้ายกว่าปกติ เป็นมุมมองระมัดระวัง ถ้าราคายังต่ำกว่าเส้นนี้ แปลว่ามี margin of safety แม้ตลาดไม่ชอบหุ้นตัวนี้",
  pbv_median:
    "median PBV 5 ปี × BVPS ล่าสุด เหมาะกับหุ้นที่สินทรัพย์สร้างกำไร เช่น ธนาคาร ไฟแนนซ์ อสังหา ไม่เหมาะกับหุ้น asset-light หรือหุ้นที่ ROE เปลี่ยนไปจากอดีตมาก",
  dividend_yield_median:
    "ปันผลเงินสด 12 เดือนล่าสุดต่อหุ้น ÷ median dividend yield 12 เดือนรายไตรมาสใน 5 ปี ไม่นับปันผลเป็นหุ้น และไม่นับไตรมาสที่ yield ต่ำกว่าเกณฑ์ขั้นต่ำ (ถือว่าไม่ได้จ่าย) ราคาต่ำกว่าแปลว่า yield ตอนนี้สูงกว่าปกติ เหมาะกับหุ้นที่จ่ายปันผลเงินสดสม่ำเสมอ ระวังปันผลพิเศษครั้งเดียวที่ทำให้ดูถูกเกินจริงไปราว 12 เดือน",
  peer_pe:
    "median PE ของหุ้นอื่นใน sector เดียวกัน × EPS TTM ราคาต่ำกว่าแปลว่าถูกกว่าเพื่อนใน sector แต่อาจถูกเพราะคุณภาพหรือการเติบโตต่ำกว่า หรือทั้ง sector แพง",
  justified_pbv:
    "(ROE TTM − g) ÷ (r − g) × ส่วนผู้ถือหุ้นต่อหุ้นล่าสุด คือ PBV ที่สมเหตุสมผลจากความสามารถทำกำไร ไม่ขึ้นกับราคาในอดีต r คือ cost of equity และ g คือ growth ระยะยาว (default 10% และ 3% ปรับได้ในหน้า settings) ไวต่อ r − g มาก และ ROE ที่สูงจากกำไรพิเศษครั้งเดียวทำให้ fair value สูงเกินจริง ใช้กับหุ้นการเงินได้",
};

const MOS_HELP =
  "margin of safety = (fair value − ราคา) ÷ fair value บวกแปลว่าราคาต่ำกว่า fair value ของเกณฑ์นั้น ถ้า fair value ต่ำมาก ค่าติดลบจะดูมากเกินจริง";

const CHECK_LABELS: Record<string, string> = {
  min_quarters: "จำนวนไตรมาสที่มีงบ",
  roe: "ROE",
  de: "D/E",
  ocf: "OCF",
  no_loss: "ไม่ขาดทุน",
};

export default function StockPage({ params }: PageProps<"/stocks/[symbol]">) {
  return (
    <Suspense fallback={<p className="text-zinc-500">กำลังโหลด…</p>}>
      <Detail params={params} />
    </Suspense>
  );
}

async function Detail({ params }: Pick<PageProps<"/stocks/[symbol]">, "params">) {
  const { symbol } = await params;
  let data: StockDetail;
  try {
    data = await engine<StockDetail>(`/stocks/${encodeURIComponent(symbol)}`);
  } catch (e) {
    if (e instanceof EngineError && e.status === 404) notFound();
    throw e;
  }
  const { stock, evaluation: ev, failure, hints, events } = data;

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold">
            {stock.symbol} {failure && <FailIcon reason={failure} />}
          </h1>
          <CopyButton text={toLlmMarkdown(data)} />
        </div>
        <p className="text-zinc-600 dark:text-zinc-400">
          {stock.name} · {stock.sector} · {stock.market}
        </p>
        {ev && (
          <p className="text-sm text-zinc-500">
            ราคาปิด {baht(ev.price)} บาท วันที่ {thaiDate(ev.price_date)} {ev.stale_price && <Tag tone="red">ราคาไม่อัปเดต</Tag>}
          </p>
        )}
      </div>

      {failure && (
        <p className="rounded-md border border-amber-300 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-950/30">
          <FailIcon reason={failure} /> ดึงข้อมูลไม่ได้ใน batch ล่าสุด: {failure}
        </p>
      )}
      {!ev && !failure && <p className="text-zinc-500">ยังไม่มีผลประเมิน</p>}

      {ev && (
        <>
          <Inclusion ev={ev} />
          <Gates ev={ev} />
          <FairValuePanel ev={ev} />
          <div className="grid gap-6 md:grid-cols-2">
            <Cdc ev={ev} />
            <RiskReward ev={ev} />
          </div>
        </>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <Section title="Catalyst hints">
          {!hints.sector_matched && <p className="mb-2 text-sm text-zinc-500">ไม่มี hint ของ sector นี้ แสดง hint ทั่วไป</p>}
          <ul className="list-disc space-y-1 pl-5">
            {hints.items.map((h) => (
              <li key={h}>{h}</li>
            ))}
          </ul>
        </Section>
        <Section title="Event calendar (6 เดือน)">
          <ul className="mb-4 space-y-1 text-sm">
            {events.length === 0 && <li className="text-zinc-500">ไม่มี event</li>}
            {events.map((e) => (
              <li key={`${e.kind}-${e.id ?? e.label}-${e.date}`} className="flex items-center gap-2">
                <span className="w-28 shrink-0">{thaiDate(e.date)}</span>
                <span className="flex-1">{e.label}</span>
                {e.estimated && <Tag>ประมาณ</Tag>}
                {e.kind === "manual" && e.id != null && (
                  <form action={deleteEvent.bind(null, e.id)}>
                    <button className="text-red-600 hover:underline" aria-label={`ลบ ${e.label}`}>
                      ลบ
                    </button>
                  </form>
                )}
              </li>
            ))}
          </ul>
          <EventForm symbol={stock.symbol} />
        </Section>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-md border border-zinc-200 p-4 dark:border-zinc-800">
      <h2 className="mb-3 font-semibold">{title}</h2>
      {children}
    </section>
  );
}

function Inclusion({ ev }: { ev: Evaluation }) {
  if (ev.candidate_rank != null) {
    return <p className="font-medium text-emerald-700 dark:text-emerald-400">อยู่ใน candidate list อันดับ {ev.candidate_rank}</p>;
  }
  return (
    <div>
      <p className="font-medium">ไม่อยู่ใน candidate list เพราะ</p>
      <ul className="list-disc pl-5 text-zinc-700 dark:text-zinc-300">
        {ev.inclusion.reasons.map((r) => (
          <li key={r}>{r}</li>
        ))}
      </ul>
    </div>
  );
}

function Verdict({ passed }: { passed: boolean | null }) {
  if (passed === null) return <span className="text-zinc-500">ข้าม</span>;
  return passed ? <span className="text-emerald-600">✓ ผ่าน</span> : <span className="text-red-600">✗ ไม่ผ่าน</span>;
}

function Gates({ ev }: { ev: Evaluation }) {
  const rows = gateRows(ev, `≥ ${(ev.liquidity.threshold / 1e6).toLocaleString()} ลบ./วัน`);
  const tally = gateTally(rows);
  return (
    <Section title={`Gates ผ่าน ${tally.passed}/${tally.evaluated} ${ev.quality ? (ev.quality.passed ? "(ผ่าน quality gate)" : "(ไม่ผ่าน quality gate)") : ""}`}>
      <table className="w-full text-sm">
        <thead className="text-left text-zinc-500">
          <tr>
            <th className="py-1 font-medium">เกณฑ์</th>
            <th className="py-1 font-medium">ผล</th>
            <th className="py-1 font-medium">เกณฑ์ที่ใช้</th>
            <th className="py-1 font-medium">ค่าจริง</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((c) => (
            <tr key={c.name} className="border-t border-zinc-100 dark:border-zinc-800">
              <td className="py-1">{c.name === "liquidity" ? "Liquidity" : (CHECK_LABELS[c.name] ?? c.name)}</td>
              <td className="py-1">
                <Verdict passed={c.passed} />
              </td>
              <td className="py-1">{c.threshold}</td>
              <td className="py-1">{c.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {!ev.quality && <p className="mt-2 text-sm text-zinc-500">ไม่ได้ดึงงบเพราะไม่ผ่าน liquidity filter</p>}
      <FairValueGate ev={ev} />
      {ev.quality?.inflection.flag && (
        <p className="mt-2">
          <Tag tone="violet">inflection</Tag> {ev.quality.inflection.reason}
        </p>
      )}
    </Section>
  );
}

function FairValueGate({ ev }: { ev: Evaluation }) {
  if (!ev.fair_value) return null;
  const gate = ev.fair_value.gate;
  if (!gate) return <p className="mt-4 text-sm text-zinc-500">MoS gate: N/A (run นี้รันก่อนมี gate ด้าน fair value)</p>;
  return (
    <div className="mt-4">
      <p className="mb-1 font-medium">
        Gate ด้าน fair value · MoS gate <b>{mosGate(ev)}</b>
      </p>
      <p className="mb-2 text-sm text-zinc-500">
        ทุก gate method ที่คำนวณได้ต้องมี MoS ≥ {pct(gate.min_mos, 0)} และต้องคำนวณได้อย่างน้อย 1 ตัว
      </p>
      <table className="w-full text-sm">
        <tbody>
          {gate.items.map((i) => (
            <tr key={i.method} className="border-t border-zinc-100 dark:border-zinc-800">
              <td className="py-1">{METHOD_SHORT[i.method] ?? i.method}</td>
              <td className="py-1">
                {i.mos === null ? <span className="text-zinc-500">คำนวณไม่ได้</span> : <Verdict passed={i.mos >= gate.min_mos} />}
              </td>
              <td className="py-1">{i.mos === null ? i.reason : `MoS ${pct(i.mos)} (fair value ${baht(i.fair_value)})`}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FairValuePanel({ ev }: { ev: Evaluation }) {
  if (!ev.fair_value) return null;
  const { items, summary, eps_ttm, structure_change, history_gap } = ev.fair_value;
  return (
    <Section title="Fair value panel">
      <p className="mb-2 text-sm">
        <b>{summary.label}</b> · MoS ต่ำสุด {pct(summary.min_mos)} · median {pct(summary.median_mos)} · สูงสุด{" "}
        {pct(summary.max_mos)} · EPS TTM {eps_ttm ?? "N/A"}
      </p>
      {structure_change.flag && (
        <p className="mb-2 text-sm">
          <Tag tone="red">โครงสร้างทุนเปลี่ยน</Tag> {structure_change.reason}
        </p>
      )}
      {history_gap?.flag && (
        <p className="mb-2 text-sm">
          <Tag>ข้อมูลย้อนหลังไม่ครบ</Tag> {history_gap.reason}
        </p>
      )}
      <table className="w-full text-sm">
        <thead className="text-left text-zinc-500">
          <tr className="relative">
            <th className="py-1 font-medium">เกณฑ์</th>
            <th className="py-1 text-right font-medium">Fair value</th>
            <th className="py-1 text-right font-medium">
              MoS
              <Tooltip id="tip-mos" text={MOS_HELP} label="MoS" />
            </th>
            <th className="py-1 pl-4 font-medium">หมายเหตุ</th>
          </tr>
        </thead>
        <tbody>
          {items.map((i) => (
            <tr key={i.method} className="relative border-t border-zinc-100 dark:border-zinc-800">
              <td className="py-1">
                {i.label}
                {FAIR_VALUE_HELP[i.method] && <Tooltip id={`tip-${i.method}`} text={FAIR_VALUE_HELP[i.method]} label={i.label} />}
              </td>
              <td className="py-1 text-right">{baht(i.fair_value)}</td>
              <td className={`py-1 text-right ${i.mos != null && i.mos > 0 ? "text-emerald-600" : ""}`}>{pct(i.mos)}</td>
              <td className="py-1 pl-4 text-zinc-500">{i.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Section>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between border-t border-zinc-100 py-1 text-sm first:border-0 dark:border-zinc-800">
      <dt className="text-zinc-500">{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function Cdc({ ev }: { ev: Evaluation }) {
  const c = ev.cdc;
  return (
    <Section title="CDC ActionZone (daily)">
      {c.state == null ? (
        <p className="text-zinc-500">{c.reason}</p>
      ) : (
        <dl>
          <Row label="State">
            <StateBadge state={c.state} />
          </Row>
          <Row label="Fast EMA">{c.fast?.toFixed(2)}</Row>
          <Row label="Slow EMA">{c.slow?.toFixed(2)}</Row>
          <Row label="Gap (Slow − Fast) / Slow">{pct(c.gap_pct, 2)}</Row>
          <Row label="ความเร็วที่ gap แคบลง">{pct(c.speed, 2)} ต่อวัน</Row>
          <Row label="ETA ถึง cross">{c.eta_days != null ? `${c.eta_days} วันทำการ` : "N/A"}</Row>
          {c.days_since_cross != null && <Row label="Cross ล่าสุด">{c.days_since_cross} วันทำการก่อน</Row>}
        </dl>
      )}
    </Section>
  );
}

function RiskReward({ ev }: { ev: Evaluation }) {
  const r = ev.risk_reward;
  return (
    <Section title="Risk / reward">
      {!r ? (
        <p className="text-zinc-500">ไม่มีข้อมูลงบ จึงคำนวณไม่ได้</p>
      ) : (
        <dl>
          <Row label="Entry (ราคาปิดล่าสุด)">{baht(r.entry)}</Row>
          <Row label="Stop">{baht(r.stop)}</Row>
          <Row label="Target (fair value ที่ต่ำกว่าของ gate methods)">{baht(r.target)}</Row>
          <Row label="Target optimistic (max)">{baht(r.target_optimistic)}</Row>
          <Row label="RRR">
            {r.rrr ?? "N/A"} {r.low_rrr && <Tag tone="red">RRR ต่ำกว่าเกณฑ์</Tag>}
          </Row>
          <Row label="Upside">
            {pct(r.upside)} {r.high_upside && <Tag tone="red">upside สูงผิดปกติ</Tag>}
          </Row>
          {r.reason && <p className="mt-2 text-sm text-zinc-500">{r.reason}</p>}
        </dl>
      )}
    </Section>
  );
}
