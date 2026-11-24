import type { ClashComparisonData } from "../../utils";
import { formatEventDate, formatTimeRange } from "../../utils";

function timePercent(hhmm: string | null): number {
  if (!hhmm) return 0;
  const [h, m] = hhmm.split(":").map(Number);
  const mins = h * 60 + m;
  // Normalize 08:00 (480) to 18:00 (1080)
  return Math.max(0, Math.min(100, ((mins - 480) / 600) * 100));
}

export function ClashComparisonCard({ clash }: { clash: ClashComparisonData }) {
  const [a, b] = clash.events;
  return (
    <div className="bento-soft rounded-2xl p-4 w-full space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="text-[11px] font-mono-tab uppercase font-bold tracking-wider text-[var(--muted)]">
          Schedule Comparison
        </span>
        {clash.overlap ? (
          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono-tab font-bold bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30">
            CLASH DETECTED · {clash.overlapWindow}
          </span>
        ) : (
          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono-tab font-bold bg-teal-500/15 text-teal-700 dark:text-teal-300 border border-teal-500/30">
            NO TIME CLASH
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
        {[a, b].map((ev, idx) => {
          const left = timePercent(ev.start);
          const right = 100 - timePercent(ev.end);
          return (
            <div key={ev.key} className="bento-card rounded-xl p-3 space-y-2">
              <div className="flex items-start justify-between gap-2">
                <div className="font-bold text-[var(--text)] leading-snug">{ev.name}</div>
                <span className="text-[10px] font-mono-tab text-[var(--muted)] shrink-0">
                  {formatEventDate(ev)}
                </span>
              </div>
              <div className="font-mono-tab text-[11px] text-[var(--muted)]">
                {formatTimeRange(ev)}
              </div>
              <div className="h-2 rounded-full bg-slate-500/15 relative overflow-hidden">
                <div
                  className={`absolute inset-y-0 rounded-full ${
                    clash.overlap ? (idx === 0 ? "bg-rose-500" : "bg-amber-500") : "bg-[#0f9d8a]"
                  }`}
                  style={{ left: `${left}%`, right: `${Math.max(0, right)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
