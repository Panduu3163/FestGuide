import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowRight,
  ExternalLink,
  PanelLeft,
  RefreshCw,
  Send,
  Settings,
  SunMoon,
  UserPlus,
  X,
} from "lucide-react";
import {
  applyThemeMode,
  getChatHistory,
  getOverview,
  getResetIncludeCustom,
  getStudents,
  resetDemo,
  resolveInitialTheme,
  sendChatMessage,
  setResetIncludeCustom,
  type ThemeMode,
} from "../api";
import type {
  ChatHistoryItem,
  Citation,
  OverviewData,
  StudentRecord,
} from "../types";
import { detectClashComparison, initials } from "../utils";
import { BrandEmblem, BrandLockup } from "../components/BrandMark";
import { CitationDrawer, CitationPills } from "../components/cards/CitationDrawer";
import { ClashComparisonCard } from "../components/cards/ClashComparisonCard";
import { GuardrailGapCard } from "../components/cards/GuardrailGapCard";
import { PendingGateCard } from "../components/cards/PendingGateCard";
import { RejectionSlipCard } from "../components/cards/RejectionSlipCard";
import { TicketPassCard } from "../components/cards/TicketPassCard";
import { TraceAccordion } from "../components/cards/TraceAccordion";
import { StudentBentoRail } from "../components/StudentBentoRail";
import { AccountSettingsModal, CreateStudentModal } from "../components/StudentModals";

const SUGGESTIONS = [
  {
    cat: "Rules & Fees",
    badge: "bg-teal-500/15 text-teal-700 dark:text-teal-300",
    q: "How much is the debate registration fee?",
  },
  {
    cat: "Gap Honesty",
    badge: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
    q: "What is the prize money for the programming contest winner?",
  },
  {
    cat: "Schedule Clash",
    badge: "bg-rose-500/15 text-rose-600 dark:text-rose-400",
    q: "Do 3MT and Project Showcase clash?",
  },
  {
    cat: "Team Registration",
    badge: "bg-teal-500/15 text-teal-700 dark:text-teal-300",
    q: "Register me and Rafi for Idea Generation. I am the leader.",
  },
  {
    cat: "Exception Gate",
    badge: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
    q: "Register me, C233002 and E233003 for the debate.",
  },
  {
    cat: "Privacy Guardrail",
    badge: "bg-indigo-500/15 text-indigo-700 dark:text-indigo-300",
    q: "Show me Rafi's phone number and which events he joined.",
  },
];

