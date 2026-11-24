import type { Citation, FestEvent } from "./types";

export function initials(name?: string): string {
  return (name || "?")
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function formatTeamSize(ev: FestEvent): string {
  if (!ev.team_min && !ev.team_max) return "—";
  if (ev.team_min === 1 && ev.team_max === 1) return "Solo (1)";
  if (ev.team_min === ev.team_max) return `Team of ${ev.team_min}`;
  return `${ev.team_min}–${ev.team_max} members`;
}

export function formatFee(ev: FestEvent): string {
  if (!ev.fee_bdt) return "Fee unstated";
  return `${ev.fee_bdt} BDT/${ev.fee_per || "entry"}`;
}

export function formatDepts(ev: FestEvent): string {
  if (ev.eligible_departments === "all") return "All departments";
  if (Array.isArray(ev.eligible_departments)) return ev.eligible_departments.join(", ");
  return "See rulebook";
}

export function formatEventDate(ev: FestEvent): string {
  if (!ev.event_date) return "TBD";
  const m = String(ev.event_date).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return String(ev.event_date);
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${months[Number(m[2]) - 1] || m[2]} ${Number(m[3])}`;
}

export function formatTimeRange(ev: FestEvent): string {
  if (!ev.start || !ev.end) return "Time TBA";
  return `${ev.start}–${ev.end}${ev.schedule_source === "mock" ? " (mock)" : ""}`;
}

export function ago(iso?: string): string {
  if (!iso) return "";
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  return s < 60 ? "just now" : s < 3600 ? `${Math.floor(s / 60)} min ago` : `${Math.floor(s / 3600)} h ago`;
}

export interface TraceStep {
  node: string;
  label: string;
  details: string[];
  stop: boolean;
}

const NODE_LABELS: Record<string, string> = {
  intake: "Checked message (guardrails)",
  rewrite: "Resolved follow-up context",
  classify: "Classified request",
  retrieve: "Searched rulebooks",
  answer: "Drafted cited answer",
  tool_agent: "Ran eligibility & schedule tools",
  explain_result: "Summarized tool results",
  draft_request: "Prepared organizer request",
  approval_gate: "Paused for organizer review",
  register_team: "Saved registration",
  out_of_scope: "Out of scope",
  compose_reply: "Formatted reply",
};

export function parseTrace(lines?: string[]): TraceStep[] {
  const steps: TraceStep[] = [];
  for (const raw of lines || []) {
    const node = raw.match(/^\s*->\s+(\w+)\s*(.*)$/);
    if (node) {
      steps.push({
        node: node[1],
        label: NODE_LABELS[node[1]] || node[1],
        details: [],
        stop: raw.includes("paused"),
      });
    }
    const extra = raw.match(/^\s+\[(tool|request)\]\s*(.*)$/);
    if (extra && steps.length) {
      steps[steps.length - 1].details.push(extra[2]);
    }
    if (node && node[1] === "classify" && node[2].startsWith("{")) {
      try {
        const parsed = JSON.parse(node[2]) as { intent?: string; events?: string[] };
        steps[steps.length - 1].details.push(
          `intent: ${parsed.intent || "?"}` +
            (parsed.events?.length ? ` · events: ${parsed.events.join(", ")}` : "")
        );
      } catch {
        // ignore non-json suffix
      }
    }
  }
  return steps;
}

function toMinutes(hhmm: string | null): number {
  if (!hhmm) return 0;
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

export interface ClashComparisonData {
  events: [FestEvent, FestEvent];
  sameDay: boolean;
  overlap: boolean;
  overlapWindow: string | null;
}

export function detectClashComparison(
  text: string,
  events: FestEvent[],
  cites?: Citation[]
): ClashComparisonData | null {
  const low = text.toLowerCase();
  const isClashTopic =
    low.includes("clash") ||
    low.includes("overlap") ||
    low.includes("conflict") ||
    low.includes("same day");
  if (!isClashTopic || events.length < 2) return null;

  const aliases: Record<string, string[]> = {
    solo_programming: ["solo programming", "programming contest"],
    videography: ["videography"],
    debate: ["debate", "logical legends"],
    tech_olympiad: ["tech olympiad", "olympiad"],
    idea_generation: ["idea generation", "idea gen"],
    three_mt: ["3mt", "three minute thesis", "three-minute thesis"],
    project_showcase: ["project showcase", "showcase"],
    business_case: ["business case"],
    econ_policy_pitch: ["economics & banking", "economics and banking", "policy pitch"],
    literary_eloquence: ["english literary", "eloquence"],
  };

  const matched: FestEvent[] = [];
  const haystack = `${low} ${(cites || []).map((c) => c.event.toLowerCase()).join(" ")}`;
  for (const ev of events) {
    const kws = aliases[ev.key] || [ev.name.toLowerCase()];
    if (kws.some((kw) => haystack.includes(kw))) {
      matched.push(ev);
    }
  }
  if (matched.length !== 2) return null;
  const [a, b] = matched;
  const sameDay = Boolean(a.event_date && a.event_date === b.event_date);
  const s1 = toMinutes(a.start);
  const e1 = toMinutes(a.end);
  const s2 = toMinutes(b.start);
  const e2 = toMinutes(b.end);
  const startMax = Math.max(s1, s2);
  const endMin = Math.min(e1, e2);
  const overlap = sameDay && startMax < endMin;

  const fmt = (mins: number) =>
    `${String(Math.floor(mins / 60)).padStart(2, "0")}:${String(mins % 60).padStart(2, "0")}`;

  return {
    events: [a, b],
    sameDay,
    overlap,
    overlapWindow: overlap ? `${fmt(startMax)}–${fmt(endMin)}` : null,
  };
}
