/**
 * Loads every file of the `reputation-audit-framework/` project at build time
 * (Vite raw glob) and exposes it as a browsable tree.
 */

const globbed = import.meta.glob("/reputation-audit-framework/**/*", {
  query: "?raw",
  eager: true,
  import: "default",
}) as Record<string, string>;

const dotted = import.meta.glob("/reputation-audit-framework/**/.*", {
  query: "?raw",
  eager: true,
  import: "default",
}) as Record<string, string>;

export type Language =
  | "python"
  | "yaml"
  | "markdown"
  | "docker"
  | "bash"
  | "make"
  | "text";

export interface ProjectFile {
  /** Path relative to the project root, e.g. `core/orchestrator.py`. */
  path: string;
  name: string;
  dir: string;
  content: string;
  language: Language;
  lines: number;
  bytes: number;
}

function detectLanguage(path: string): Language {
  const name = path.split("/").pop() ?? "";
  if (name === "Dockerfile" || name.startsWith("Dockerfile.")) return "docker";
  if (name === "Makefile") return "make";
  if (name.endsWith(".py")) return "python";
  if (name.endsWith(".yaml") || name.endsWith(".yml")) return "yaml";
  if (name.endsWith(".md")) return "markdown";
  if (name.endsWith(".sh")) return "bash";
  return "text";
}

const ORDER = [
  "README.md",
  "main.py",
  "config.yaml",
  "requirements.txt",
  "Dockerfile",
  "docker-compose.yml",
  "Makefile",
  "install.sh",
];

export const FILES: ProjectFile[] = Object.entries({ ...globbed, ...dotted })
  .map(([abs, content]) => {
    const path = abs.replace("/reputation-audit-framework/", "");
    const parts = path.split("/");
    return {
      path,
      name: parts[parts.length - 1],
      dir: parts.slice(0, -1).join("/"),
      content,
      language: detectLanguage(path),
      lines: content.split("\n").length,
      bytes: new Blob([content]).size,
    };
  })
  .sort((a, b) => {
    const ai = ORDER.indexOf(a.path);
    const bi = ORDER.indexOf(b.path);
    if (ai !== -1 || bi !== -1) return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
    if (a.dir !== b.dir) return a.dir.localeCompare(b.dir);
    return a.name.localeCompare(b.name);
  });

export interface TreeNode {
  name: string;
  path: string;
  type: "dir" | "file";
  children: TreeNode[];
  file?: ProjectFile;
}

/** Build a nested directory tree from the flat file list. */
export function buildTree(files: ProjectFile[]): TreeNode[] {
  const root: TreeNode = { name: "", path: "", type: "dir", children: [] };
  for (const file of files) {
    const parts = file.path.split("/");
    let cursor = root;
    parts.forEach((part, index) => {
      const isFile = index === parts.length - 1;
      const path = parts.slice(0, index + 1).join("/");
      let next = cursor.children.find((c) => c.name === part && c.path === path);
      if (!next) {
        next = {
          name: part,
          path,
          type: isFile ? "file" : "dir",
          children: [],
          file: isFile ? file : undefined,
        };
        cursor.children.push(next);
      }
      cursor = next;
    });
  }
  const sortNodes = (nodes: TreeNode[]): TreeNode[] => {
    nodes.sort((a, b) => {
      if (a.type !== b.type) return a.type === "dir" ? -1 : 1;
      const ai = ORDER.indexOf(a.path);
      const bi = ORDER.indexOf(b.path);
      if (ai !== -1 || bi !== -1) return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
      return a.name.localeCompare(b.name);
    });
    nodes.forEach((n) => sortNodes(n.children));
    return nodes;
  };
  return sortNodes(root.children);
}

export const TREE = buildTree(FILES);

export const STATS = {
  files: FILES.length,
  lines: FILES.reduce((sum, f) => sum + f.lines, 0),
  python: FILES.filter((f) => f.language === "python").length,
  bytes: FILES.reduce((sum, f) => sum + f.bytes, 0),
};

export function getFile(path: string): ProjectFile | undefined {
  return FILES.find((f) => f.path === path);
}