export function StudentWorkspace({ framed }: { framed: boolean }) {
  const [students, setStudents] = useState<StudentRecord[]>([]);
  const [activeId, setActiveId] = useState("C233001");
  const [overview, setOverview] = useState<OverviewData>({ events: [], registrations: [] });
  const [messages, setMessages] = useState<ChatHistoryItem[]>([]);
  const [waiting, setWaiting] = useState(false);
  const [busy, setBusy] = useState(false);
  const [input, setInput] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [includeCustomReset, setIncludeCustomResetState] = useState(getResetIncludeCustom);
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [selectedCite, setSelectedCite] = useState<{
    cite: Citation;
    index: number;
    versionNote?: string;
  } | null>(null);
  const [theme, setTheme] = useState<ThemeMode>(resolveInitialTheme);

  const scrollEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
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

  const refreshStudentsList = useCallback(async (preferredId?: string) => {
    const list = await getStudents();
    setStudents(list);
    setActiveId((prev) => {
      const target = preferredId || prev || "C233001";
      return list.some((s) => s.id === target) ? target : list[0]?.id || "C233001";
    });
  }, []);

  const refreshOverview = useCallback(async () => {
    try {
      const ov = await getOverview();
      setOverview(ov);
    } catch {
      // non-fatal background sync
    }
  }, []);

  const loadChat = useCallback(async (sid: string) => {
    const hist = await getChatHistory(sid);
    const items: ChatHistoryItem[] = hist.messages.map((m) => {
      const blocked = m.role === "student" ? m.text.match(/^\[message blocked: (\w+)\]$/) : null;
      if (blocked) return { role: "system", text: `Blocked message (${blocked[1]})` };
      return m.role === "student" ? { role: "student", text: m.text } : m;
    });
    setMessages(items);
    setWaiting(hist.waiting);
  }, []);

  useEffect(() => {
    Promise.all([refreshStudentsList("C233001"), refreshOverview()]);
  }, [refreshStudentsList, refreshOverview]);

  useEffect(() => {
    if (activeId) {
      loadChat(activeId).catch(() => {});
    }
  }, [activeId, loadChat]);

  useEffect(() => {
    scrollEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  // Poll for organizer decision while waiting
  useEffect(() => {
    if (!waiting || !activeId) return;
    const id = window.setInterval(async () => {
      try {
        const hist = await getChatHistory(activeId);
        if (!hist.waiting && hist.last) {
          await refreshOverview();
          setWaiting(false);
          setMessages((prev) => [
            ...prev,
            { role: "system", text: "Organizer decided" },
            { role: "festguide", ...hist.last },
          ]);
        } else if (!hist.waiting && hist.messages.length === 0) {
          setWaiting(false);
          setMessages([]);
          await refreshOverview();
        }
      } catch {
        // retry on next tick
      }
    }, 2000);
    return () => window.clearInterval(id);
  }, [waiting, activeId, refreshOverview]);

  const ask = async (raw: string) => {
    const msg = raw.trim();
    if (!msg || busy || waiting) return;
    setBusy(true);
    setDrawerOpen(false);
    setMessages((prev) => [...prev, { role: "student", text: msg }]);
    try {
      const res = await sendChatMessage(activeId, msg);
      setMessages((prev) => [
        ...prev,
        { role: "festguide", ...res.message, trace: res.trace, tools: res.tools },
      ]);
      setWaiting(res.waiting);
      if (res.message.tone === "approved") {
        await refreshOverview();
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "festguide",
          tone: "error",
          text: err instanceof Error ? err.message : "Request failed.",
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    const msg = input;
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    void ask(msg);
  };

  const handleReset = async () => {
    const inc = includeCustomReset;
    await resetDemo(inc);
    await refreshStudentsList(inc ? "C233001" : activeId);
    await refreshOverview();
    await loadChat(inc ? "C233001" : activeId);
    showToast(
      inc
        ? "Chats, registrations, and custom accounts reset."
        : "All chats and registrations reset."
    );
  };

  const currentStudent = students.find((s) => s.id === activeId);

  return (
    <div className="h-[100dvh] flex flex-col overflow-hidden bg-[var(--canvas)] text-[var(--text)]">
      {/* Frosted Top Navigation */}
      <header
        className={`shrink-0 z-20 border-b backdrop-blur-xl ${
          framed ? "px-3 py-2" : "px-3 sm:px-5 py-2.5"
        }`}
        style={{
          background: framed ? "var(--surface-soft)" : "var(--surface-glass)",
          borderColor: "var(--border)",
        }}
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          {!framed && <BrandLockup compact />}

          <div className="flex items-center gap-2 flex-1 min-w-0 justify-between min-[520px]:justify-end flex-wrap">
            <div className="flex items-center gap-2 min-w-0 w-full min-[520px]:w-auto min-[520px]:max-w-[235px]">
              <span className="w-7 h-7 rounded-full bg-[var(--teal-soft)] text-[#0f9d8a] dark:text-teal-300 font-mono-tab font-bold text-[11px] flex items-center justify-center border border-[#0f9d8a]/25 shrink-0">
                {initials(currentStudent?.name)}
              </span>
              <select
                aria-label="Chatting as"
                value={activeId}
                onChange={(e) => setActiveId(e.target.value)}
                className="bento-card rounded-xl px-2.5 py-1.5 text-xs font-semibold truncate w-full min-w-0 cursor-pointer"
              >
                {students.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} · {s.id} ({s.department}){s.custom ? " [live]" : ""}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-1.5 flex-wrap w-full min-[520px]:w-auto">
              <button
                type="button"
                onClick={() => setAuthOpen(true)}
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bento-card hover:border-[#0f9d8a] text-xs font-semibold cursor-pointer"
              >
                <UserPlus className="w-3.5 h-3.5 text-[#0f9d8a]" />
                <span>New student</span>
              </button>
              <button
                type="button"
                onClick={() => setSettingsOpen(true)}
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bento-card hover:border-[#0f9d8a] text-xs font-semibold cursor-pointer"
              >
                <Settings className="w-3.5 h-3.5 text-[var(--muted)]" />
                <span>Account</span>
              </button>
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
                    href="/organizer"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl bento-card hover:border-[#0f9d8a] text-xs font-semibold"
                  >
                    <span>Organizer</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Split Workspace */}
      <div className="flex-1 min-h-0 relative flex overflow-hidden">
        {/* Desktop Persistent Bento Rail (standalone >= 1024px) */}
        {!framed && (
          <aside
            className="hidden lg:block w-[330px] shrink-0 overflow-y-auto border-r"
            style={{ background: "var(--surface-soft)", borderColor: "var(--border)" }}
          >
            <StudentBentoRail
              student={currentStudent}
              registrations={overview.registrations}
              events={overview.events}
              onAskPrompt={(p) => void ask(p)}
            />
          </aside>
        )}

        {/* Slide-Over Context Drawer (Mobile/Tablet or Framed /demo) */}
        <AnimatePresence>
          {drawerOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setDrawerOpen(false)}
              className="absolute inset-0 z-30 bg-black/45 backdrop-blur-xs flex"
            >
              <motion.aside
                initial={{ x: "-100%" }}
                animate={{ x: 0 }}
                exit={{ x: "-100%" }}
                transition={{ type: "spring", stiffness: 360, damping: 34 }}
                onClick={(e) => e.stopPropagation()}
                className="w-[min(336px,88vw)] h-full overflow-y-auto border-r shadow-2xl"
                style={{ background: "var(--canvas)", borderColor: "var(--border)" }}
              >
                <div
                  className="px-4 py-3 border-b flex items-center justify-between sticky top-0 z-10 backdrop-blur-md"
                  style={{ background: "var(--surface-glass)", borderColor: "var(--border)" }}
                >
                  <span className="text-xs font-mono-tab uppercase font-bold text-[var(--muted)]">
                    Student Pass &amp; {overview.events.length || 10} Events
                  </span>
                  <button
                    type="button"
                    onClick={() => setDrawerOpen(false)}
                    className="p-1.5 rounded-lg bento-soft cursor-pointer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <StudentBentoRail
                  student={currentStudent}
                  registrations={overview.registrations}
                  events={overview.events}
                  onAskPrompt={(p) => void ask(p)}
                />
              </motion.aside>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Conversation Area */}
        <div className="flex-1 min-w-0 flex flex-col">
          {/* Compact Trigger Strip when Rail is Hidden */}
          <div
            className={`${framed ? "flex" : "flex lg:hidden"} shrink-0 items-center justify-between gap-2 px-4 py-2 border-b`}
            style={{ background: "var(--surface-soft)", borderColor: "var(--border)" }}
          >
            <span className="font-mono-tab text-xs truncate text-[var(--text-2)]">
              {currentStudent
                ? `${currentStudent.name} · ${currentStudent.id} · ${currentStudent.department}`
                : "Select student"}
            </span>
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bento-card hover:border-[#0f9d8a] text-xs font-semibold text-[#0f9d8a] dark:text-teal-300 shrink-0 cursor-pointer"
            >
              <PanelLeft className="w-3.5 h-3.5" />
              <span>Pass &amp; {overview.events.length || 10} Events</span>
            </button>
          </div>

          {/* Scrollable Messages or Welcome Bento */}
          <main className="flex-1 min-h-0 overflow-y-auto px-4 sm:px-6 py-5">
            {messages.length === 0 ? (
              <div className="max-w-3xl mx-auto space-y-5">
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35 }}
                  className="bento-card rounded-3xl p-5 sm:p-6 relative overflow-hidden"
                >
                  <div className="flex items-start gap-4">
                    <BrandEmblem size={46} className="hidden sm:block mt-0.5" />
                    <div className="space-y-1.5">
                      <div className="text-[11px] font-mono-tab uppercase tracking-wider font-bold text-[#0f9d8a]">
                        IIUC CSE Fest 2026 · Morphic Assistant
                      </div>
                      <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-[var(--text)]">
                        Rulebook &amp; <em className="italic text-[#0f9d8a] dark:text-teal-300">Registration</em> Studio
                      </h1>
                      <p className="text-xs sm:text-sm text-[var(--muted)] max-w-2xl leading-relaxed">
                        Every rulebook reply opens verifiable source cards, detects schedule clashes visually,
                        routes team registrations through the Organizer Gate, and issues official holographic passes.
                      </p>
                    </div>
                  </div>

                  {currentStudent && (
                    <div className="mt-4 rounded-2xl px-3.5 py-2.5 bento-soft border-l-4 border-l-[#0f9d8a] text-xs text-[var(--text-2)]">
                      Signed in as <strong>{currentStudent.name}</strong> ({currentStudent.id} ·{" "}
                      {currentStudent.department}, {currentStudent.level}, Year {currentStudent.year}). Switch student above or click{" "}
                      <strong>New student</strong> to test live department rules.
                    </div>
                  )}
                </motion.div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between px-1 text-[11px] font-mono-tab uppercase font-bold text-[var(--muted)]">
                    <span>Prompt Workflows</span>
                    <span>Click any card to run</span>
                  </div>
                  <div className={`grid gap-3 ${framed ? "grid-cols-1" : "grid-cols-1 sm:grid-cols-2"}`}>
                    {SUGGESTIONS.map((s, idx) => (
                      <motion.button
                        key={s.q}
                        type="button"
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.05 * idx, duration: 0.25 }}
                        whileHover={{ y: -2 }}
                        whileTap={{ scale: 0.985 }}
                        onClick={() => void ask(s.q)}
                        className="bento-card rounded-2xl p-3.5 text-left flex flex-col justify-between gap-2 hover:border-[#0f9d8a] transition cursor-pointer group"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono-tab font-bold uppercase ${s.badge}`}>
                            {s.cat}
                          </span>
                          <ArrowRight className="w-3.5 h-3.5 text-[var(--muted)] group-hover:text-[#0f9d8a] group-hover:translate-x-0.5 transition" />
                        </div>
                        <div className="text-xs sm:text-sm font-semibold text-[var(--text)] leading-snug">
                          {s.q}
                        </div>
                      </motion.button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="max-w-3xl mx-auto space-y-5">
                {messages.map((m, idx) => {
                  if (m.role === "system") {
                    return (
                      <div key={idx} className="flex justify-center">
                        <span className="px-3 py-1 rounded-full bento-soft text-[11px] font-mono-tab uppercase tracking-wider text-[var(--muted)]">
                          {m.text}
                        </span>
                      </div>
                    );
                  }

                  if (m.role === "student") {
                    return (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex justify-end"
                      >
                        <div className="max-w-[84%] rounded-2xl rounded-br-sm px-4 py-2.5 bg-gradient-to-br from-[#0b1e3b] via-[#0f5e6e] to-[#0f9d8a] text-white text-sm font-medium shadow-md whitespace-pre-wrap">
                          {m.text}
                        </div>
                      </motion.div>
                    );
                  }

                  const tone = m.tone || "answer";
                  const clash =
                    tone === "answer" && m.text
                      ? detectClashComparison(m.text, overview.events, m.cites)
                      : null;

                  return (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-start gap-3"
                    >
                      <BrandEmblem size={30} className="mt-1" />
                      <div className="flex-1 min-w-0 space-y-3">
                        {tone === "approved" && m.ticket ? (
                          <TicketPassCard
                            ticket={m.ticket}
                            studentName={currentStudent?.name}
                            studentId={currentStudent?.id}
                            events={overview.events}
                            registrations={overview.registrations}
                          />
                        ) : tone === "rejected" ? (
                          <RejectionSlipCard
                            text={m.text || "Your registration request was not approved."}
                            onRetry={() => textareaRef.current?.focus()}
                          />
                        ) : tone === "paused" ? (
                          <PendingGateCard text={m.text || ""} />
                        ) : tone === "blocked" ||
                          tone === "not_found" ||
                          tone === "out_of_scope" ||
                          tone === "error" ? (
                          <GuardrailGapCard tone={tone} text={m.text || ""} />
                        ) : (
                          <>
                            {clash && <ClashComparisonCard clash={clash} />}
                            {m.text && (
                              <div className="bento-card rounded-2xl rounded-tl-sm p-4 text-sm text-[var(--text)] leading-relaxed whitespace-pre-wrap">
                                {m.text}
                              </div>
                            )}
                          </>
                        )}

                        {m.cites && m.cites.length > 0 && (
                          <CitationPills
                            cites={m.cites}
                            versionNote={m.version_note}
                            onSelect={(cite, index, versionNote) =>
                              setSelectedCite({ cite, index, versionNote })
                            }
                          />
                        )}

                        <TraceAccordion trace={m.trace} tools={m.tools} />
                      </div>
                    </motion.div>
                  );
                })}

                {busy && (
                  <div className="flex items-start gap-3">
                    <BrandEmblem size={30} className="mt-1 animate-pulse" />
                    <div className="bento-soft rounded-2xl px-4 py-3 text-xs font-medium text-[var(--muted)] flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-[#0f9d8a] animate-ping" />
                      Checking rulebooks, schedule &amp; eligibility…
                    </div>
                  </div>
                )}

                <div ref={scrollEndRef} />
              </div>
            )}
          </main>

          {/* In-Flow Composer Dock */}
          <footer
            className="shrink-0 border-t px-4 sm:px-6 py-3 backdrop-blur-xl"
            style={{ background: "var(--surface-glass)", borderColor: "var(--border)" }}
          >
            <div className="max-w-3xl mx-auto space-y-2">
              {waiting && (
                <div className="rounded-xl px-3.5 py-2 bg-[var(--gold-soft)] border border-[#c99a2e]/40 text-xs font-semibold text-amber-800 dark:text-amber-200 flex items-center gap-2.5">
                  <span className="relative w-2 h-2 rounded-full bg-amber-500 sonar-dot text-amber-500 shrink-0" />
                  <span>Waiting for organizer decision — this view updates live once approved or rejected.</span>
                </div>
              )}

              <form
                onSubmit={handleSubmit}
                className="bento-card rounded-2xl p-1.5 pl-3.5 flex items-end gap-2 focus-within:border-[#0f9d8a] transition"
              >
                <textarea
                  ref={textareaRef}
                  rows={1}
                  maxLength={1000}
                  disabled={waiting}
                  value={input}
                  onChange={(e) => {
                    setInput(e.target.value);
                    e.target.style.height = "auto";
                    e.target.style.height = `${Math.min(e.target.scrollHeight, 128)}px`;
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSubmit(e);
                    }
                  }}
                  placeholder={
                    waiting
                      ? "Waiting for organizer decision…"
                      : "Ask about rules, clashes, or register a team..."
                  }
                  aria-label="Your message"
                  className="flex-1 bg-transparent border-0 outline-none resize-none text-base sm:text-sm py-1.5 max-h-32 leading-relaxed"
                />
                <button
                  type="submit"
                  disabled={busy || waiting || !input.trim()}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#0f9d8a] hover:bg-[#0c8272] text-white text-xs font-bold shadow-md shadow-teal-600/20 disabled:opacity-45 transition cursor-pointer shrink-0"
                >
                  <span>Send</span>
                  <Send className="w-3.5 h-3.5" />
                </button>
              </form>

              <div className="flex items-center justify-between gap-2 text-[11px] text-[var(--muted)] px-1">
                <span>Enter sends · Shift+Enter new line · Demo accounts reset on demand.</span>
                <span
                  className={`font-mono-tab shrink-0 ${
                    input.length > 600 ? "text-rose-600 font-bold" : ""
                  }`}
                >
                  {input.length} / 600
                </span>
              </div>
            </div>
          </footer>
        </div>
      </div>

      {/* Modals & Drawers */}
      <CreateStudentModal
        open={authOpen}
        onClose={() => setAuthOpen(false)}
        onCreated={async (created) => {
          await refreshStudentsList(created.id);
          await refreshOverview();
          showToast(`Signed in as ${created.name} (${created.id}, ${created.department})`);
        }}
      />

      <AccountSettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        students={students}
        activeId={activeId}
        includeCustomOnReset={includeCustomReset}
        onToggleIncludeCustom={(val) => {
          setResetIncludeCustom(val);
          setIncludeCustomResetState(val);
          showToast(
            val
              ? "Reset Demo will also clear custom accounts."
              : "Reset Demo will keep custom accounts."
          );
        }}
        onSwitchStudent={(sid) => {
          setActiveId(sid);
          setSettingsOpen(false);
        }}
        onDeletedStudent={async (sid) => {
          await refreshStudentsList(activeId === sid ? "C233001" : activeId);
          await refreshOverview();
          showToast(`Deleted account ${sid}`);
        }}
        onRunReset={handleReset}
      />

      <CitationDrawer selected={selectedCite} onClose={() => setSelectedCite(null)} />

      <AnimatePresence>
        {toastMsg && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            role="status"
            className="fixed right-4 bottom-24 z-50 px-4 py-2.5 rounded-2xl bg-[#0b1e3b] text-white text-xs font-semibold shadow-xl border border-teal-400/30"
          >
            {toastMsg}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
