import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Check,
  CheckCircle2,
  Coins,
  ExternalLink,
  HelpCircle,
  RefreshCw,
  SunMoon,
  X,
  XCircle,
} from "lucide-react";
import {
  applyThemeMode,
  getConfig,
  getOrganizerPending,
  getOverview,
  getResetIncludeCustom,
  postOrganizerDecision,
  resetDemo,
  resolveInitialTheme,
  type ThemeMode,
} from "../api";
import type { OverviewData, PendingItem, SessionDecision } from "../types";
import { ago, initials } from "../utils";
import { BrandLockup } from "../components/BrandMark";

function RequestDossier({
  item,
  pin,
  onFocusInput,
  onBlurInput,
  onDecided,
}: {
  item: PendingItem;
  pin: string;
  onFocusInput: () => void;
  onBlurInput: () => void;
  onDecided: (d: SessionDecision) => Promise<void>;
}) {
  const [note, setNote] = useState("");
  const [err, setErr] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const req = item.request;

  const decide = async (status: "approved" | "rejected") => {
    setErr("");
    setSubmitting(true);
    try {
      await postOrganizerDecision(item.thread_id, status, note, pin);
      await onDecided({
        event: req.event_name,
        who: item.leader_name,
        status,
        note,
      });
    } catch (error) {
      setErr(error instanceof Error ? error.message : "Could not record decision.");
      setSubmitting(false);
    }
  };

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96 }}
      className="bento-card rounded-3xl p-5 space-y-4 border-l-4"
      style={{ borderLeftColor: req.kind === "exception" ? "var(--gold)" : "var(--teal)" }}
    >
      <div className="flex items-baseline justify-between gap-2 flex-wrap border-b pb-3" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="font-display font-bold text-lg text-[var(--text)]">
            {req.kind === "exception" ? "Exception Request" : "Team Registration"} · {req.event_name}
          </h3>
          <span
            className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono-tab font-bold uppercase ${
              req.kind === "exception"
                ? "bg-[var(--gold-soft)] text-amber-700 dark:text-amber-300 border border-[#c99a2e]/35"
                : "bg-[var(--teal-soft)] text-[#0f9d8a] dark:text-teal-300 border border-[#0f9d8a]/30"
            }`}
          >
            {req.kind}
          </span>
        </div>
        <span className="text-xs font-mono-tab text-[var(--muted)]">asked {ago(item.asked_at)}</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-3">
          {/* Team Roster Pills */}
          <div className="flex flex-wrap gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-[var(--teal-soft)] border border-[#0f9d8a]/35">
              <span className="w-5 h-5 rounded-full bg-[#0f9d8a] text-white font-mono-tab text-[10px] flex items-center justify-center font-bold">
                {initials(item.leader_name)}
              </span>
              <span>{item.leader_name}</span>
              <span className="font-mono-tab text-[10px] text-[var(--muted)]">lead · {req.leader_id}</span>
            </span>
            {req.member_ids.map((mid, i) => (
              <span
                key={mid}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bento-soft"
              >
                <span className="w-5 h-5 rounded-full bento-card font-mono-tab text-[10px] flex items-center justify-center font-bold">
                  {initials(item.member_names[i])}
                </span>
                <span>{item.member_names[i]}</span>
                <span className="font-mono-tab text-[10px] text-[var(--muted)]">{mid}</span>
              </span>
            ))}
          </div>

          <div className="inline-flex items-center gap-1.5 text-xs text-[var(--muted)]">
            <Coins className="w-3.5 h-3.5 text-[#c99a2e]" />
            <span>{req.fee_note}</span>
          </div>

          {/* Eligibility & Team Checks */}
          <div className="space-y-2 pt-2 border-t" style={{ borderColor: "var(--border)" }}>
            {req.checks.map((k, idx) => (
              <div key={idx} className="bento-soft rounded-xl px-3 py-2 text-xs space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold flex items-center gap-1.5">
                    {k.eligible === true ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-[#0f9d8a]" />
                    ) : k.eligible === false ? (
                      <XCircle className="w-3.5 h-3.5 text-rose-500" />
                    ) : (
                      <HelpCircle className="w-3.5 h-3.5 text-amber-500" />
                    )}
                    {k.student}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-mono-tab font-bold ${
                      k.eligible === true
                        ? "bg-teal-500/15 text-teal-700 dark:text-teal-300"
                        : k.eligible === false
                          ? "bg-rose-500/15 text-rose-600 dark:text-rose-400"
                          : "bg-amber-500/15 text-amber-700 dark:text-amber-300"
                    }`}
                  >
                    {k.eligible === true ? "eligible" : k.eligible === false ? "not eligible" : "unclear"}
                  </span>
                </div>
                {k.problems.map((p, pi) => (
                  <div key={pi} className="text-rose-600 dark:text-rose-400 pl-5">{p}</div>
                ))}
                {k.unclear.map((u, ui) => (
                  <div key={ui} className="text-amber-700 dark:text-amber-300 pl-5">{u}</div>
                ))}
              </div>
            ))}

            {(req.team_problems || []).map((tp, ti) => (
              <div key={ti} className="rounded-xl px-3 py-2 text-xs bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 font-medium">
                ✕ Team size: {tp}
              </div>
            ))}
          </div>
        </div>

        {/* Right: Rulebook Clauses & Transcript */}
        <div className="space-y-2.5">
          {req.cited_rules.map((r, ri) => (
            <div key={ri} className="bento-soft rounded-xl p-3 border-l-2 border-l-[#0f9d8a] text-xs space-y-1">
              <div className="font-mono-tab text-[10px] font-bold uppercase text-[#0f9d8a]">{r.source}</div>
              <p className="text-[var(--text-2)] leading-relaxed">
                {r.text.slice(0, 260)}
                {r.text.length > 260 ? "…" : ""}
              </p>
            </div>
          ))}

          <div className="bento-soft rounded-xl p-3 text-xs space-y-1">
            <div className="font-mono-tab text-[10px] uppercase font-bold text-[var(--muted)]">
              Student Wrote
            </div>
            <div className="italic text-[var(--text)]">“{req.student_message}”</div>
          </div>
        </div>
      </div>

      {/* Decision Action Row */}
      <div className="pt-3 border-t flex flex-wrap items-center gap-2" style={{ borderColor: "var(--border)" }}>
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          onFocus={onFocusInput}
          onBlur={onBlurInput}
          placeholder="Organizer note (required to reject)"
          aria-label="Organizer note"
          className="flex-1 min-w-[200px] rounded-xl px-3 py-2 bento-soft text-sm outline-none focus:border-[#0f9d8a]"
        />
        <button
          type="button"
          disabled={submitting}
          onClick={() => void decide("approved")}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#0f9d8a] hover:bg-[#0c8272] text-white text-xs font-bold shadow-md shadow-teal-600/20 disabled:opacity-50 cursor-pointer"
        >
          <Check className="w-3.5 h-3.5" /> Approve
        </button>
        <button
          type="button"
          disabled={submitting}
          onClick={() => void decide("rejected")}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold shadow-md shadow-rose-600/20 disabled:opacity-50 cursor-pointer"
        >
          <X className="w-3.5 h-3.5" /> Reject
        </button>
        {err && <div className="w-full text-xs font-semibold text-rose-600 dark:text-rose-400">{err}</div>}
      </div>
    </motion.article>
  );
}

