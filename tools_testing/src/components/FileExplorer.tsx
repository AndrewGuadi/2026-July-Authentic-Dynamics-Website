import { useMemo, useState } from "react";
import JSZip from "jszip";
import { CodeBlock } from "@/components/Code";
import { FILES, STATS, TREE, type ProjectFile, type TreeNode } from "@/data/project";
import { cn } from "@/utils/cn";

const LANG_BADGE: Record<string, string> = {
  python: "text-sky-300 border-sky-400/30 bg-sky-400/10",
  yaml: "text-amber-300 border-amber-400/30 bg-amber-400/10",
  markdown: "text-violet-300 border-violet-400/30 bg-violet-400/10",
  docker: "text-blue-300 border-blue-400/30 bg-blue-400/10",
  bash: "text-emerald-300 border-emerald-400/30 bg-emerald-400/10",
  make: "text-orange-300 border-orange-400/30 bg-orange-400/10",
  text: "text-slate-300 border-slate-400/30 bg-slate-400/10",
};

function icon(node: TreeNode): string {
  if (node.type === "dir") return "▸";
  if (node.name.endsWith(".py")) return "◆";
  if (node.name.endsWith(".yaml") || node.name.endsWith(".yml")) return "◇";
  if (node.name.endsWith(".md")) return "▤";
  return "·";
}

function TreeBranch({
  nodes,
  depth,
  active,
  open,
  onToggle,
  onSelect,
}: {
  nodes: TreeNode[];
  depth: number;
  active: string;
  open: Record<string, boolean>;
  onToggle: (path: string) => void;
  onSelect: (file: ProjectFile) => void;
}) {
  return (
    <ul className="space-y-px">
      {nodes.map((node) => {
        const isOpen = open[node.path] ?? true;
        return (
          <li key={node.path}>
            <button
              onClick={() => (node.type === "dir" ? onToggle(node.path) : node.file && onSelect(node.file))}
              className={cn(
                "flex w-full items-center gap-2 rounded-md px-2 py-[5px] text-left font-mono text-[12px] transition",
                node.type === "dir"
                  ? "text-emerald-300/80 hover:bg-emerald-400/5"
                  : "text-slate-400 hover:bg-emerald-400/5 hover:text-slate-200",
                active === node.path && "bg-emerald-400/10 text-emerald-200 ring-1 ring-emerald-400/30",
              )}
              style={{ paddingLeft: `${depth * 12 + 8}px` }}
            >
              <span
                className={cn(
                  "text-[10px] transition-transform",
                  node.type === "dir" && isOpen && "rotate-90",
                  node.type === "dir" ? "text-emerald-400/70" : "text-slate-600",
                )}
              >
                {icon(node)}
              </span>
              <span className="truncate">{node.name}</span>
              {node.type === "dir" && (
                <span className="ml-auto pr-1 text-[10px] text-slate-600">{node.children.length}</span>
              )}
            </button>
            {node.type === "dir" && isOpen && node.children.length > 0 && (
              <TreeBranch
                nodes={node.children}
                depth={depth + 1}
                active={active}
                open={open}
                onToggle={onToggle}
                onSelect={onSelect}
              />
            )}
          </li>
        );
      })}
    </ul>
  );
}

export function FileExplorer() {
  const [current, setCurrent] = useState<ProjectFile>(
    FILES.find((f) => f.path === "main.py") ?? FILES[0],
  );
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [zipping, setZipping] = useState(false);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return null;
    return FILES.filter(
      (f) => f.path.toLowerCase().includes(q) || f.content.toLowerCase().includes(q),
    ).slice(0, 40);
  }, [query]);

  const download = (file: ProjectFile) => {
    const url = URL.createObjectURL(new Blob([file.content], { type: "text/plain" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = file.name;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const downloadZip = async () => {
    setZipping(true);
    try {
      const zip = new JSZip();
      const root = zip.folder("reputation-audit-framework")!;
      FILES.forEach((f) => root.file(f.path, f.content));
      const blob = await zip.generateAsync({ type: "blob" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "reputation-audit-framework.zip";
      anchor.click();
      URL.revokeObjectURL(url);
    } finally {
      setZipping(false);
    }
  };

  return (
    <div className="rounded-2xl border border-emerald-500/15 bg-[#070b10]/80 p-3 shadow-[0_0_60px_-15px_rgba(16,185,129,0.25)] backdrop-blur">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3 px-1">
        <div className="flex items-center gap-3">
          <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-emerald-400/70">
            source tree
          </span>
          <span className="font-mono text-[11px] text-slate-500">
            {STATS.files} files · {STATS.lines.toLocaleString()} lines
          </span>
        </div>
        <button
          onClick={downloadZip}
          disabled={zipping}
          className="rounded-lg border border-emerald-400/40 bg-emerald-400/10 px-3 py-1.5 font-mono text-[11px] text-emerald-200 transition hover:bg-emerald-400/20 disabled:opacity-50"
        >
          {zipping ? "packaging…" : "↓ download .zip"}
        </button>
      </div>

      <div className="grid gap-3 lg:grid-cols-[300px_minmax(0,1fr)]">
        <div className="flex max-h-[640px] flex-col rounded-xl border border-emerald-500/10 bg-[#0a0f15]">
          <div className="border-b border-emerald-500/10 p-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="grep files + contents…"
              className="w-full rounded-md border border-emerald-500/15 bg-[#070b10] px-2.5 py-1.5 font-mono text-[12px] text-slate-200 outline-none placeholder:text-slate-600 focus:border-emerald-400/40"
            />
          </div>
          <div className="flex-1 overflow-auto p-1.5">
            {results ? (
              <ul className="space-y-px">
                {results.length === 0 && (
                  <li className="px-2 py-2 font-mono text-[12px] text-slate-600">no matches</li>
                )}
                {results.map((file) => (
                  <li key={file.path}>
                    <button
                      onClick={() => setCurrent(file)}
                      className={cn(
                        "w-full truncate rounded-md px-2 py-[5px] text-left font-mono text-[12px] text-slate-400 hover:bg-emerald-400/5 hover:text-slate-200",
                        current.path === file.path && "bg-emerald-400/10 text-emerald-200",
                      )}
                    >
                      {file.path}
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <TreeBranch
                nodes={TREE}
                depth={0}
                active={current.path}
                open={open}
                onToggle={(path) => setOpen((prev) => ({ ...prev, [path]: !(prev[path] ?? true) }))}
                onSelect={setCurrent}
              />
            )}
          </div>
        </div>

        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2 px-1">
            <span
              className={cn(
                "rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase",
                LANG_BADGE[current.language],
              )}
            >
              {current.language}
            </span>
            <span className="font-mono text-[11px] text-slate-500">
              {current.lines} lines · {(current.bytes / 1024).toFixed(1)} KB
            </span>
          </div>
          <CodeBlock
            code={current.content}
            language={current.language}
            filename={`reputation-audit-framework/${current.path}`}
            showLineNumbers
            maxHeight="600px"
            actions={
              <button
                onClick={() => download(current)}
                className="rounded-md border border-emerald-500/20 px-2 py-1 font-mono text-[10px] tracking-wide text-emerald-300/80 transition hover:border-emerald-400/50 hover:bg-emerald-400/10 hover:text-emerald-200"
              >
                DOWNLOAD
              </button>
            }
          />
        </div>
      </div>
    </div>
  );
}
