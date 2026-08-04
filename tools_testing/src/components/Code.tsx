import { useMemo, useState } from "react";
import type { Language } from "@/data/project";
import { cn } from "@/utils/cn";

interface Rule {
  cls: string;
  pattern: string;
}

const COMMON_STRING =
  `"""[\\s\\S]*?"""|'''[\\s\\S]*?'''|[rbfu]?"(?:\\\\.|[^"\\\\])*"|[rbfu]?'(?:\\\\.|[^'\\\\])*'`;

const RULES: Record<Language, Rule[]> = {
  python: [
    { cls: "tok-comment", pattern: `#[^\\n]*` },
    { cls: "tok-string", pattern: COMMON_STRING },
    { cls: "tok-decorator", pattern: `@[\\w.]+` },
    {
      cls: "tok-keyword",
      pattern: `\\b(?:def|class|return|if|elif|else|for|while|try|except|finally|with|as|import|from|raise|pass|break|continue|in|not|and|or|is|None|True|False|lambda|yield|global|assert|del|async|await)\\b`,
    },
    { cls: "tok-self", pattern: `\\b(?:self|cls)\\b` },
    {
      cls: "tok-type",
      pattern: `\\b(?:str|int|bool|float|bytes|list|dict|set|tuple|Path|Optional|Any|List|Dict|Iterable|Sequence|Tuple|Type|Union|Console|Table|Panel)\\b`,
    },
    { cls: "tok-number", pattern: `\\b\\d+(?:\\.\\d+)?\\b` },
    { cls: "tok-func", pattern: `\\b[A-Za-z_]\\w*(?=\\()` },
  ],
  yaml: [
    { cls: "tok-comment", pattern: `#[^\\n]*` },
    { cls: "tok-string", pattern: `"(?:\\\\.|[^"\\\\])*"|'(?:[^'])*'` },
    { cls: "tok-key", pattern: `^[ \\t]*(?:-[ \\t]+)?[\\w.\\-/]+(?=:)` },
    { cls: "tok-punct", pattern: `^[ \\t]*-[ \\t]` },
    { cls: "tok-keyword", pattern: `\\b(?:true|false|null|yes|no)\\b` },
    { cls: "tok-number", pattern: `\\b\\d+(?:\\.\\d+)?\\b` },
    { cls: "tok-var", pattern: `\\$\\{[^}]+\\}` },
  ],
  docker: [
    { cls: "tok-comment", pattern: `#[^\\n]*` },
    {
      cls: "tok-keyword",
      pattern: `^[ \\t]*(?:FROM|RUN|CMD|ENV|ARG|COPY|ADD|WORKDIR|USER|ENTRYPOINT|EXPOSE|VOLUME|LABEL|HEALTHCHECK|SHELL)\\b`,
    },
    { cls: "tok-string", pattern: `"(?:\\\\.|[^"\\\\])*"` },
    { cls: "tok-type", pattern: `\\bAS\\b|\\\\$` },
  ],
  bash: [
    { cls: "tok-comment", pattern: `#[^\\n]*` },
    { cls: "tok-string", pattern: `"(?:\\\\.|[^"\\\\])*"|'(?:[^'])*'` },
    {
      cls: "tok-keyword",
      pattern: `\\b(?:if|then|else|elif|fi|for|in|do|done|while|case|esac|function|return|exit|set|source|local|command|printf|echo|cat|mkdir|python|python3|pip|docker)\\b`,
    },
    { cls: "tok-var", pattern: `\\$\\{?[\\w@#?]+\\}?` },
  ],
  make: [
    { cls: "tok-comment", pattern: `#[^\\n]*` },
    { cls: "tok-key", pattern: `^[a-zA-Z_-]+(?=:)` },
    { cls: "tok-var", pattern: `\\$\\{?\\(?[\\w@#?]+\\)?\\}?` },
    { cls: "tok-string", pattern: `"(?:\\\\.|[^"\\\\])*"` },
  ],
  markdown: [
    { cls: "tok-heading", pattern: `^#{1,6}[^\\n]*` },
    { cls: "tok-string", pattern: "`[^`\\n]+`" },
    { cls: "tok-keyword", pattern: `\\*\\*[^*\\n]+\\*\\*` },
    { cls: "tok-comment", pattern: `^>[^\\n]*` },
    { cls: "tok-punct", pattern: `^[ \\t]*[-*+] |^\\|.*\\|$` },
    { cls: "tok-func", pattern: `\\[[^\\]\\n]+\\]\\([^)\\n]+\\)` },
  ],
  text: [
    { cls: "tok-comment", pattern: `#[^\\n]*` },
    { cls: "tok-punct", pattern: `[├└│─]+` },
  ],
};

