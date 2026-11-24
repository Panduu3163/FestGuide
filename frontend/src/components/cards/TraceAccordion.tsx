import { useState } from "react";
import { ChevronRight, Layers } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { parseTrace } from "../../utils";

export function TraceAccordion({ trace, tools }: { trace?: string[]; tools?: string[] }) {
  const [open, setOpen] = useState(false);
  const steps = parseTrace(trace);
  const uniqueTools = [...new Set(tools || [])];

  if (!steps.length && !uniqueTools.length) return null;

  return (
    <div className="w-full space-y-1.5 pt-1">
      {uniqueTools.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-[var(--muted)]">
          <Layers className="w-3 h-3" />
          <span>Tools:</span>
          {uniqueTools.map((t) => (
            <code
              key={t}
              className="px-1.5 py-0.5 rounded bento-soft font-mono-tab text-[10px] font-semibold text-[var(--text-2)]"
            >
              {t}
            </code>
          ))}
        </div>
      )}

      {steps.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--muted)] hover:text-[var(--text)] transition cursor-pointer"
          >
            <ChevronRight
              className={`w-3.5 h-3.5 transition-transform duration-150 ${open ? "rotate-90" : ""}`}
            />
            <span>Trace · {steps.length} steps</span>
          </button>

          <AnimatePresence initial={false}>
            {open && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden"
              >
                <div
                  className="mt-2 ml-1.5 pl-3 border-l-2 space-y-2 text-xs"
                  style={{ borderColor: "var(--border-strong)" }}
                >
                  {steps.map((st, idx) => (
                    <div key={`${st.node}-${idx}`} className="relative">
                      <span
                        className={`absolute -left-[17px] top-1.5 w-2 h-2 rounded-full ${
                          st.stop ? "bg-amber-500" : "bg-[#0f9d8a]"
                        }`}
                      />
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <strong className="font-semibold text-[var(--text)]">{st.label}</strong>
                        <code className="px-1.5 py-0.5 rounded bento-soft font-mono-tab text-[10px]">
                          {st.node}
                        </code>
                      </div>
                      {st.details.length > 0 && (
                        <div className="mt-1 space-y-1">
                          {st.details.map((d, di) => (
                            <div
                              key={di}
                              className="text-[11px] font-mono-tab text-[var(--muted)] break-all"
                            >
                              {d.length > 150 ? `${d.slice(0, 150)}…` : d}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
