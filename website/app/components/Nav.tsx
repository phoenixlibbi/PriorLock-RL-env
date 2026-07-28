"use client";

import { useEffect, useState } from "react";

const links = [
  { id: "how-it-works", label: "How it works" },
  { id: "probes", label: "Probes" },
  { id: "soundness", label: "Soundness" },
  { id: "evaluators", label: "Evaluators" },
  { id: "research", label: "Research" },
  { id: "leaderboard", label: "Leaderboard" },
  { id: "contribute", label: "Contribute" },
  { id: "quickstart", label: "Quickstart" },
];

const pages = [{ href: "/implementation", label: "Implementation" }];

export default function Nav() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    const onResize = () => {
      if (window.matchMedia("(min-width: 960px)").matches) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", onResize);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onResize);
      document.body.style.overflow = prev;
    };
  }, [open]);

  function close() {
    setOpen(false);
  }

  return (
    <nav className="nav-bar">
      <div className="nav-inner">
        <a href="/" className="nav-brand" onClick={close}>
          Prior<span style={{ color: "var(--accent)" }}>Lock</span>
        </a>

        <div className="nav-center">
          {links.map((link) => (
            <a key={link.id} href={`/#${link.id}`} className="nav-link">
              {link.label}
            </a>
          ))}
          {pages.map((p) => (
            <a
              key={p.href}
              href={p.href}
              className="nav-link"
              style={{ color: "var(--accent)" }}
            >
              {p.label}
            </a>
          ))}
        </div>

        <div className="nav-right">
          <a
            href="https://github.com/phoenixlibbi/PriorLock-RL-env"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-ghost !px-3 !py-1.5 text-xs"
          >
            <GithubIcon />
            GitHub
          </a>

          <button
            type="button"
            className="nav-menu-btn nav-menu-desktop-hide"
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            aria-controls="mobile-nav"
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <CloseIcon /> : <MenuIcon />}
          </button>
        </div>
      </div>

      {open && (
        <>
          <button
            type="button"
            className="nav-menu-backdrop nav-menu-desktop-hide"
            aria-label="Close menu"
            onClick={close}
          />
          <div
            id="mobile-nav"
            className="nav-menu-panel nav-menu-desktop-hide"
            role="dialog"
            aria-modal="true"
          >
            <div className="flex flex-col gap-1 px-4 py-3">
              {links.map((link) => (
                <a
                  key={link.id}
                  href={`/#${link.id}`}
                  className="nav-menu-link"
                  onClick={close}
                >
                  {link.label}
                </a>
              ))}
              {pages.map((p) => (
                <a
                  key={p.href}
                  href={p.href}
                  className="nav-menu-link"
                  style={{ color: "var(--accent)" }}
                  onClick={close}
                >
                  {p.label}
                </a>
              ))}
              <a
                href="https://github.com/phoenixlibbi/PriorLock-RL-env"
                target="_blank"
                rel="noopener noreferrer"
                className="nav-menu-link"
                onClick={close}
              >
                GitHub ↗
              </a>
            </div>
          </div>
        </>
      )}
    </nav>
  );
}

function MenuIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M4 7h16M4 12h16M4 17h16"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M6 6l12 12M18 6L6 18"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function GithubIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
    </svg>
  );
}