interface Token {
  text: string;
  cls?: string;
}

/** Tokenize source text into class-tagged spans for highlighting. */
function tokenize(code: string, language: Language): Token[] {
  const rules = RULES[language] ?? [];
  if (!rules.length) return [{ text: code }];
  const regex = new RegExp(rules.map((r) => `(${r.pattern})`).join("|"), "gm");
  const tokens: Token[] = [];
  let last = 0;
  for (const match of code.matchAll(regex)) {
    const index = match.index ?? 0;
    if (index > last) tokens.push({ text: code.slice(last, index) });
    const groupIndex = match.slice(1).findIndex((g) => g !== undefined);
    tokens.push({ text: match[0], cls: rules[groupIndex]?.cls });
    last = index + match[0].length;
  }
  if (last < code.length) tokens.push({ text: code.slice(last) });
  return tokens;
}

export function Highlighted({ code, language }: { code: string; language: Language }) {
  const tokens = useMemo(() => tokenize(code, language), [code, language]);
  return (
    <>
      {tokens.map((token, i) =>
        token.cls ? (
          <span key={i} className={token.cls}>
            {token.text}
          </span>
        ) : (
          <span key={i}>{token.text}</span>
        ),
      )}
    </>
  );
}

interface CodeBlockProps {
  code: string;
  language: Language;
  filename?: string;
  showLineNumbers?: boolean;
  maxHeight?: string;
  className?: string;
  actions?: React.ReactNode;
}

export function CodeBlock({
  code,
  language,
  filename,
  showLineNumbers = false,
  maxHeight = "none",
  className,
  actions,
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const lineCount = code.split("\n").length;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div
      className={cn(
        "group relative overflow-hidden rounded-xl border border-emerald-500/15 bg-[#080c11]",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-3 border-b border-emerald-500/10 bg-[#0b1117] px-3 py-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-red-500/70" />
          <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-amber-400/70" />
          <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-emerald-400/70" />
          {filename && (
            <span className="ml-2 truncate font-mono text-[11px] text-slate-400">{filename}</span>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {actions}
          <button
            onClick={copy}
            className="rounded-md border border-emerald-500/20 px-2 py-1 font-mono text-[10px] tracking-wide text-emerald-300/80 transition hover:border-emerald-400/50 hover:bg-emerald-400/10 hover:text-emerald-200"
          >
            {copied ? "COPIED ✓" : "COPY"}
          </button>
        </div>
      </div>
      <div className="overflow-auto" style={{ maxHeight }}>
        <div className="flex min-w-full">
          {showLineNumbers && (
            <pre
              aria-hidden
              className="select-none border-r border-emerald-500/10 bg-[#0a0f15] px-3 py-3 text-right font-mono text-[12px] leading-[1.6] text-slate-600"
            >
              {Array.from({ length: lineCount }, (_, i) => i + 1).join("\n")}
            </pre>
          )}
          <pre className="flex-1 px-4 py-3 font-mono text-[12px] leading-[1.6] text-slate-300">
            <code>
              <Highlighted code={code} language={language} />
            </code>
          </pre>
        </div>
      </div>
    </div>
  );
}
