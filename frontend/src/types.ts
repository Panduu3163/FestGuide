export interface StudentRecord {
  id: string;
  name: string;
  department: string;
  level: string;
  year: number;
  custom: boolean;
}

export interface CreateStudentPayload {
  id: string;
  name: string;
  department: string;
  year: number;
  level: string;
  gender: string;
}

export interface FestEvent {
  key: string;
  name: string;
  team_min: number | null;
  team_max: number | null;
  fee_bdt: number | null;
  fee_per: string | null;
  event_date: string | null;
  reg_deadline: string | null;
  eligible_departments: string | string[] | null;
  eligible_level: string | null;
  start: string | null;
  end: string | null;
  schedule_source: string | null;
}

export interface TeamRegistration {
  ref: string;
  event: string;
  event_name: string;
  leader_id: string;
  leader_name: string;
  member_ids: string[];
  member_names: string[];
  status: "approved" | "rejected" | string;
  organizer_note: string | null;
  created_at: string;
}

export interface OverviewData {
  events: FestEvent[];
  registrations: TeamRegistration[];
}

export interface Citation {
  event: string;
  section: string;
  page: number | null;
  version: string;
}

export interface TicketInfo {
  ref: string | null;
  event: string | null;
  note: string | null;
}

export type MessageTone =
  | "answer"
  | "approved"
  | "rejected"
  | "paused"
  | "blocked"
  | "not_found"
  | "out_of_scope"
  | "error";

export interface ShapedMessage {
  text: string;
  cites: Citation[];
  version_note: string;
  tone: MessageTone;
  ticket?: TicketInfo;
}

export interface ChatHistoryItem {
  role: "student" | "festguide" | "system";
  text?: string;
  cites?: Citation[];
  version_note?: string;
  tone?: MessageTone;
  ticket?: TicketInfo;
  trace?: string[];
  tools?: string[];
  event_hint?: string;
}

export interface ChatHistoryResponse {
  messages: Array<{
    role: "student" | "festguide";
    text: string;
    cites?: Citation[];
    version_note?: string;
    tone?: MessageTone;
    ticket?: TicketInfo;
  }>;
  waiting: boolean;
  last: ShapedMessage | null;
  last_reply: string;
}

export interface ChatPostResponse {
  reply: string;
  message: ShapedMessage;
  trace: string[];
  tools: string[];
  waiting: boolean;
}

export interface PendingCheck {
  student: string;
  eligible: boolean | null;
  problems: string[];
  unclear: string[];
}

export interface PendingRuleQuote {
  source: string;
  text: string;
}

export interface PendingRequestPayload {
  kind: "standard" | "exception" | string;
  event: string;
  event_name: string;
  leader_id: string;
  member_ids: string[];
  fee_note: string;
  checks: PendingCheck[];
  team_problems?: string[];
  cited_rules: PendingRuleQuote[];
  student_message: string;
}

export interface PendingItem {
  thread_id: string;
  asked_at: string;
  leader_name: string;
  member_names: string[];
  request: PendingRequestPayload;
}

export interface SessionDecision {
  event: string;
  who: string;
  status: "approved" | "rejected";
  note: string;
}
