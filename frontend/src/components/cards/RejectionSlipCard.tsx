import { motion } from "framer-motion";
import { RotateCcw, XCircle } from "lucide-react";

interface Props {
  text: string;
  onRetry?: () => void;
}

export function RejectionSlipCard({ text, onRetry }: Props) {
  const reasonMatch = text.match(/Reason:\s*(.+)$/i);
  const reason = reasonMatch ? reasonMatch[1].trim() : text;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className="relative w-full rounded-3xl border-2 border-dashed border-rose-500/45 bg-gradient-to-br from-rose-500/[0.09] via-rose-500/[0.04] to-transparent p-5 overflow-hidden shadow-md"
    >
      {/* Left Hazard Ribbon */}
      <div className="absolute inset-y-0 left-0 w-1.5 bg-gradient-to-b from-rose-500 to-red-700" />

      {/* Mechanical Tilted Ink Stamp */}
      <div className="stamp-slam absolute right-4 top-4 pointer-events-none select-none">
        <div className="border-[3px] border-rose-600/85 text-rose-600 dark:text-rose-400 dark:border-rose-400/85 px-3 py-1 rounded-lg font-mono-tab font-black tracking-widest text-xs uppercase bg-rose-500/10 shadow-[inset_0_0_6px_rgba(225,29,72,0.18)]">
          REJECTED
        </div>
      </div>

      <div className="pl-2 pr-24 space-y-1.5">
        <div className="inline-flex items-center gap-1.5 text-[10px] font-mono-tab uppercase tracking-wider text-rose-600 dark:text-rose-400 font-bold">
          <XCircle className="w-3.5 h-3.5" />
          Registration Declined · No Team Saved
        </div>
        <h4 className="font-bold text-sm text-[var(--text)]">Organizer Decision Slip</h4>
      </div>

      <div className="ml-2 mt-3.5 p-3 rounded-xl bg-rose-500/10 border border-rose-500/25 text-xs space-y-1">
        <div className="font-mono-tab text-[10px] uppercase text-rose-600 dark:text-rose-400 font-bold">
          Reason Provided
        </div>
        <div className="font-medium text-[var(--text)] leading-relaxed">{reason}</div>
      </div>

      <div className="ml-2 mt-3.5 pt-3 border-t border-rose-500/20 flex items-center justify-between gap-2 text-xs flex-wrap">
        <span className="font-mono-tab text-[11px] text-[var(--muted)]">0 registration rows written</span>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-600 text-white font-semibold hover:bg-rose-700 transition cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Try Another Team
          </button>
        )}
      </div>
    </motion.div>
  );
}
