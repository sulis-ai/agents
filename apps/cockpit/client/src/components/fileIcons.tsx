// Files redesign (Direction B) — file-type iconography (Heroicons).
//
// One place that maps a path / node-kind to its Heroicon, so the tree,
// the folder-overview list, and the breadcrumb all icon files the same
// way. Mini (20/solid) glyphs, `currentColor` (the CSS sets the colour:
// folders teal via .folder .ti / .oi, everything else muted). Pure
// presentation — no state.

import {
  FolderIcon,
  FolderOpenIcon,
  DocumentIcon,
  DocumentTextIcon,
  CodeBracketSquareIcon,
  PhotoIcon,
} from "@heroicons/react/20/solid";

type IconCmp = typeof DocumentIcon;

const CODE_EXT = new Set([
  "ts", "tsx", "js", "jsx", "mjs", "cjs", "json", "css", "scss", "html",
  "htm", "py", "rb", "go", "rs", "java", "kt", "c", "h", "cpp", "sh",
  "bash", "zsh", "yaml", "yml", "toml", "sql", "php", "swift", "lua",
]);
const DOC_EXT = new Set(["md", "markdown", "txt", "rst", "adoc"]);
const IMG_EXT = new Set(["png", "jpg", "jpeg", "gif", "svg", "webp", "ico", "bmp", "avif"]);

function ext(path: string): string {
  const base = path.split("/").pop() ?? path;
  const dot = base.lastIndexOf(".");
  return dot > 0 ? base.slice(dot + 1).toLowerCase() : "";
}

/** Pick the icon component for a file path (by extension). */
export function fileIconFor(path: string): IconCmp {
  const e = ext(path);
  if (DOC_EXT.has(e)) return DocumentTextIcon;
  if (CODE_EXT.has(e)) return CodeBracketSquareIcon;
  if (IMG_EXT.has(e)) return PhotoIcon;
  return DocumentIcon;
}

/** Pick the icon component for a directory (open vs closed). */
export function folderIconFor(expanded: boolean): IconCmp {
  return expanded ? FolderOpenIcon : FolderIcon;
}

interface NodeIconProps {
  kind: "file" | "directory";
  path: string;
  expanded?: boolean;
  className?: string;
}

/** Render the icon for a tree/overview node. */
export function NodeIcon({ kind, path, expanded = false, className }: NodeIconProps) {
  const Cmp = kind === "directory" ? folderIconFor(expanded) : fileIconFor(path);
  return <Cmp className={className} aria-hidden="true" />;
}
