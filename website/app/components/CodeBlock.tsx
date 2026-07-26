"use client";

import { useRef, useState } from "react";

type CodeBlockProps = {
  code: string;
  className?: string;
  preClassName?: string;
  /** Inline row: code left, copy button right, vertically centered (hero/one-liners). */
  variant?: "block" | "inline";
};

/** Sync copy — must run in the click call stack (preserves user activation). */
function fallbackCopy(text: string): boolean {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.setAttribute("readonly", "");
  ta.setAttribute("aria-hidden", "true");
  // Keep in viewport; some engines reject offscreen/opacity-0 targets.
  ta.style.cssText =
    "position:fixed;top:0;left:0;width:2em;height:2em;padding:0;border:0;outline:none;box-shadow:none;background:transparent;opacity:0.01;z-index:2147483647;";
  document.body.appendChild(ta);

  const prevActive = document.activeElement as HTMLElement | null;
  ta.focus({ preventScroll: true });
  ta.select();
  ta.setSelectionRange(0, ta.value.length);

  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch {
    ok = false;
  }

  document.body.removeChild(ta);
  prevActive?.focus?.({ preventScroll: true });
  return ok;
}

export default function CodeBlock({
  code,
  className = "",
  preClassName = "",
  variant = "block",
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const copyGenRef = useRef(0);

  function handleCopy() {
    const gen = ++copyGenRef.current;

    // Sync-copy first. Async clipboard.writeText can take seconds then reject
    // with "Document is not focused", and by then user activation is gone.
    if (fallbackCopy(code)) {
      setCopied(true);
      window.setTimeout(() => {
        if (gen === copyGenRef.current) setCopied(false);
      }, 1600);
      return;
    }

    if (!navigator.clipboard?.writeText) return;

    void navigator.clipboard.writeText(code).then(
      () => {
        if (gen !== copyGenRef.current) return;
        setCopied(true);
        window.setTimeout(() => {
          if (gen === copyGenRef.current) setCopied(false);
        }, 1600);
      },
      () => {
        /* ignore — sync path already failed */
      },
    );
  }

  const btn = (
    <button
      type="button"
      className="code-copy-btn"
      onClick={handleCopy}
      aria-label={copied ? "Copied" : "Copy code"}
    >
      {copied ? (
        <>
          <CheckIcon />
          Copied
        </>
      ) : (
        <>
          <CopyIcon />
          Copy
        </>
      )}
    </button>
  );

  if (variant === "inline") {
    return (
      <div className={`code-block code-block-inline ${className}`.trim()}>
        <pre className={preClassName}>{code}</pre>
        {btn}
      </div>
    );
  }

  return (
    <div className={`code-block code-block-stack ${className}`.trim()}>
      <div className="code-block-toolbar">{btn}</div>
      <pre className={preClassName}>{code}</pre>
    </div>
  );
}

function CopyIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect
        x="9"
        y="9"
        width="13"
        height="13"
        rx="2"
        stroke="currentColor"
        strokeWidth="2"
      />
      <path
        d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"
        stroke="currentColor"
        strokeWidth="2"
      />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M20 6 9 17l-5-5"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
