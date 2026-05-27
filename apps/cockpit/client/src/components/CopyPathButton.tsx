// WP-014 — <CopyPathButton />.
//
// Copies a file's absolute filesystem path to the clipboard so the
// founder can open it locally (the cockpit is read-only — editing
// happens in the founder's own editor). On a successful copy, shows a
// transient "Copied" confirmation for 2 seconds.
//
// The Clipboard API requires a secure context; localhost qualifies in
// all major browsers (WP-014 Risks & notes). If the API is somehow
// unavailable, the button degrades gracefully: the click is a no-op
// rather than a thrown error, and the path stays visible in the title
// tooltip so the founder can select-and-copy manually.
//
// References: WP-014 Contract (<CopyPathButton>).

import { useEffect, useRef, useState } from "react";
import styles from "../styles/FilesPanel.module.css";

interface Props {
  /** Absolute filesystem path to copy. */
  absolutePath: string;
}

const CONFIRM_MS = 2000;

export function CopyPathButton({ absolutePath }: Props) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  async function handleCopy() {
    const clipboard = navigator.clipboard;
    if (!clipboard || typeof clipboard.writeText !== "function") {
      // No Clipboard API (non-secure context, or unsupported). The path
      // stays visible in the title tooltip for manual copy.
      return;
    }
    try {
      await clipboard.writeText(absolutePath);
      setCopied(true);
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopied(false), CONFIRM_MS);
    } catch {
      // Permission denied or transient failure — leave the path in the
      // tooltip; do not surface a scary error for a copy affordance.
    }
  }

  // Before the file's data arrives (loading / error states), there is no
  // absolute path to copy — disable rather than copy an empty string.
  const ready = absolutePath.length > 0;

  return (
    <button
      type="button"
      className={styles.copyPathButton}
      onClick={handleCopy}
      disabled={!ready}
      title={absolutePath}
      data-testid="copy-path-button"
    >
      <span aria-hidden="true">📋</span>
      <span>{copied ? "Copied" : "Copy path"}</span>
    </button>
  );
}
