import { useState, type ReactNode } from "react";
import { CodeBlock } from "@/components/Code";
import { getFile, STATS } from "@/data/project";
import { cn } from "@/utils/cn";

export function Section({
  id,
  eyebrow,
  title,
  lead,
  children,
}: {
  id: string;
  eyebrow: string;
  title: string;
  lead?: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="mx-auto w-full max-w-7xl px-5 py-16 sm:py-20">
      <div className="mb-8 max-w-3xl">
        <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-emerald-400/70">
          {eyebrow}
        </p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-100 sm:text-3xl">
          {title}
        </h2>
        {lead && <p className="mt-3 text-[15px] leading-relaxed text-slate-400">{lead}</p>}
      </div>
      {children}
    </section>
  );
}

/* ------------------------------------------------------------------ hero */

const RUN_COMMAND = `python main.py run \\
  --full-name "Sarah Mitchell" \\
  --domain "sarahmitchellhomes.com" \\
  --username "sarahmitchellrealtor" \\
  --image-dir "./images" \\
  --authorized yes`;

const BANNER_OUTPUT = `  ___ ___ ___ _   _ _____ _ _____ ___ ___  _  _
 | _ \\ __| _ \\ | | |_   _/_\\_   _|_ _/ _ \\| \\| |
 |   / _||  _/ |_| | | |/ _ \\| |  | | (_) | .\` |
 |_|_\\___|_|  \\___/  |_/_/ \\_\\_| |___\\___/|_|\\_|
      A U D I T   F R A M E W O R K   v1.0.0

╭───────────────────── LEGAL NOTICE ─────────────────────╮
│ AUTHORIZED USE ONLY — PASSIVE RECONNAISSANCE           │
│ 1. Written permission from the audit subject required. │
│ 2. No authentication, paywall or CAPTCHA is bypassed.  │
│ 3. No brute force or intrusive scanning is performed.  │
╰────────────────────────────────────────────────────────╯

▸ running maigret    → sarahmitchellrealtor
▸ running blackbird  → sarahmitchellrealtor
▸ running amass      → sarahmitchellhomes.com   [-passive]
▸ running spiderfoot → sarahmitchellhomes.com   [allowlist]
▸ running exiftool   → ./images

  Risk score: 9   Band: High
  Report: output/sarah_mitchell_2026-02-14/report/report.md`;

