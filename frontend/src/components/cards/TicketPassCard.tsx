import { useState } from "react";
import { motion } from "framer-motion";
import { Check, Copy, Ticket } from "lucide-react";
import type { FestEvent, TeamRegistration, TicketInfo } from "../../types";
import { formatEventDate, formatTimeRange } from "../../utils";
import { BrandEmblem } from "../BrandMark";

interface Props {
  ticket: TicketInfo;
  studentName?: string;
  studentId?: string;
  events: FestEvent[];
  registrations: TeamRegistration[];
}

export function TicketPassCard({ ticket, studentName, studentId, events, registrations }: Props) {
  const [copied, setCopied] = useState(false);
  const refCode = ticket.ref || "REG-????";

  const regMatch = registrations.find((r) => r.ref === refCode);
  const evMatch = events.find(
    (e) => e.name.toLowerCase() === (ticket.event || "").toLowerCase() || e.key === regMatch?.event
  );

  const memberCount = regMatch?.member_ids?.length || 1;
  const dateLabel = evMatch ? formatEventDate(evMatch) : "Jun 2026";
  const timeLabel = evMatch ? formatTimeRange(evMatch) : "Scheduled";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(refCode);
    } catch {
      // clipboard fallback ignored
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.34, ease: [0.22, 1, 0.36, 1] }}
      className="ticket-foil text-white rounded-3xl shadow-xl border border-teal-300/25 flex flex-col sm:flex-row relative w-full"
    >
      {/* Semi-circle Ticket Notches */}
      <div
        className="hidden sm:block absolute -top-3 left-[67%] -translate-x-1/2 w-6 h-6 rounded-full z-20"
        style={{ background: "var(--notch-bg)" }}
      />
      <div
        className="hidden sm:block absolute -bottom-3 left-[67%] -translate-x-1/2 w-6 h-6 rounded-full z-20"
        style={{ background: "var(--notch-bg)" }}
      />

      {/* Left Main Pass */}
      <div className="flex-1 p-5 flex flex-col justify-between gap-3.5 relative z-10 min-w-0">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2">
            <BrandEmblem size={22} />
            <span className="text-[10px] font-mono-tab uppercase tracking-widest text-teal-200 font-semibold">
              IIUC CSE Fest 2026 · Official Pass
            </span>
          </div>
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono-tab font-bold bg-[#c99a2e]/25 border border-[#e5c158]/40 text-amber-200">
            <Ticket className="w-3 h-3" /> CONFIRMED
          </span>
        </div>

        <div>
          <div className="text-[10px] font-mono-tab text-teal-200/75 uppercase">Competition Entry</div>
          <h3 className="font-display text-lg sm:text-xl font-bold tracking-tight text-white mt-0.5">
            {ticket.event || regMatch?.event_name || "Fest Event"}
          </h3>
          <p className="text-xs text-teal-100/85 mt-1">
            {ticket.note ? `Organizer note: “${ticket.note}”` : "Mock / demo registration record."}
          </p>
        </div>

        <div className="grid grid-cols-3 gap-2.5 pt-3 border-t border-white/15 text-xs">
          <div className="min-w-0">
            <div className="text-[10px] font-mono-tab text-teal-200/70">LEADER</div>
            <div className="font-semibold truncate">{regMatch?.leader_name || studentName || studentId || "Leader"}</div>
          </div>
          <div>
            <div className="text-[10px] font-mono-tab text-teal-200/70">ROSTER</div>
            <div className="font-semibold">
              {memberCount} {memberCount === 1 ? "Member" : "Members"}
            </div>
          </div>
          <div>
            <div className="text-[10px] font-mono-tab text-teal-200/70">SCHEDULE</div>
            <div className="font-semibold truncate">{dateLabel}</div>
          </div>
        </div>
      </div>

      {/* Perforated Seam */}
      <div className="hidden sm:flex items-center justify-center relative z-10">
        <div className="w-[2px] h-[82%] perforation-v" />
      </div>
      <div className="sm:hidden w-full h-[2px] perforation-h relative z-10" />

      {/* Right Tear-off Stub */}
      <div className="sm:w-48 p-5 bg-black/25 flex flex-col justify-between gap-3 relative z-10 sm:rounded-r-3xl">
        <div>
          <div className="text-[10px] font-mono-tab text-teal-200/75 uppercase">Ticket Ref</div>
          <div className="font-mono-tab text-xl font-black tracking-tight text-[#e5c158] mt-0.5">
            {refCode}
          </div>
          <div className="text-[10px] text-teal-100/75 mt-0.5">{timeLabel}</div>
          <button
            type="button"
            onClick={handleCopy}
            className="mt-2.5 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/15 hover:bg-white/25 border border-white/20 text-[11px] font-mono-tab font-semibold text-white transition cursor-pointer"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-300" /> : <Copy className="w-3 h-3" />}
            {copied ? "Copied" : "Copy Ref"}
          </button>
        </div>

        <div className="pt-2 border-t border-white/15">
          <svg
            className="w-full h-7 text-white/85"
            viewBox="0 0 100 24"
            preserveAspectRatio="none"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M0,0 h2 v24 h-2 z M4,0 h1 v24 h-1 z M7,0 h3 v24 h-3 z M12,0 h1 v24 h-1 z M15,0 h2 v24 h-2 z M19,0 h4 v24 h-4 z M25,0 h1 v24 h-1 z M28,0 h3 v24 h-3 z M33,0 h2 v24 h-2 z M37,0 h1 v24 h-1 z M40,0 h3 v24 h-3 z M45,0 h2 v24 h-2 z M49,0 h1 v24 h-1 z M52,0 h4 v24 h-4 z M58,0 h1 v24 h-1 z M61,0 h2 v24 h-2 z M65,0 h3 v24 h-3 z M70,0 h1 v24 h-1 z M73,0 h2 v24 h-2 z M77,0 h3 v24 h-3 z M82,0 h1 v24 h-1 z M85,0 h2 v24 h-2 z M89,0 h4 v24 h-4 z M95,0 h1 v24 h-1 z M98,0 h2 v24 h-2 z" />
          </svg>
          <div className="text-[9px] font-mono-tab text-teal-200/70 tracking-widest mt-1 text-center">
            DEMO · VERIFIED PASS
          </div>
        </div>
      </div>
    </motion.div>
  );
}
