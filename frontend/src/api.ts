import type {
  ChatHistoryResponse,
  ChatPostResponse,
  CreateStudentPayload,
  OverviewData,
  PendingItem,
  StudentRecord,
} from "./types";

async function api<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(path, opts);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (body as { detail?: unknown }).detail;
    const msg = Array.isArray(detail)
      ? detail.map((e: { msg?: string }) => e.msg || JSON.stringify(e)).join("; ")
      : typeof detail === "string"
        ? detail
        : res.statusText;
    throw new Error(msg || res.statusText);
  }
  return body as T;
}

export const getConfig = () => api<{ demo: boolean }>("/api/config");
export const getOverview = () => api<OverviewData>("/api/overview");
export const getStudents = () => api<StudentRecord[]>("/api/students");

export const createStudent = (payload: CreateStudentPayload) =>
  api<StudentRecord>("/api/students", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

export const deleteStudent = (studentId: string) =>
  api<{ ok: boolean }>(`/api/students/${encodeURIComponent(studentId)}`, {
    method: "DELETE",
  });

export const getChatHistory = (studentId: string) =>
  api<ChatHistoryResponse>(`/api/chat/${encodeURIComponent(studentId)}`);

export const sendChatMessage = (studentId: string, message: string) =>
  api<ChatPostResponse>("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ student_id: studentId, message }),
  });

export const getOrganizerPending = (pin?: string) =>
  api<PendingItem[]>("/api/organizer/pending", {
    headers: pin ? { "X-Pin": pin } : undefined,
  });

export const postOrganizerDecision = (
  thread_id: string,
  status: "approved" | "rejected",
  note: string,
  pin?: string
) =>
  api<{ reply: string }>("/api/organizer/decide", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(pin ? { "X-Pin": pin } : {}),
    },
    body: JSON.stringify({ thread_id, status, note }),
  });

export const resetDemo = (include_custom_students: boolean) =>
  api<{ ok: boolean }>("/api/demo/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ include_custom_students }),
  });

const RESET_CUSTOM_KEY = "fg_reset_include_custom";
const THEME_KEY = "fg_theme";

export function getResetIncludeCustom(): boolean {
  return localStorage.getItem(RESET_CUSTOM_KEY) === "1";
}

export function setResetIncludeCustom(val: boolean): void {
  localStorage.setItem(RESET_CUSTOM_KEY, val ? "1" : "0");
}

export type ThemeMode = "light" | "dark";

export function resolveInitialTheme(): ThemeMode {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyThemeMode(mode: ThemeMode): void {
  const style = document.createElement("style");
  style.append(document.createTextNode("*,*::before,*::after{transition:none !important}"));
  document.head.append(style);
  document.documentElement.classList.toggle("dark", mode === "dark");
  localStorage.setItem(THEME_KEY, mode);
  void document.body.offsetHeight;
  requestAnimationFrame(() => requestAnimationFrame(() => style.remove()));
}