export function Hero() {
  return (
    <header className="relative overflow-hidden border-b border-emerald-500/10">
      <div className="raf-grid absolute inset-0" />
      <div className="raf-glow absolute inset-0" />
      <div className="raf-scanline pointer-events-none absolute inset-0" />
      <div className="relative mx-auto grid w-full max-w-7xl gap-10 px-5 pt-16 pb-20 lg:grid-cols-[1.05fr_1fr] lg:items-center lg:pt-24">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-400/5 px-3 py-1 font-mono text-[11px] text-emerald-300">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
            v1.0.0 · passive reconnaissance only
          </div>

          <h1 className="mt-5 text-4xl font-bold tracking-tight text-slate-50 sm:text-5xl">
            reputation
            <span className="text-emerald-400">-</span>audit
            <span className="text-emerald-400">-</span>framework
          </h1>

          <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-slate-400">
            A modular, containerised OSINT reputation audit framework for{" "}
            <span className="text-slate-200">authorized</span> engagements. Enumerates public
            account, domain and media exposure for a client, normalises every tool output into one
            JSON schema, scores it with a deterministic heuristic engine and ships an executive
            Markdown/PDF report — with an authorization gate that runs before anything else.
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <a
              href="#source"
              className="rounded-lg border border-emerald-400/40 bg-emerald-400/10 px-4 py-2 font-mono text-[12px] text-emerald-200 transition hover:bg-emerald-400/20"
            >
              browse source →
            </a>
            <a
              href="#quickstart"
              className="rounded-lg border border-slate-700 px-4 py-2 font-mono text-[12px] text-slate-300 transition hover:border-slate-500 hover:text-slate-100"
            >
              one-command install
            </a>
          </div>

          <dl className="mt-8 grid max-w-lg grid-cols-4 gap-3">
            {[
              { k: "files", v: STATS.files },
              { k: "lines", v: STATS.lines.toLocaleString() },
              { k: "modules", v: 7 },
              { k: "risk bands", v: 4 },
            ].map((s) => (
              <div
                key={s.k}
                className="rounded-lg border border-emerald-500/10 bg-[#0a0f15]/80 px-3 py-2.5"
              >
                <dt className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                  {s.k}
                </dt>
                <dd className="font-mono text-lg text-emerald-300">{s.v}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="space-y-3">
          <CodeBlock code={RUN_COMMAND} language="bash" filename="terminal — cli usage" />
          <CodeBlock code={BANNER_OUTPUT} language="text" filename="stdout" maxHeight="360px" />
        </div>
      </div>
    </header>
  );
}

/* --------------------------------------------------------------- pipeline */

const PIPELINE = [
  { step: "01", name: "authorization gate", file: "core/validator.py", desc: "Exits unless --authorized yes; records operator, scope and UTC attestation." },
  { step: "02", name: "workspace", file: "core/workspace.py", desc: "Creates output/{client}_{date}/ with six evidence directories." },
  { step: "03", name: "collection", file: "modules/*.py", desc: "Runs each enabled tool natively or as an ephemeral container." },
  { step: "04", name: "normalisation", file: "normalization/*.py", desc: "Maps every tool schema onto one canonical finding record." },
  { step: "05", name: "risk engine", file: "core/risk.py", desc: "Config-driven weights → Low / Moderate / Elevated / High." },
  { step: "06", name: "reporting", file: "reporting/*.py", desc: "Executive Markdown, structured JSON, optional wkhtmltopdf PDF." },
  { step: "07", name: "audit trail", file: "core/logger.py", desc: "JSON-lines log of every command, exit code and timestamp." },
];

export function Pipeline() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {PIPELINE.map((stage) => (
        <div
          key={stage.step}
          className="group relative overflow-hidden rounded-xl border border-emerald-500/12 bg-[#0a0f15] p-4 transition hover:border-emerald-400/35"
        >
          <div className="flex items-baseline justify-between">
            <span className="font-mono text-[11px] text-emerald-400/60">{stage.step}</span>
            <span className="font-mono text-[10px] text-slate-600">{stage.file}</span>
          </div>
          <h3 className="mt-2 font-mono text-sm text-slate-100">{stage.name}</h3>
          <p className="mt-1.5 text-[13px] leading-relaxed text-slate-500">{stage.desc}</p>
          <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-emerald-400/40 to-transparent opacity-0 transition group-hover:opacity-100" />
        </div>
      ))}
    </div>
  );
}

/* ---------------------------------------------------------------- modules */

const MODULES = [
  { name: "maigret", tool: "Maigret", input: "--username", exec: "auto", plugin: false, desc: "Public account presence for a handle across OSINT-indexed sites." },
  { name: "blackbird", tool: "Blackbird", input: "--username", exec: "docker", plugin: false, desc: "Second-source corroboration of handle presence." },
  { name: "amass", tool: "OWASP Amass", input: "--domain", exec: "auto", plugin: false, desc: "Passive subdomain enumeration — the -passive flag is hard-locked." },
  { name: "spiderfoot", tool: "SpiderFoot", input: "--domain", exec: "docker", plugin: false, desc: "Passive OSINT correlation; active modules are denylisted pre-flight." },
  { name: "exiftool", tool: "ExifTool", input: "--image-dir", exec: "auto", plugin: false, desc: "EXIF/IPTC/XMP review of client-supplied imagery; GPS + identity leakage." },
  { name: "trufflehog", tool: "TruffleHog", input: "--image-dir", exec: "auto", plugin: true, desc: "Secret detection in local assets; verification disabled, values redacted." },
  { name: "theharvester", tool: "theHarvester", input: "--domain", exec: "docker", plugin: true, desc: "Hostnames + published addresses from passive feeds only." },
];

export function Modules() {
  return (
    <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
      {MODULES.map((m) => (
        <div
          key={m.name}
          className="rounded-xl border border-emerald-500/12 bg-[#0a0f15] p-4 transition hover:border-emerald-400/30"
        >
          <div className="flex items-center justify-between gap-2">
            <h3 className="font-mono text-sm text-emerald-300">{m.name}</h3>
            <span
              className={cn(
                "rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wide",
                m.plugin
                  ? "border-violet-400/30 bg-violet-400/10 text-violet-300"
                  : "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
              )}
            >
              {m.plugin ? "plugin · off" : "enabled"}
            </span>
          </div>
          <p className="mt-1 font-mono text-[11px] text-slate-500">{m.tool}</p>
          <p className="mt-2 text-[13px] leading-relaxed text-slate-400">{m.desc}</p>
          <div className="mt-3 flex flex-wrap gap-1.5 font-mono text-[10px]">
            <span className="rounded bg-slate-800/70 px-1.5 py-0.5 text-slate-400">{m.input}</span>
            <span className="rounded bg-slate-800/70 px-1.5 py-0.5 text-slate-400">exec: {m.exec}</span>
            <span className="rounded bg-slate-800/70 px-1.5 py-0.5 text-emerald-400/70">passive</span>
          </div>
        </div>
      ))}
    </div>
  );
}

/* -------------------------------------------------------------- workspace */

const SCHEMA_JSON = `{
  "type": "username",              // username | domain | image
  "source_tool": "maigret",
  "value": "https://example.social/sarahmitchellrealtor_official",
  "risk_hint": "impersonation_keyword",
  "evidence_file": "usernames/maigret_raw/report_simple.json",
  "timestamp": "2026-02-14T09:31:07+00:00",
  "details": { "site": "example.social", "status": "claimed" }
}`;

export function WorkspaceAndSchema() {
  const tree = getFile("examples/output-tree.txt");
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <div>
        <p className="mb-2 font-mono text-[11px] uppercase tracking-[0.2em] text-emerald-400/70">
          evidence workspace
        </p>
        <CodeBlock
          code={tree?.content ?? ""}
          language="text"
          filename="examples/output-tree.txt"
          maxHeight="440px"
        />
      </div>
      <div className="space-y-4">
        <div>
          <p className="mb-2 font-mono text-[11px] uppercase tracking-[0.2em] text-emerald-400/70">
            canonical finding schema
          </p>
          <CodeBlock code={SCHEMA_JSON} language="text" filename="normalization/schema.py" />
        </div>
        <div className="rounded-xl border border-emerald-500/12 bg-[#0a0f15] p-4">
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-emerald-400/70">
            risk hints
          </p>
          <ul className="mt-3 space-y-1.5 font-mono text-[12px]">
            {[
              ["impersonation_keyword", "+2 each · cap 6", "text-amber-300"],
              ["gps_metadata", "+3", "text-orange-300"],
              ["subdomain_exposure", "+2 when > 10 hosts", "text-amber-300"],
              ["secret_exposure", "+4", "text-red-300"],
              ["pii_metadata", "+1", "text-sky-300"],
              ["informational", "0 · context only", "text-slate-500"],
            ].map(([hint, pts, colour]) => (
              <li key={hint} className="flex items-center justify-between border-b border-slate-800/60 pb-1.5">
                <span className="text-slate-400">{hint}</span>
                <span className={colour}>{pts}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------- quickstart */

const TABS: { id: string; label: string; language: "bash" | "yaml"; code: string }[] = [
  {
    id: "local",
    label: "local install",
    language: "bash",
    code: `# 1. one-command install (creates .venv, installs deps, probes collectors)
./install.sh
source .venv/bin/activate

# 2. confirm which collectors are available
python main.py doctor
python main.py modules

# 3. validate scope without collecting anything
python main.py run --full-name "Sarah Mitchell" \\
  --domain "sarahmitchellhomes.com" \\
  --username "sarahmitchellrealtor" \\
  --image-dir "./images" --authorized yes --dry-run

# 4. run the audit for real
python main.py run --full-name "Sarah Mitchell" \\
  --domain "sarahmitchellhomes.com" \\
  --username "sarahmitchellrealtor" \\
  --image-dir "./images" --authorized yes`,
  },
  {
    id: "docker",
    label: "docker",
    language: "bash",
    code: `# build the app image
docker compose build audit

# pull every collector image (one time)
docker compose --profile tools pull

# run an audit inside the container
docker compose run --rm audit run \\
  --full-name "Sarah Mitchell" \\
  --domain "sarahmitchellhomes.com" \\
  --username "sarahmitchellrealtor" \\
  --image-dir "/app/images" \\
  --authorized yes

# volumes: ./output (rw)  ./images (ro)  ./config.yaml (ro)
#          /var/run/docker.sock  → sibling collector containers`,
  },
  {
    id: "config",
    label: "config.yaml",
    language: "yaml",
    code: `modules:
  maigret: true
  blackbird: true
  amass: true
  spiderfoot: true
  exiftool: true
  trufflehog: false     # plugin-ready, opt-in
  theharvester: false   # plugin-ready, opt-in

default_execution: auto  # native | docker | auto

risk_thresholds:
  high: 8
  elevated: 5
  moderate: 3

risk_weights:
  impersonation_keyword: 2
  gps_metadata: 3
  subdomain_exposure: 2
  secret_exposure: 4
  pii_metadata: 1`,
  },
  {
    id: "cli",
    label: "cli reference",
    language: "bash",
    code: `python main.py run       # execute an audit against an authorized scope
python main.py modules   # registered modules, enabled state, execution mode
python main.py doctor    # which binaries / runtimes are available
python main.py version

# run flags
  --full-name TEXT       client legal/brand name          [required]
  --domain TEXT          client-owned domain in scope
  --username TEXT        primary handle to enumerate
  --image-dir PATH       client-supplied images
  --authorized TEXT      must be "yes"                    [gate]
  --config, -c PATH      alternate config.yaml
  --output-dir, -o PATH  override the evidence root
  --engagement-id TEXT   ticket / matter reference
  --dry-run              validate + print plan only
  --no-pdf               markdown deliverable only
  --verbose, -v          DEBUG console logging

# exit codes
  0 success · 1 module errors · 2 bad scope/config
  3 authorization missing · 130 interrupted`,
  },
];

export function Quickstart() {
  const [active, setActive] = useState(TABS[0].id);
  const tab = TABS.find((t) => t.id === active) ?? TABS[0];
  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setActive(t.id)}
            className={cn(
              "rounded-lg border px-3 py-1.5 font-mono text-[12px] transition",
              active === t.id
                ? "border-emerald-400/50 bg-emerald-400/10 text-emerald-200"
                : "border-slate-800 bg-[#0a0f15] text-slate-500 hover:border-slate-700 hover:text-slate-300",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>
      <CodeBlock code={tab.code} language={tab.language} filename={tab.label} maxHeight="520px" />
    </div>
  );
}

/* ----------------------------------------------------------------- report */

export function ReportPreview() {
  const report = getFile("examples/EXAMPLE_REPORT.md");
  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
      <CodeBlock
        code={report?.content ?? ""}
        language="markdown"
        filename="report/report.md"
        maxHeight="560px"
        showLineNumbers
      />
      <div className="space-y-3">
        {[
          { t: "1. Client summary", d: "Engagement ID, analyst, collection window, headline risk band." },
          { t: "2. Scope confirmation", d: "Every input, the authorization attestation and operator identity." },
          { t: "3. Risk score", d: "Per-rule breakdown: rule, points, rationale, sample evidence." },
          { t: "4. Findings by category", d: "Identity, infrastructure and media tables with evidence paths." },
          { t: "5. Collection coverage", d: "Module status, execution mode, duration — including skips." },
          { t: "6. Remediation checklist", d: "Actionable, hint-driven checkboxes plus standing hygiene." },
          { t: "7. Evidence index", d: "Every raw artefact path written during the run." },
          { t: "8. Appendix", d: "Method, exclusions by design and data-handling statement." },
        ].map((s) => (
          <div key={s.t} className="rounded-lg border border-emerald-500/10 bg-[#0a0f15] p-3">
            <p className="font-mono text-[12px] text-emerald-300">{s.t}</p>
            <p className="mt-1 text-[12.5px] leading-relaxed text-slate-500">{s.d}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ----------------------------------------------------------------- extend */

const EXTEND_CODE = `# 1 — modules/mytool_module.py
class MyToolModule(OSINTModule):
    """One-line description used in reports."""

    name = "mytool"          # must match the config.yaml key
    scope_field = "domain"   # domain | username | image_dir
    category = "domain"      # username | domain | image
    passive = True

    def run(self, scope, workspace) -> ModuleResult:
        target = self.target_value(scope)
        if not target:
            return ModuleResult.skipped(self.name, "no domain in scope")

        mode = self.execution_mode()
        if (blocked := self.unavailable(mode)):
            return blocked

        command = (
            self.docker_command(["--target", target], volumes={workspace.domain: "/out"})
            if mode == "docker"
            else ["mytool", "--target", target]
        )
        result = run_command(command, timeout=self.timeout)
        raw_files = self.save_raw(workspace, result)
        findings = [
            make_finding("domain", self.name, row, "informational", raw_files[0])
            for row in (self.parse_json(result.stdout) or [])
        ]
        return ModuleResult(module=self.name, status="ok", findings=findings,
                            raw_files=raw_files, command=result.printable,
                            execution=mode, duration=result.duration)

# 2 — modules/__init__.py
MODULE_REGISTRY[MyToolModule.name] = MyToolModule
MODULE_ORDER = (*MODULE_ORDER, "mytool")

# 3 — config.yaml
# modules: { mytool: true }   execution: { mytool: auto }
# docker_images: { mytool: org/mytool:latest }   timeouts: { mytool: 600 }`;

export function Extend() {
  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
      <CodeBlock code={EXTEND_CODE} language="python" filename="extension guide" maxHeight="520px" />
      <div className="space-y-3">
        {[
          ["Passive sources only", "If it authenticates, brute forces or solves CAPTCHAs, it does not ship."],
          ["Never raise", "Return ModuleResult.failed() or .skipped(); the engagement always completes."],
          ["Always persist evidence", "Call self.save_raw() and reference the path in every finding."],
          ["Emit canonical findings", "Use make_finding() so the risk engine and report stay consistent."],
          ["Declare your scope field", "domain, username or image_dir — the orchestrator skips you if absent."],
        ].map(([t, d]) => (
          <div key={t} className="rounded-lg border border-emerald-500/10 bg-[#0a0f15] p-3">
            <p className="font-mono text-[12px] text-emerald-300">{t}</p>
            <p className="mt-1 text-[12.5px] leading-relaxed text-slate-500">{d}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ legal */

export function Legal() {
  const never = [
    "bypass authentication or session controls",
    "solve, relay or circumvent CAPTCHAs",
    "cross paywalls or scrape gated content",
    "brute force credentials or subdomains",
    "run active/intrusive scans against hosts",
    "interact with third parties on the client's behalf",
  ];
  const always = [
    "require --authorized yes before any collection",
    "print the legal notice on every invocation",
    "record operator, host and UTC attestation in scope.json",
    "stamp every finding with its collection timestamp",
    "log every command, exit code and duration",
    "keep raw evidence alongside the normalised record",
  ];
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <div className="rounded-2xl border border-red-500/25 bg-red-500/[0.04] p-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-red-300/80">
          this framework never will
        </p>
        <ul className="mt-3 space-y-2">
          {never.map((item) => (
            <li key={item} className="flex gap-2.5 text-[13.5px] text-slate-300">
              <span className="mt-0.5 font-mono text-red-400">✕</span>
              {item}
            </li>
          ))}
        </ul>
      </div>
      <div className="rounded-2xl border border-emerald-500/25 bg-emerald-500/[0.04] p-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-emerald-300/80">
          this framework always will
        </p>
        <ul className="mt-3 space-y-2">
          {always.map((item) => (
            <li key={item} className="flex gap-2.5 text-[13.5px] text-slate-300">
              <span className="mt-0.5 font-mono text-emerald-400">✓</span>
              {item}
            </li>
          ))}
        </ul>
      </div>
      <div className="lg:col-span-2">
        <CodeBlock
          code={`AUTHORIZATION FOR PASSIVE OPEN-SOURCE REPUTATION ASSESSMENT

Client:            ____________________________________________
Authorised signer: ____________________________________________
Assessor:          ____________________________________________
Engagement ID:     ____________________________________________
Window:            ______________  to  ______________

The Client authorises the Assessor to perform a PASSIVE open-source
intelligence assessment of the following assets, which the Client warrants
it owns or is otherwise entitled to have assessed:

  Domain(s):   ____________________________________________
  Handle(s):   ____________________________________________
  Image set:   ____________________________________________

The Assessor will:
  1. Collect only publicly available information.
  2. Not bypass authentication, paywalls, CAPTCHAs or access controls.
  3. Not perform brute-force, credential testing or intrusive scanning.
  4. Not interact with third parties on the Client's behalf.
  5. Record scope, operator identity and UTC collection timestamps.
  6. Store findings confidentially and delete them after ____ days.

Client signature: ______________________  Date: ______________
Assessor signature: ____________________  Date: ______________`}
          language="text"
          filename="README.md — legal disclaimer template"
          maxHeight="340px"
        />
      </div>
    </div>
  );
}
