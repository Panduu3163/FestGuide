import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Calendar, ChevronDown, Sparkles, Ticket } from "lucide-react";
import type { FestEvent, StudentRecord, TeamRegistration } from "../types";
import {
  formatDepts,
  formatEventDate,
  formatFee,
  formatTeamSize,
  formatTimeRange,
  initials,
} from "../utils";
import { BrandEmblem } from "./BrandMark";

export function StudentBentoRail({
  student,
  registrations,
  events,
  onAskPrompt,
}: {
  student?: StudentRecord;
  registrations: TeamRegistration[];
  events: FestEvent[];
  onAskPrompt: (prompt: string) => void;
}) {
  const [openKey, setOpenKey] = useState<string | null>(null);

  const myRegs = student
    ? registrations.filter(
        (r) => r.leader_id === student.id || (r.member_ids || []).includes(student.id)
      )
    : [];

  return (
    <div className="p-4 space-y-4">
      {/* Lanyard Punched Student Credential Pass */}
      <div className="bento-card rounded-3xl p-4 pt-7 relative overflow-hidden">
        {/* Lanyard Notch Cutout */}
        <div
          className="absolute top-2.5 left-1/2 -translate-x-1/2 w-12 h-2 rounded-full border"
          style={{ background: "var(--canvas)", borderColor: "var(--border)" }}
        />
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-1.5">
            <BrandEmblem size={18} />
            <span className="text-[10px] font-mono-tab uppercase tracking-wider text-[#0f9d8a] font-bold">
              Student Pass
            </span>
          </div>
          {student && (
            <span
              className={`px-2 py-0.5 rounded-full text-[10px] font-mono-tab font-semibold ${
                student.custom
                  ? "bg-indigo-500/15 text-indigo-700 dark:text-indigo-300"
                  : "bento-soft text-[var(--muted)]"
              }`}
            >
              {student.custom ? "Live Account" : "Seed Demo"}
            </span>
          )}
        </div>

        {student && (
          <>
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-[#0b1e3b] via-[#0f5e6e] to-[#0f9d8a] text-white font-mono-tab font-bold text-sm flex items-center justify-center shadow-md shrink-0">
                {initials(student.name)}
              </div>
              <div className="min-w-0">
                <div className="font-display font-bold text-base truncate text-[var(--text)]">
                  {student.name}
                </div>
                <div className="text-xs font-mono-tab text-[var(--muted)]">
                  {student.id} · {student.department} · Yr {student.year}
                </div>
              </div>
            </div>

            <div className="mt-3.5 pt-3 border-t border-dashed space-y-2" style={{ borderColor: "var(--border-strong)" }}>
              <div className="flex items-center justify-between text-[10px] font-mono-tab uppercase text-[var(--muted)] font-bold">
                <span className="inline-flex items-center gap-1">
                  <Ticket className="w-3 h-3 text-[#c99a2e]" /> My Teams ({myRegs.length})
                </span>
                <span>{student.level}</span>
              </div>
              {myRegs.length === 0 ? (
                <div className="text-xs text-[var(--muted)]">No team registrations yet.</div>
              ) : (
                <div className="space-y-1.5">
                  {myRegs.map((r) => (
                    <div
                      key={r.ref}
                      className="bento-soft rounded-xl px-2.5 py-1.5 flex items-center justify-between gap-2 text-[11px]"
                    >
                      <span className="truncate font-medium">
                        <span className="font-mono-tab font-bold">{r.ref}</span> · {r.event_name}
                      </span>
                      <span
                        className={`px-1.5 py-0.5 rounded-full text-[10px] font-mono-tab font-bold ${
                          r.status === "approved"
                            ? "bg-teal-500/15 text-teal-700 dark:text-teal-300"
                            : "bg-rose-500/15 text-rose-600 dark:text-rose-400"
                        }`}
                      >
                        {r.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Expandable 7 Fest Events Bento Stack */}
      <div className="bento-card rounded-3xl p-3.5 space-y-2">
        <div className="flex items-center justify-between px-1 pb-1">
          <span className="inline-flex items-center gap-1.5 text-[10px] font-mono-tab uppercase tracking-wider font-bold text-[var(--muted)]">
            <Calendar className="w-3.5 h-3.5 text-[#0f9d8a]" />
            Fest Events ({events.length})
          </span>
          <span className="text-[11px] font-mono-tab text-[#c99a2e] font-semibold">Jun 12–16</span>
        </div>

        <div className="space-y-1.5">
          {events.map((ev) => {
            const isOpen = openKey === ev.key;
            return (
              <div
                key={ev.key}
                className={`bento-soft rounded-2xl transition overflow-hidden ${
                  isOpen ? "border-[#0f9d8a]/60" : "hover:border-[var(--border-strong)]"
                }`}
              >
                <button
                  type="button"
                  onClick={() => setOpenKey(isOpen ? null : ev.key)}
                  aria-expanded={isOpen}
                  className="w-full px-3 py-2.5 text-left flex items-start justify-between gap-2 cursor-pointer"
                >
                  <div className="min-w-0">
                    <div className="text-xs font-bold text-[var(--text)] leading-snug">{ev.name}</div>
                    <div className="text-[11px] text-[var(--muted)] mt-0.5 font-mono-tab">
                      {formatTeamSize(ev)} · {formatFee(ev)}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <span className="text-[10px] font-mono-tab px-1.5 py-0.5 rounded bg-[var(--teal-soft)] text-[#0f9d8a] dark:text-teal-300 font-semibold">
                      {formatEventDate(ev)}
                    </span>
                    <ChevronDown
                      className={`w-3.5 h-3.5 text-[var(--muted)] transition-transform ${
                        isOpen ? "rotate-180" : ""
                      }`}
                    />
                  </div>
                </button>

                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="px-3 pb-3 pt-1 space-y-2 border-t text-[11px]" style={{ borderColor: "var(--border)" }}>
                        <div className="space-y-0.5 text-[var(--text-2)]">
                          <div>Schedule: {formatEventDate(ev)} · {formatTimeRange(ev)}</div>
                          <div>
                            Eligible: {formatDepts(ev)}
                            {ev.eligible_level && ev.eligible_level !== "any" ? ` (${ev.eligible_level})` : ""}
                          </div>
                        </div>
                        <div className="flex gap-1.5 flex-wrap">
                          <button
                            type="button"
                            onClick={() =>
                              onAskPrompt(
                                `What are the eligibility rules, team size, fee, and schedule for ${ev.name}?`
                              )
                            }
                            className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bento-card hover:border-[#0f9d8a] cursor-pointer"
                          >
                            Ask rules
                          </button>
                          <button
                            type="button"
                            onClick={() => onAskPrompt(`Am I eligible for ${ev.name}?`)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-[var(--teal-soft)] text-[#0f9d8a] dark:text-teal-300 cursor-pointer"
                          >
                            <Sparkles className="w-3 h-3" /> Am I eligible?
                          </button>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
