import { useMemo, useState } from "react";
import { CodeBlock } from "@/components/Code";
import { cn } from "@/utils/cn";

const THRESHOLDS = { moderate: 3, elevated: 5, high: 8 };
const MAX_IMPERSONATION = 6;
const SUBDOMAIN_THRESHOLD = 10;

const BANDS = [
  { name: "Low", colour: "text-emerald-300", bar: "bg-emerald-400", ring: "ring-emerald-400/40" },
  { name: "Moderate", colour: "text-amber-300", bar: "bg-amber-400", ring: "ring-amber-400/40" },
  { name: "Elevated", colour: "text-orange-300", bar: "bg-orange-400", ring: "ring-orange-400/40" },
  { name: "High", colour: "text-red-300", bar: "bg-red-400", ring: "ring-red-400/40" },
];

function bandFor(score: number) {
  if (score >= THRESHOLDS.high) return BANDS[3];
  if (score >= THRESHOLDS.elevated) return BANDS[2];
  if (score >= THRESHOLDS.moderate) return BANDS[1];
  return BANDS[0];
}

export function RiskLab() {
  const [impersonation, setImpersonation] = useState(2);
  const [subdomains, setSubdomains] = useState(17);
  const [gps, setGps] = useState(true);
  const [secrets, setSecrets] = useState(false);
  const [pii, setPii] = useState(true);

  const contributions = useMemo(() => {
    const rows: { rule: string; points: number; detail: string }[] = [];
    if (impersonation > 0) {
      rows.push({
        rule: "impersonation_keyword",
        points: Math.min(impersonation * 2, MAX_IMPERSONATION),
        detail: `${impersonation} handle(s) contain brand keywords (2 pts each, cap ${MAX_IMPERSONATION})`,
      });
    }
    if (gps) {
      rows.push({ rule: "gps_metadata", points: 3, detail: "published imagery retains GPS coordinates" });
    }
    if (subdomains > SUBDOMAIN_THRESHOLD) {
      rows.push({
        rule: "subdomain_exposure",
        points: 2,
        detail: `${subdomains} unique hostnames > threshold ${SUBDOMAIN_THRESHOLD}`,
      });
    }
    if (secrets) {
      rows.push({ rule: "secret_exposure", points: 4, detail: "credential material detected in assets" });
    }
    if (pii) {
      rows.push({ rule: "pii_metadata", points: 1, detail: "author / device identifiers retained" });
    }
    return rows;
  }, [impersonation, gps, subdomains, secrets, pii]);

  const score = contributions.reduce((sum, c) => sum + c.points, 0);
  const band = bandFor(score);
  const pct = Math.min(100, (score / 12) * 100);

  const json = JSON.stringify(
    {
      score,
      band: band.name,
      counts: { total: contributions.length },
      contributions: contributions.map((c) => ({ rule: c.rule, points: c.points, detail: c.detail })),
    },
    null,
    2,
  );

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <div className="rounded-2xl border border-emerald-500/15 bg-[#0a0f15] p-5">
        <p className="mb-4 font-mono text-[11px] uppercase tracking-[0.2em] text-emerald-400/70">
          heuristic inputs
        </p>

        <div className="space-y-5">
          <div>
            <div className="mb-2 flex items-baseline justify-between">
              <label className="font-mono text-[12px] text-slate-300">
                look-alike handles found
              </label>
              <span className="font-mono text-[12px] text-emerald-300">{impersonation}</span>
            </div>
            <input
              type="range"
              min={0}
              max={5}
              value={impersonation}
              onChange={(e) => setImpersonation(Number(e.target.value))}
              className="w-full accent-emerald-400"
            />
            <p className="mt-1 font-mono text-[10px] text-slate-600">+2 each · capped at +6</p>
          </div>

          <div>
            <div className="mb-2 flex items-baseline justify-between">
              <label className="font-mono text-[12px] text-slate-300">unique subdomains</label>
              <span className="font-mono text-[12px] text-emerald-300">{subdomains}</span>
            </div>
            <input
              type="range"
              min={0}
              max={40}
              value={subdomains}
              onChange={(e) => setSubdomains(Number(e.target.value))}
              className="w-full accent-emerald-400"
            />
            <p className="mt-1 font-mono text-[10px] text-slate-600">+2 when &gt; 10 hostnames</p>
          </div>

          {[
            { label: "GPS coordinates in imagery", value: gps, set: setGps, pts: "+3" },
            { label: "secret / credential detected", value: secrets, set: setSecrets, pts: "+4" },
            { label: "author / device identifiers", value: pii, set: setPii, pts: "+1" },
          ].map((toggle) => (
            <button
              key={toggle.label}
              onClick={() => toggle.set(!toggle.value)}
              className={cn(
                "flex w-full items-center justify-between rounded-lg border px-3 py-2.5 font-mono text-[12px] transition",
                toggle.value
                  ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-200"
                  : "border-slate-700/60 bg-[#070b10] text-slate-500 hover:border-slate-600",
              )}
            >
              <span className="flex items-center gap-2">
                <span
                  className={cn(
                    "grid h-4 w-4 place-items-center rounded border text-[9px]",
                    toggle.value ? "border-emerald-400/60 bg-emerald-400/20" : "border-slate-600",
                  )}
                >
                  {toggle.value ? "✓" : ""}
                </span>
                {toggle.label}
              </span>
              <span className="text-[11px] opacity-70">{toggle.pts}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        <div className={cn("rounded-2xl border border-emerald-500/15 bg-[#0a0f15] p-5 ring-1", band.ring)}>
          <div className="flex items-end justify-between">
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-slate-500">
                engagement risk
              </p>
              <p className={cn("mt-1 text-4xl font-semibold tracking-tight", band.colour)}>
                {band.name}
              </p>
            </div>
            <p className="font-mono text-3xl text-slate-200">
              {score}
              <span className="text-base text-slate-600">/12+</span>
            </p>
          </div>

          <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-800">
            <div
              className={cn("h-full rounded-full transition-all duration-300", band.bar)}
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="mt-2 flex justify-between font-mono text-[10px] text-slate-600">
            <span>Low</span>
            <span>Moderate ≥3</span>
            <span>Elevated ≥5</span>
            <span>High ≥8</span>
          </div>

          <ul className="mt-4 space-y-1.5">
            {contributions.length === 0 && (
              <li className="font-mono text-[11px] text-slate-600">no scoring rule fired</li>
            )}
            {contributions.map((c) => (
              <li
                key={c.rule}
                className="flex items-start justify-between gap-3 border-b border-slate-800/60 pb-1.5 font-mono text-[11px]"
              >
                <span className="text-slate-400">
                  <span className="text-emerald-300">{c.rule}</span> — {c.detail}
                </span>
                <span className="shrink-0 text-amber-300">+{c.points}</span>
              </li>
            ))}
          </ul>
        </div>

        <CodeBlock
          code={json}
          language="text"
          filename="normalized/risk.json"
          maxHeight="260px"
        />
      </div>
    </div>
  );
}
