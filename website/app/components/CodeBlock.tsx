"use client";

import { useState } from "react";

type CodeBlockProps = {
  code: string;
  className?: string;
  preClassName?: string;
  /** Inline row: code left, copy button right, vertically centered (hero/one-liners). */
  variant?: "block" | "inline";
};

export default function CodeBlock({
  code,
  className = "",
  preClassName = "",
  variant = "block",
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = code;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    }
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
