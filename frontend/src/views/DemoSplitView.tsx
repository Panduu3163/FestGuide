import { useEffect, useRef, useState } from "react";
import { ExternalLink, RefreshCw, SunMoon } from "lucide-react";
import { applyThemeMode, getResetIncludeCustom, resetDemo, resolveInitialTheme, type ThemeMode } from "../api";
import { BrandLockup } from "../components/BrandMark";

export function DemoSplitView() {
  const [activeTab, setActiveTab] = useState<"student" | "organizer">("student");
  const [theme, setTheme] = useState<ThemeMode>(resolveInitialTheme);
  const [resetKey, setResetKey] = useState(0);
  const studentFrameRef = useRef<HTMLIFrameElement>(null);
  const orgFrameRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    applyThemeMode(theme);
    const payload = { type: "fg_theme", mode: theme };
    studentFrameRef.current?.contentWindow?.postMessage(payload, window.location.origin);
    orgFrameRef.current?.contentWindow?.postMessage(payload, window.location.origin);
  }, [theme]);

  const handleReset = async () => {
    await resetDemo(getResetIncludeCustom());
    setResetKey((k) => k + 1);
  };

  return (
    <div className="h-[100dvh] flex flex-col overflow-hidden bg-[var(--canvas)] text-[var(--text)]">
      {/* Master Header */}
      <header
        className="shrink-0 px-4 py-2.5 border-b flex items-center justify-between gap-3 backdrop-blur-xl"
        style={{ background: "var(--surface-glass)", borderColor: "var(--border)" }}
      >
        <div className="flex items-center gap-3 min-w-0">
          <BrandLockup compact />
          <div className="hidden xl:flex items-center gap-1.5 text-[11px] font-mono-tab text-[var(--muted)]">
            <span className="px-2.5 py-0.5 rounded-full bento-soft">1. Ask or register left</span>
            <span>→</span>
            <span className="px-2.5 py-0.5 rounded-full bento-soft">2. Decide on right</span>
            <span>→</span>
            <span className="px-2.5 py-0.5 rounded-full bento-soft">3. Live Ticket sync</span>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={handleReset}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bento-card hover:border-[#0f9d8a] text-xs font-semibold cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5 text-[var(--muted)]" />
            <span>Reset demo</span>
          </button>
          <button
            type="button"
            aria-label="Toggle theme"
            onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
            className="p-1.5 rounded-xl bento-card hover:border-[#0f9d8a] cursor-pointer"
          >
            <SunMoon className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Mobile / Narrow Segmented Switcher */}
      <div className="lg:hidden shrink-0 px-3 pt-2.5 flex gap-2">
        <button
          type="button"
          onClick={() => setActiveTab("student")}
          className={`flex-1 py-2 rounded-xl text-xs font-bold border transition cursor-pointer ${
            activeTab === "student"
              ? "bg-[#0f9d8a] text-white border-[#0f9d8a] shadow"
              : "bento-card text-[var(--muted)]"
          }`}
        >
          Student Workspace
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("organizer")}
          className={`flex-1 py-2 rounded-xl text-xs font-bold border transition cursor-pointer ${
            activeTab === "organizer"
              ? "bg-[#0f9d8a] text-white border-[#0f9d8a] shadow"
              : "bento-card text-[var(--muted)]"
          }`}
        >
          Organizer Console
        </button>
      </div>

      {/* Dual Split Panes */}
      <div className="flex-1 min-h-0 p-2.5 grid grid-cols-1 lg:grid-cols-2 gap-3">
        <section
          className={`bento-card rounded-2xl overflow-hidden flex-col min-h-0 ${
            activeTab === "student" ? "flex" : "hidden lg:flex"
          }`}
        >
          <div
            className="h-8 shrink-0 px-3 border-b flex items-center justify-between text-[10px] font-mono-tab uppercase tracking-wider font-bold text-[var(--muted)]"
            style={{ background: "var(--surface-soft)", borderColor: "var(--border)" }}
          >
            <span>Student Workspace</span>
            <a
              href="/"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-[#0f9d8a] hover:underline"
            >
              Open standalone <ExternalLink className="w-3 h-3" />
            </a>
          </div>
          <iframe
            ref={studentFrameRef}
            key={`s-${resetKey}`}
            src="/"
            title="Student workspace"
            className="flex-1 min-h-0 w-full border-0"
          />
        </section>

        <section
          className={`bento-card rounded-2xl overflow-hidden flex-col min-h-0 ${
            activeTab === "organizer" ? "flex" : "hidden lg:flex"
          }`}
        >
          <div
            className="h-8 shrink-0 px-3 border-b flex items-center justify-between text-[10px] font-mono-tab uppercase tracking-wider font-bold text-[var(--muted)]"
            style={{ background: "var(--surface-soft)", borderColor: "var(--border)" }}
          >
            <span>Organizer Console</span>
            <a
              href="/organizer"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-[#0f9d8a] hover:underline"
            >
              Open standalone <ExternalLink className="w-3 h-3" />
            </a>
          </div>
          <iframe
            ref={orgFrameRef}
            key={`o-${resetKey}`}
            src="/organizer"
            title="Organizer console"
            className="flex-1 min-h-0 w-full border-0"
          />
        </section>
      </div>
    </div>
  );
}
