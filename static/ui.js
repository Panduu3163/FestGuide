// Small helpers shared by the student, organizer and demo pages. No libraries.
// Everything that shows text goes through textContent, so model output can never inject HTML.

const ICONS = {
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
  check: '<polyline points="20 6 9 17 4 12"/>',
  x: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  help: '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  sparkle: '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>',
  chevron: '<polyline points="9 18 15 12 9 6"/>',
  send: '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
  calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
  users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  alert: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>',
  layers: '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
  refresh: '<polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>',
  inbox: '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
  coin: '<circle cx="12" cy="12" r="10"/><path d="M15 9.5a3 3 0 0 0-3-1.5c-1.7 0-3 .9-3 2.2 0 3 6 1.6 6 4.6 0 1.4-1.3 2.2-3 2.2a3.2 3.2 0 0 1-3-1.6"/><line x1="12" y1="6" x2="12" y2="18"/>',
};

function icon(name) {
  const t = document.createElement("template");
  t.innerHTML = `<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ""}</svg>`;
  return t.content.firstChild;
}

function el(tag, cls, content) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (content !== undefined && content !== null) e.textContent = content;
  return e;
}

const initials = (name) => name.split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();

async function api(path, opts) {
  const r = await fetch(path, opts);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.detail || r.statusText);
  return body;
}

const logoMark = () => { const m = el("div", "mark"); m.append(icon("sparkle")); return m; };

// A burst of coloured paper for an approval. Skipped when the visitor asked for reduced motion.
function confetti(host) {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const box = el("div", "confetti");
  const colours = ["#ffd166", "#ffffff", "#9ef0c4", "#b9c4ff", "#ff9eb5"];
  for (let i = 0; i < 26; i++) {
    const p = el("i");
    const angle = (Math.PI * 2 * i) / 26 + Math.random() * 0.4, dist = 70 + Math.random() * 90;
    p.style.cssText = `--i:${i};--x:${Math.cos(angle) * dist}px;--y:${Math.sin(angle) * dist - 20}px;--r:${Math.random() * 540 - 270}deg;background:${colours[i % 5]}`;
    box.append(p);
  }
  host.append(box);
  setTimeout(() => box.remove(), 1800);
}

// ---- the graph trace, drawn as a timeline ------------------------------------------------------
const NODE = {
  intake: "Checked the message (guardrails)", rewrite: "Checked if it was a follow-up", classify: "Understood the request",
  retrieve: "Searched the rulebooks", answer: "Wrote an answer from the sources", tool_agent: "Used tools on mock fest data",
  explain_result: "Explained the tool results", draft_request: "Drafted the registration request",
  approval_gate: "Paused for an organizer", register_team: "Saved the registration", out_of_scope: "Out of scope",
  compose_reply: "Built the reply",
};

function parseTrace(lines) {
  const steps = [];
  for (const raw of lines || []) {
    const node = raw.match(/^\s*->\s+(\w+)\s*(.*)$/);
    if (node) { steps.push({ node: node[1], label: NODE[node[1]] || node[1], details: [], stop: raw.includes("paused") }); }
    const extra = raw.match(/^\s+\[(tool|request)\]\s*(.*)$/);
    if (extra && steps.length) steps[steps.length - 1].details.push(extra[2]);
    if (node && node[1] === "classify" && node[2].startsWith("{")) {
      try {
        const i = JSON.parse(node[2]);
        steps[steps.length - 1].details.push(`intent: ${i.intent}` + (i.events?.length ? ` · events: ${i.events.join(", ")}` : ""));
      } catch (_) { /* a trace line that is not JSON is just skipped */ }
    }
  }
  return steps;
}

function timeline(trace) {
  const steps = parseTrace(trace);
  if (!steps.length) return null;
  const d = el("details", "how");
  const s = el("summary");
  s.append(icon("chevron"), icon("layers"), document.createTextNode(` How FestGuide got this · ${steps.length} steps`));
  const tl = el("div", "tl");
  steps.forEach((st, n) => {
    const row = el("div", "st" + (st.stop ? " stop" : ""));
    row.style.setProperty("--n", n);
    const b = el("b", "", st.label);
    row.append(b, document.createTextNode("  "), el("code", "", st.node));
    if (st.details.length) {
      const det = el("div", "det");
      st.details.forEach((x) => det.append(el("code", "", x.length > 150 ? x.slice(0, 150) + "…" : x)));
      row.append(det);
    }
    tl.append(row);
  });
  d.append(s, tl);
  return d;
}