export function OrganizerConsole({ framed }: { framed: boolean }) {
  const [items, setItems] = useState<PendingItem[]>([]);
  const [overview, setOverview] = useState<OverviewData>({ events: [], registrations: [] });
  const [decided, setDecided] = useState<SessionDecision[]>([]);
  const [pin, setPin] = useState("");
  const [isDemo, setIsDemo] = useState(false);
  const [err, setErr] = useState("");
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [theme, setTheme] = useState<ThemeMode>(resolveInitialTheme);
  const pausedPoll = useRef(false);
  const toastTimer = useRef<number | undefined>(undefined);

  const showToast = useCallback((msg: string) => {
    setToastMsg(msg);
    window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToastMsg(null), 3000);
  }, []);

  useEffect(() => {
    applyThemeMode(theme);
  }, [theme]);

  useEffect(() => {
    const onMsg = (ev: MessageEvent) => {
      if (ev.origin !== window.location.origin) return;
      if (ev.data?.type === "fg_theme" && (ev.data.mode === "light" || ev.data.mode === "dark")) {
        setTheme(ev.data.mode);
      }
    };
    window.addEventListener("message", onMsg);
    return () => window.removeEventListener("message", onMsg);
  }, []);

  const refresh = useCallback(async (force = false) => {
    if (pausedPoll.current && !force) return;
    try {
      const [pendingList, ov] = await Promise.all([
        getOrganizerPending(pin || undefined),
        getOverview(),
      ]);
      setItems(pendingList);
      setOverview(ov);
      setErr("");
    } catch (error) {
      setErr(error instanceof Error ? error.message : "Could not load queue.");
    }
  }, [pin]);

  useEffect(() => {
    getConfig().then((c) => setIsDemo(c.demo)).catch(() => {});
  }, []);

  useEffect(() => {
    void refresh(true);
    const id = window.setInterval(() => void refresh(false), 3000);
    return () => window.clearInterval(id);
  }, [refresh]);

  const handleReset = async () => {
    await resetDemo(getResetIncludeCustom());
    setDecided([]);
    await refresh(true);
    showToast("All chats and registrations reset.");
  };

  const approvedCount = overview.registrations.filter((r) => r.status === "approved").length;
  const rejectedCount = overview.registrations.filter((r) => r.status === "rejected").length;

  return (
    <div className="min-h-[100dvh] flex flex-col bg-[var(--canvas)] text-[var(--text)]">
      <header
        className={`sticky top-0 z-20 border-b backdrop-blur-xl ${
          framed ? "px-3 py-2" : "px-3 sm:px-5 py-2.5"
        }`}
        style={{
          background: framed ? "var(--surface-soft)" : "var(--surface-glass)",
          borderColor: "var(--border)",
        }}
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2.5 flex-wrap">
            {!framed && <BrandLockup compact />}
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono-tab font-bold uppercase bento-soft text-[var(--muted)]">
              Organizer
            </span>
            <span className="inline-flex items-center gap-1.5 text-xs font-bold text-[#0f9d8a] dark:text-teal-300">
              <span className="relative w-2 h-2 rounded-full bg-[#0f9d8a] sonar-dot text-[#0f9d8a]" />
              Live
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono-tab font-semibold bento-card">
              {items.length} waiting
            </span>
          </div>

          <div className="flex items-center gap-1.5 flex-wrap">
            {!isDemo && (
              <input
                type="password"
                value={pin}
                onChange={(e) => setPin(e.target.value)}
                placeholder="PIN (if set)"
                aria-label="Organizer PIN"
                className="w-28 rounded-xl px-2.5 py-1.5 bento-card text-xs outline-none focus:border-[#0f9d8a]"
              />
            )}
            <button
              type="button"
              onClick={handleReset}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bento-card hover:border-[#0f9d8a] text-xs font-semibold cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5 text-[var(--muted)]" />
              <span>Reset demo</span>
            </button>

            {!framed && (
              <>
                <button
                  type="button"
                  aria-label="Toggle theme"
                  onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
                  className="p-1.5 rounded-xl bento-card hover:border-[#0f9d8a] cursor-pointer"
                >
                  <SunMoon className="w-4 h-4" />
                </button>
                <a
                  href="/"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl bento-card hover:border-[#0f9d8a] text-xs font-semibold"
                >
                  <span>Student page</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </>
            )}
          </div>
        </div>
      </header>

      <main className={`w-full max-w-5xl mx-auto space-y-5 ${framed ? "p-3.5" : "p-4 sm:p-6"}`}>
        {/* 3 Animated Bento Metric Tiles */}
        <section className="grid grid-cols-1 sm:grid-cols-3 gap-3" aria-label="Queue metrics">
          <div className="bento-card rounded-2xl p-4 flex sm:flex-col justify-between items-center sm:items-start gap-1">
            <span className="text-[11px] font-mono-tab uppercase font-bold text-[var(--muted)]">
              Pending Review
            </span>
            <span
              className={`font-display text-2xl font-bold font-mono-tab ${
                items.length > 0 ? "text-amber-600 dark:text-amber-400" : "text-[var(--text)]"
              }`}
            >
              {items.length}
            </span>
          </div>

          <div className="bento-card rounded-2xl p-4 flex sm:flex-col justify-between items-center sm:items-start gap-1">
            <span className="text-[11px] font-mono-tab uppercase font-bold text-[var(--muted)]">
              Approved Teams
            </span>
            <span className="font-display text-2xl font-bold font-mono-tab text-[#0f9d8a] dark:text-teal-300">
              {approvedCount}
            </span>
          </div>

          <div className="bento-card rounded-2xl p-4 flex sm:flex-col justify-between items-center sm:items-start gap-1">
            <span className="text-[11px] font-mono-tab uppercase font-bold text-[var(--muted)]">
              Rejected Records
            </span>
            <span className="font-display text-2xl font-bold font-mono-tab text-rose-600 dark:text-rose-400">
              {rejectedCount}
            </span>
          </div>
        </section>

        {/* Approval Queue */}
        <section className="space-y-2.5">
          <div className="flex items-center justify-between px-1">
            <span className="text-[11px] font-mono-tab uppercase font-bold text-[var(--muted)]">
              Approval Queue
            </span>
            <span className="text-[11px] font-mono-tab text-[var(--muted)]">
              Polling checkpoints
            </span>
          </div>

          {err ? (
            <div className="bento-card rounded-2xl p-4 border-l-4 border-l-rose-500 text-xs font-semibold text-rose-600 dark:text-rose-400">
              {err}
            </div>
          ) : items.length === 0 ? (
            <div className="bento-card rounded-2xl p-4 border-l-4 border-l-[#0f9d8a] flex items-center gap-3 text-xs sm:text-sm text-[var(--text-2)]">
              <CheckCircle2 className="w-4 h-4 text-[#0f9d8a] shrink-0" />
              <span>Queue clear — 0 registrations awaiting review. New requests appear automatically.</span>
            </div>
          ) : (
            <div className="space-y-4">
              <AnimatePresence>
                {items.map((p) => (
                  <RequestDossier
                    key={p.thread_id}
                    item={p}
                    pin={pin}
                    onFocusInput={() => { pausedPoll.current = true; }}
                    onBlurInput={() => { pausedPoll.current = false; }}
                    onDecided={async (d) => {
                      pausedPoll.current = false;
                      setDecided((prev) => [d, ...prev]);
                      showToast(
                        d.status === "approved"
                          ? "Approved. Student view updated."
                          : "Rejected with reason."
                      );
                      await refresh(true);
                    }}
                  />
                ))}
              </AnimatePresence>
            </div>
          )}
        </section>

        {/* Session Decisions */}
        {decided.length > 0 && (
          <section className="space-y-2">
            <div className="text-[11px] font-mono-tab uppercase font-bold text-[var(--muted)] px-1">
              Decided This Visit
            </div>
            <div className="space-y-2">
              {decided.map((d, i) => (
                <div
                  key={i}
                  className="bento-card rounded-2xl px-4 py-2.5 flex items-center justify-between gap-2 text-xs"
                >
                  <span className="font-medium truncate">
                    {d.who} · {d.event}
                    {d.note ? ` · “${d.note}”` : ""}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-mono-tab font-bold uppercase ${
                      d.status === "approved"
                        ? "bg-teal-500/15 text-teal-700 dark:text-teal-300"
                        : "bg-rose-500/15 text-rose-600 dark:text-rose-400"
                    }`}
                  >
                    {d.status}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Live Official Registrations Ledger */}
        <section className="space-y-2.5">
          <div className="flex items-center justify-between px-1">
            <span className="text-[11px] font-mono-tab uppercase font-bold text-[var(--muted)]">
              Official Registrations Ledger (SQLite)
            </span>
            <span className="text-[11px] font-mono-tab text-[var(--muted)]">
              {overview.registrations.length} records
            </span>
          </div>

          <div className="bento-card rounded-2xl overflow-hidden">
            {/* Desktop / Tablet Table */}
            <div className="hidden sm:block overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs sm:text-sm">
                <thead>
                  <tr className="bento-soft border-b text-[10px] font-mono-tab uppercase text-[var(--muted)]" style={{ borderColor: "var(--border)" }}>
                    <th className="py-2.5 px-3.5">Ref</th>
                    <th className="py-2.5 px-3.5">Event</th>
                    <th className="py-2.5 px-3.5">Team</th>
                    <th className="py-2.5 px-3.5">Status</th>
                    {!framed && <th className="py-2.5 px-3.5">Organizer Note</th>}
                  </tr>
                </thead>
                <tbody>
                  {overview.registrations.map((r) => {
                    const teamStr = r.member_names?.length
                      ? r.member_names.map((n, i) => `${n} (${r.member_ids[i] || ""})`).join(", ")
                      : `${r.leader_name} (${r.leader_id})`;
                    return (
                      <tr key={r.ref} className="border-b last:border-b-0" style={{ borderColor: "var(--border)" }}>
                        <td className="py-2.5 px-3.5 font-mono-tab font-bold whitespace-nowrap">{r.ref}</td>
                        <td className="py-2.5 px-3.5 font-medium">{r.event_name}</td>
                        <td className="py-2.5 px-3.5 text-[var(--text-2)]">{teamStr}</td>
                        <td className="py-2.5 px-3.5 whitespace-nowrap">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-mono-tab font-bold ${
                              r.status === "approved"
                                ? "bg-teal-500/15 text-teal-700 dark:text-teal-300"
                                : "bg-rose-500/15 text-rose-600 dark:text-rose-400"
                            }`}
                          >
                            {r.status}
                          </span>
                        </td>
                        {!framed && (
                          <td className="py-2.5 px-3.5 text-[var(--muted)]">{r.organizer_note || "—"}</td>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Mobile Stacked Cards */}
            <div className="sm:hidden divide-y" style={{ borderColor: "var(--border)" }}>
              {overview.registrations.map((r) => {
                const teamStr = r.member_names?.length
                  ? r.member_names.map((n, i) => `${n} (${r.member_ids[i] || ""})`).join(", ")
                  : `${r.leader_name} (${r.leader_id})`;
                return (
                  <div key={r.ref} className="p-3.5 space-y-1 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono-tab font-bold">{r.ref}</span>
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-mono-tab font-bold ${
                          r.status === "approved"
                            ? "bg-teal-500/15 text-teal-700 dark:text-teal-300"
                            : "bg-rose-500/15 text-rose-600 dark:text-rose-400"
                        }`}
                      >
                        {r.status}
                      </span>
                    </div>
                    <div className="font-semibold">{r.event_name}</div>
                    <div className="text-[var(--text-2)]">{teamStr}</div>
                    {r.organizer_note && <div className="text-[var(--muted)]">Note: {r.organizer_note}</div>}
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      </main>

      <AnimatePresence>
        {toastMsg && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            role="status"
            className="fixed right-4 bottom-6 z-50 px-4 py-2.5 rounded-2xl bg-[#0b1e3b] text-white text-xs font-semibold shadow-xl border border-teal-400/30"
          >
            {toastMsg}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
