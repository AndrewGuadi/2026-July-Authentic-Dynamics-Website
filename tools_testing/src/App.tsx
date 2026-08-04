import { useEffect, useState } from "react";
import { FileExplorer } from "@/components/FileExplorer";
import { RiskLab } from "@/components/RiskLab";
import {
  Extend,
  Hero,
  Legal,
  Modules,
  Pipeline,
  Quickstart,
  ReportPreview,
  Section,
  WorkspaceAndSchema,
} from "@/components/Sections";
import { cn } from "@/utils/cn";

const NAV = [
  { id: "pipeline", label: "pipeline" },
  { id: "modules", label: "modules" },
  { id: "output", label: "output" },
  { id: "source", label: "source" },
  { id: "risk", label: "risk" },
  { id: "report", label: "report" },
  { id: "quickstart", label: "install" },
  { id: "extend", label: "extend" },
  { id: "legal", label: "legal" },
];

export default function App() {
  const [active, setActive] = useState("pipeline");

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) setActive(visible.target.id);
      },
      { rootMargin: "-20% 0px -65% 0px", threshold: [0.05, 0.25, 0.5] },
    );
    NAV.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, []);

  return (
    <div className="min-h-screen bg-[#05080c] text-slate-300">
      <nav className="sticky top-0 z-50 border-b border-emerald-500/10 bg-[#05080c]/85 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-7xl items-center gap-4 px-5 py-3">
          <a href="#top" className="flex shrink-0 items-center gap-2">
            <span className="grid h-7 w-7 place-items-center rounded border border-emerald-400/40 bg-emerald-400/10 font-mono text-[11px] text-emerald-300">
              RAF
            </span>
            <span className="hidden font-mono text-[13px] text-slate-300 sm:inline">
              reputation-audit-framework
            </span>
          </a>
          <div className="ml-auto flex items-center gap-1 overflow-x-auto">
            {NAV.map((item) => (
              <a
                key={item.id}
                href={`#${item.id}`}
                className={cn(
                  "shrink-0 rounded-md px-2.5 py-1.5 font-mono text-[11.5px] transition",
                  active === item.id
                    ? "bg-emerald-400/10 text-emerald-300"
                    : "text-slate-500 hover:text-slate-300",
                )}
              >
                {item.label}
              </a>
            ))}
          </div>
        </div>
      </nav>

      <div id="top">
        <Hero />
      </div>

      <div className="mx-auto w-full max-w-7xl px-5">
        <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-2 rounded-xl border border-amber-400/25 bg-amber-400/[0.04] px-4 py-3">
          <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-amber-300">
            authorized use only
          </span>
          <p className="text-[13px] text-slate-400">
            The CLI refuses to collect anything unless{" "}
            <code className="rounded bg-slate-800/70 px-1.5 py-0.5 font-mono text-[12px] text-amber-200">
              --authorized yes
            </code>{" "}
            is supplied — the gate runs before the workspace is even created (exit code 3).
          </p>
        </div>
      </div>

      <Section
        id="pipeline"
        eyebrow="architecture"
        title="Seven stages, one deterministic pipeline"
        lead="Each stage is an isolated package with a narrow contract, so a module failure degrades the run instead of aborting it."
      >
        <Pipeline />
      </Section>

      <Section
        id="modules"
        eyebrow="collectors"
        title="Passive tooling, config-gated"
        lead="Every collector is optional and toggled in config.yaml. Execution resolves to a native binary or an ephemeral Docker container — Amass is locked to -passive and SpiderFoot filters its module list against an active-technique denylist before launch."
      >
        <Modules />
      </Section>

      <Section
        id="output"
        eyebrow="evidence"
        title="Structured workspace + one finding schema"
        lead="Raw tool output, normalised findings, logs and deliverables live side by side in a timestamped, per-client workspace."
      >
        <WorkspaceAndSchema />
      </Section>

      <Section
        id="source"
        eyebrow="source"
        title="The complete framework"
        lead="Every file below is the real project — browse it, copy any file, or download the whole tree as a zip."
      >
        <FileExplorer />
      </Section>

      <Section
        id="risk"
        eyebrow="heuristics"
        title="Risk engine, live"
        lead="The same weights and thresholds shipped in config.yaml. Move the inputs to see how core/risk.py scores an engagement and what it writes to normalized/risk.json."
      >
        <RiskLab />
      </Section>

      <Section
        id="report"
        eyebrow="deliverable"
        title="Executive Markdown report"
        lead="Rendered on every run, with an optional PDF when wkhtmltopdf is present. This is a real generated example."
      >
        <ReportPreview />
      </Section>

      <Section
        id="quickstart"
        eyebrow="setup"
        title="Installable in one command"
        lead="Local virtualenv or fully containerised — the app image ships ExifTool, Maigret and wkhtmltopdf so it works even without a Docker socket."
      >
        <Quickstart />
      </Section>

      <Section
        id="extend"
        eyebrow="extensibility"
        title="Add a collector in three steps"
        lead="Implement the base class, register it, flip the flag. TruffleHog and theHarvester ship as the reference plugins."
      >
        <Extend />
      </Section>

      <Section
        id="legal"
        eyebrow="safety"
        title="Legal guardrails, not guidelines"
        lead="The constraints below are enforced in code — in the authorization gate, the module allowlists and the argument vectors themselves."
      >
        <Legal />
      </Section>

      <footer className="border-t border-emerald-500/10 bg-[#070b10]">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-3 px-5 py-8 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-mono text-[12px] text-slate-400">
              reputation-audit-framework <span className="text-emerald-400">v1.0.0</span>
            </p>
            <p className="mt-1 text-[12px] text-slate-600">
              Passive OSINT reputation auditing for authorized business engagements.
            </p>
          </div>
          <p className="max-w-md text-[11.5px] leading-relaxed text-slate-600">
            Use only with documented written permission. Unauthorized use may violate the CFAA,
            UK CMA 1990, GDPR/CCPA and equivalent statutes in your jurisdiction.
          </p>
        </div>
      </footer>
    </div>
  );
}
