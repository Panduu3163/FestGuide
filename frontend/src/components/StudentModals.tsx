import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { RefreshCw, Trash2, UserPlus, X } from "lucide-react";
import { createStudent, deleteStudent } from "../api";
import type { StudentRecord } from "../types";

export function CreateStudentModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (created: StudentRecord) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [id, setId] = useState("");
  const [department, setDepartment] = useState("CSE");
  const [level, setLevel] = useState("undergraduate");
  const [year, setYear] = useState(4);
  const [gender, setGender] = useState("male");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      const created = await createStudent({
        id: id.trim(),
        name: name.trim(),
        department,
        level,
        year,
        gender,
      });
      await onCreated(created);
      setName("");
      setId("");
      onClose();
    } catch (error) {
      setErr(error instanceof Error ? error.message : "Could not create account.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            transition={{ duration: 0.2 }}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="authModalTitle"
            className="bento-card w-full max-w-lg rounded-3xl overflow-hidden shadow-2xl"
          >
            <div className="px-5 py-4 border-b flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
              <div className="flex items-center gap-2">
                <UserPlus className="w-4 h-4 text-[#0f9d8a]" />
                <h2 id="authModalTitle" className="font-display font-bold text-lg">
                  Create Live Student Account
                </h2>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="p-1.5 rounded-lg bento-soft hover:border-[var(--border-strong)] cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-5 space-y-4">
              <p className="text-xs text-[var(--muted)]">
                Create a live student profile in SQLite and sign straight into their FestGuide workspace.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                <label className="space-y-1">
                  <span className="text-xs font-semibold text-[var(--text-2)] block">Full name</span>
                  <input
                    required
                    maxLength={80}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Mynul Kabir Nayem"
                    className="w-full rounded-xl px-3 py-2 bento-soft text-base sm:text-sm outline-none focus:border-[#0f9d8a]"
                  />
                </label>

                <label className="space-y-1">
                  <span className="text-xs font-semibold text-[var(--text-2)] block">Student ID</span>
                  <input
                    required
                    maxLength={16}
                    value={id}
                    onChange={(e) => setId(e.target.value)}
                    placeholder="e.g. C223163 or B243901"
                    className="w-full rounded-xl px-3 py-2 bento-soft font-mono-tab text-base sm:text-sm outline-none focus:border-[#0f9d8a]"
                  />
                </label>

                <label className="space-y-1">
                  <span className="text-xs font-semibold text-[var(--text-2)] block">Department</span>
                  <select
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    className="w-full rounded-xl px-3 py-2 bento-soft text-base sm:text-sm"
                  >
                    {["CSE", "EEE", "ETE", "CE", "CCE", "Pharmacy", "BBA", "ELL", "EB"].map((d) => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                </label>

                <label className="space-y-1">
                  <span className="text-xs font-semibold text-[var(--text-2)] block">Level</span>
                  <select
                    value={level}
                    onChange={(e) => setLevel(e.target.value)}
                    className="w-full rounded-xl px-3 py-2 bento-soft text-base sm:text-sm"
                  >
                    <option value="undergraduate">Undergraduate</option>
                    <option value="postgraduate">Postgraduate</option>
                  </select>
                </label>

                <label className="space-y-1">
                  <span className="text-xs font-semibold text-[var(--text-2)] block">Year</span>
                  <select
                    value={year}
                    onChange={(e) => setYear(Number(e.target.value))}
                    className="w-full rounded-xl px-3 py-2 bento-soft text-base sm:text-sm"
                  >
                    {[1, 2, 3, 4, 5].map((y) => (
                      <option key={y} value={y}>Year {y}</option>
                    ))}
                  </select>
                </label>

                <label className="space-y-1">
                  <span className="text-xs font-semibold text-[var(--text-2)] block">Gender</span>
                  <select
                    value={gender}
                    onChange={(e) => setGender(e.target.value)}
                    className="w-full rounded-xl px-3 py-2 bento-soft text-base sm:text-sm"
                  >
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                  </select>
                </label>
              </div>

              {err && <div className="text-xs font-semibold text-rose-600 dark:text-rose-400">{err}</div>}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bento-soft cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={busy}
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-[#0f9d8a] hover:bg-[#0c8272] text-white shadow-md shadow-teal-600/20 disabled:opacity-50 cursor-pointer"
                >
                  {busy ? "Creating..." : "Create & Sign In"}
                </button>
              </div>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function AccountSettingsModal({
  open,
  onClose,
  students,
  activeId,
  includeCustomOnReset,
  onToggleIncludeCustom,
  onSwitchStudent,
  onDeletedStudent,
  onRunReset,
}: {
  open: boolean;
  onClose: () => void;
  students: StudentRecord[];
  activeId: string;
  includeCustomOnReset: boolean;
  onToggleIncludeCustom: (val: boolean) => void;
  onSwitchStudent: (id: string) => void;
  onDeletedStudent: (id: string) => Promise<void>;
  onRunReset: () => Promise<void>;
}) {
  const current = students.find((s) => s.id === activeId);
  const customs = students.filter((s) => s.custom);

  const handleDelete = async (sid: string) => {
    await deleteStudent(sid);
    await onDeletedStudent(sid);
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            transition={{ duration: 0.2 }}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="settingsModalTitle"
            className="bento-card w-full max-w-lg rounded-3xl overflow-hidden shadow-2xl max-h-[90dvh] flex flex-col"
          >
            <div className="px-5 py-4 border-b flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
              <h2 id="settingsModalTitle" className="font-display font-bold text-lg">
                Account Settings &amp; Reset
              </h2>
              <button
                type="button"
                onClick={onClose}
                className="p-1.5 rounded-lg bento-soft cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 space-y-4 overflow-y-auto">
              {current && (
                <div className="bento-soft rounded-2xl p-4 flex items-center justify-between gap-3">
                  <div>
                    <div className="font-bold text-sm">{current.name} ({current.id})</div>
                    <div className="text-xs text-[var(--muted)] mt-0.5">
                      {current.department} · Year {current.year} · {current.level} ·{" "}
                      {current.custom ? "Live account" : "Seed demo account"}
                    </div>
                  </div>
                  {current.custom && (
                    <button
                      type="button"
                      onClick={() => handleDelete(current.id)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30 text-xs font-semibold cursor-pointer"
                    >
                      <Trash2 className="w-3.5 h-3.5" /> Delete
                    </button>
                  )}
                </div>
              )}

              <div className="bento-soft rounded-2xl p-4 space-y-3">
                <div>
                  <div className="font-bold text-sm">Reset Demo Behavior</div>
                  <p className="text-xs text-[var(--muted)] mt-0.5">
                    By default, Reset Demo deletes only chats &amp; team registrations while preserving live-created accounts.
                  </p>
                </div>
                <label className="flex items-center justify-between gap-3 text-xs font-medium cursor-pointer">
                  <span>Also delete custom student accounts on Reset</span>
                  <input
                    type="checkbox"
                    checked={includeCustomOnReset}
                    onChange={(e) => onToggleIncludeCustom(e.target.checked)}
                    className="w-4 h-4 accent-[#0f9d8a]"
                  />
                </label>
                <button
                  type="button"
                  onClick={onRunReset}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bento-card text-xs font-semibold hover:border-[#0f9d8a] cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Run Reset Now
                </button>
              </div>

              <div className="bento-soft rounded-2xl p-4 space-y-2.5">
                <div className="font-bold text-sm">Live-Created Accounts ({customs.length})</div>
                {customs.length === 0 ? (
                  <p className="text-xs text-[var(--muted)]">No live-created student accounts yet.</p>
                ) : (
                  <div className="space-y-2">
                    {customs.map((s) => (
                      <div
                        key={s.id}
                        className="bento-card rounded-xl px-3 py-2 flex items-center justify-between gap-2"
                      >
                        <div className="min-w-0">
                          <div className="text-xs font-bold truncate">{s.name}</div>
                          <div className="text-[11px] font-mono-tab text-[var(--muted)]">
                            {s.id} · {s.department} · {s.level}
                          </div>
                        </div>
                        <div className="flex gap-1.5 shrink-0">
                          <button
                            type="button"
                            disabled={s.id === activeId}
                            onClick={() => onSwitchStudent(s.id)}
                            className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bento-soft disabled:opacity-45 cursor-pointer"
                          >
                            {s.id === activeId ? "Active" : "Switch"}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDelete(s.id)}
                            className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-rose-500/15 text-rose-600 dark:text-rose-400 cursor-pointer"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
