import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, BookOpen, X } from "lucide-react";
import type { Citation } from "../../types";

export function CitationPills({
  cites,
  versionNote,
  onSelect,
}: {
  cites: Citation[];
  versionNote?: string;
  onSelect: (c: Citation, idx: number, note?: string) => void;
}) {
  return (
    <div className="w-full space-y-2 pt-1">
      <div className="flex items-center gap-1.5 text-[10px] font-mono-tab uppercase tracking-wider text-[var(--muted)] font-semibold">
        <BookOpen className="w-3.5 h-3.5 text-[#0f9d8a]" />
        {cites.length} Rulebook Source{cites.length > 1 ? "s" : ""} (click to inspect)
      </div>
      <div className="flex flex-wrap gap-2">
        {cites.map((c, n) => {
          const isMock = Boolean(c.version && c.version !== "2026");
          return (
            <button
              key={`${c.event}-${c.section}-${n}`}
              type="button"
              onClick={() => onSelect(c, n + 1, versionNote)}
              className="group bento-soft hover:border-[#0f9d8a] rounded-xl px-3 py-1.5 text-xs flex items-center gap-2 transition cursor-pointer text-left"
            >
              <span className="w-5 h-5 rounded-md bg-[var(--teal-soft)] text-[#0f9d8a] dark:text-teal-300 font-mono-tab font-bold flex items-center justify-center text-[11px]">
                {n + 1}
              </span>
              <span className="font-semibold text-[var(--text)] truncate max-w-[200px]">
                {c.event}
              </span>
              {c.page && (
                <span className="px-1.5 py-0.5 rounded bg-indigo-500/12 text-indigo-700 dark:text-indigo-300 font-mono-tab text-[10px]">
                  p.{c.page}
                </span>
              )}
              <span
                className={`px-1.5 py-0.5 rounded font-mono-tab text-[10px] font-semibold ${
                  isMock
                    ? "bg-amber-500/15 text-amber-700 dark:text-amber-300"
                    : "bg-teal-500/15 text-teal-700 dark:text-teal-300"
                }`}
              >
                {isMock ? "v1-mock" : "2026"}
              </span>
            </button>
          );
        })}
      </div>
      {versionNote && (
        <div className="rounded-xl px-3 py-2 text-xs flex items-center gap-2 bg-[var(--gold-soft)] border border-[#c99a2e]/30 text-amber-800 dark:text-amber-200">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          <span>{versionNote}</span>
        </div>
      )}
    </div>
  );
}

export function CitationDrawer({
  selected,
  onClose,
}: {
  selected: { cite: Citation; index: number; versionNote?: string } | null;
  onClose: () => void;
}) {
  return (
    <AnimatePresence>
      {selected && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-50 bg-black/45 backdrop-blur-xs flex justify-end"
        >
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 360, damping: 34 }}
            onClick={(e) => e.stopPropagation()}
            className="bento-card w-full max-w-md h-full p-6 flex flex-col justify-between rounded-l-3xl shadow-2xl overflow-y-auto"
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: "var(--border)" }}>
                <div>
                  <div className="text-[10px] font-mono-tab uppercase text-[#0f9d8a] font-bold">
                    Rulebook Source [{selected.index}]
                  </div>
                  <h3 className="font-display font-bold text-lg mt-0.5 text-[var(--text)]">
                    {selected.cite.event}
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  aria-label="Close source drawer"
                  className="p-1.5 rounded-lg bento-soft hover:border-[var(--border-strong)] cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="flex flex-wrap gap-2 text-xs font-mono-tab">
                {selected.cite.section && (
                  <span className="px-2.5 py-1 rounded-lg bento-soft font-medium">
                    Section: {selected.cite.section}
                  </span>
                )}
                {selected.cite.page && (
                  <span className="px-2.5 py-1 rounded-lg bg-teal-500/15 text-teal-700 dark:text-teal-300 font-bold">
                    Page {selected.cite.page}
                  </span>
                )}
                <span className="px-2.5 py-1 rounded-lg bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 font-bold">
                  {selected.cite.version || "2026"}
                </span>
              </div>

              <div className="bento-soft rounded-2xl p-4 text-xs leading-relaxed space-y-2">
                <div className="font-mono-tab text-[10px] uppercase text-[var(--muted)] font-bold">
                  Verified Rulebook Metadata
                </div>
                <p className="text-[var(--text-2)]">
                  Retrieved directly from indexed chunks of <strong>{selected.cite.event}</strong>
                  {selected.cite.section ? ` under "${selected.cite.section}"` : ""}
                  {selected.cite.page ? ` (PDF page ${selected.cite.page})` : ""}.
                </p>
              </div>

              {selected.versionNote && (
                <div className="rounded-2xl p-4 bg-[var(--gold-soft)] border border-[#c99a2e]/35 text-xs space-y-1">
                  <div className="font-mono-tab text-[10px] uppercase font-bold text-amber-700 dark:text-amber-300">
                    Version Conflict Note
                  </div>
                  <p className="text-[var(--text)]">{selected.versionNote}</p>
                </div>
              )}
            </div>

            <div className="text-[11px] pt-4 border-t text-[var(--muted)]" style={{ borderColor: "var(--border)" }}>
              Citations are extracted deterministically from chunk metadata — never synthesized by the language model.
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
