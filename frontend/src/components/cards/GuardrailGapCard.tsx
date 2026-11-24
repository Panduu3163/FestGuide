import { AlertCircle, Compass, HelpCircle, ShieldAlert } from "lucide-react";
import type { MessageTone } from "../../types";

const CONFIG: Record<
  Exclude<MessageTone, "answer" | "approved" | "rejected" | "paused">,
  { title: string; badge: string; border: string; bg: string; badgeClass: string; Icon: typeof ShieldAlert }
> = {
  blocked: {
    title: "Stopped by Safety & Privacy Guardrail",
    badge: "GUARDRAIL",
    border: "border-rose-500/35",
    bg: "bg-rose-500/[0.07]",
    badgeClass: "bg-rose-500/15 text-rose-600 dark:text-rose-400",
    Icon: ShieldAlert,
  },
  not_found: {
    title: "Not Stated in Official Rulebook",
    badge: "RULEBOOK GAP",
    border: "border-[#c99a2e]/40",
    bg: "bg-[#c99a2e]/[0.08]",
    badgeClass: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
    Icon: HelpCircle,
  },
  out_of_scope: {
    title: "Outside IIUC CSE Fest Scope",
    badge: "OUT OF SCOPE",
    border: "border-indigo-500/35",
    bg: "bg-indigo-500/[0.07]",
    badgeClass: "bg-indigo-500/15 text-indigo-700 dark:text-indigo-300",
    Icon: Compass,
  },
  error: {
    title: "Request Notice",
    badge: "ERROR",
    border: "border-rose-500/35",
    bg: "bg-rose-500/[0.07]",
    badgeClass: "bg-rose-500/15 text-rose-600 dark:text-rose-400",
    Icon: AlertCircle,
  },
};

export function GuardrailGapCard({
  tone,
  text,
}: {
  tone: Exclude<MessageTone, "answer" | "approved" | "rejected" | "paused">;
  text: string;
}) {
  const c = CONFIG[tone];
  const Icon = c.Icon;
  return (
    <div className={`w-full rounded-2xl border p-4 space-y-2 ${c.border} ${c.bg}`}>
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="inline-flex items-center gap-2 text-xs font-bold text-[var(--text)]">
          <Icon className="w-4 h-4 shrink-0" />
          <span>{c.title}</span>
        </div>
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono-tab font-bold ${c.badgeClass}`}>
          {c.badge}
        </span>
      </div>
      <div className="text-sm text-[var(--text)] leading-relaxed whitespace-pre-wrap">{text}</div>
    </div>
  );
}
