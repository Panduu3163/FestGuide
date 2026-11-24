import { motion } from "framer-motion";
import { Clock } from "lucide-react";

export function PendingGateCard({ text }: { text: string }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
      className="w-full rounded-2xl border border-[#c99a2e]/45 bg-[#c99a2e]/[0.09] p-4 space-y-3"
    >
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="inline-flex items-center gap-2">
          <span className="relative w-2.5 h-2.5 rounded-full bg-amber-500 sonar-dot text-amber-500" />
          <span className="text-xs font-mono-tab font-bold uppercase tracking-wider text-amber-700 dark:text-amber-300">
            Paused at Organizer Approval Gate
          </span>
        </div>
        <span className="inline-flex items-center gap-1 text-[11px] font-mono-tab text-amber-700 dark:text-amber-300">
          <Clock className="w-3 h-3" /> Awaiting Decision
        </span>
      </div>

      <div className="text-sm text-[var(--text)] leading-relaxed whitespace-pre-wrap">{text}</div>

      <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-mono-tab pt-2 border-t border-[#c99a2e]/25">
        <span className="px-2 py-0.5 rounded bg-teal-500/15 text-teal-700 dark:text-teal-300">intake ✓</span>
        <span className="text-[var(--muted)]">→</span>
        <span className="px-2 py-0.5 rounded bg-teal-500/15 text-teal-700 dark:text-teal-300">draft_request ✓</span>
        <span className="text-[var(--muted)]">→</span>
        <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-700 dark:text-amber-300 font-bold">
          approval_gate ⏳
        </span>
      </div>
    </motion.div>
  );
}
