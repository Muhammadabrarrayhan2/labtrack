// LabTrack web front end. Plain JavaScript, no build step. Every call goes to the same
// REST API the Swagger UI uses, with the JWT kept in sessionStorage for this tab only.
"use strict";

const state = { token: null, me: null, courses: [], courseId: null, view: "rekap" };
const $ = (sel) => document.querySelector(sel);

// ---------- small DOM helper: text is always set with textContent (no HTML injection)
function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "text") el.textContent = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

// ---------- API access
class ApiError extends Error {
  constructor(status, message, requestId) { super(message); this.status = status; this.requestId = requestId; }
}

function describe(detail) {
  if (Array.isArray(detail)) {
    return detail.map((d) => `${(d.loc || []).slice(-1)[0] || "data"}: ${d.msg}`).join("; ");
  }
  return detail || "Terjadi galat";
}

async function api(path, { method = "GET", json, form, body } = {}) {
  const headers = {};
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  let payload = body;
  if (json !== undefined) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(json); }
  if (form) { headers["Content-Type"] = "application/x-www-form-urlencoded"; payload = new URLSearchParams(form); }
  const res = await fetch(path, { method, headers, body: payload });
  const requestId = res.headers.get("X-Request-ID");
  if (res.status === 204) return null;
  let data = null;
  try { data = await res.json(); } catch { /* non-JSON error page */ }
  if (!res.ok) {
    if (res.status === 401 && state.token) logout("Sesi berakhir. Silakan masuk kembali.");
    throw new ApiError(res.status, data ? describe(data.detail) : `HTTP ${res.status}`, (data && data.request_id) || requestId);
  }
  return data;
}

// ---------- messages
function flash(message, ok = false, requestId = null) {
  const box = $("#flash");
  box.replaceChildren(h("span", { text: message }));
  if (requestId) box.append(h("span", {}, "Kode laporan: ", h("code", { class: "rid", text: requestId })));
  box.className = ok ? "alert ok" : "alert";
  box.hidden = false;
  if (ok) setTimeout(() => { box.hidden = true; }, 4000);
}
function fail(err) {
  if (err instanceof ApiError) flash(`${err.message} (HTTP ${err.status})`, false, err.requestId);
  else flash("Tidak dapat terhubung ke server. Periksa koneksi lalu coba lagi.");
}
async function busy(button, fn) {
  button.disabled = true;
  try { return await fn(); } catch (e) { fail(e); } finally { button.disabled = false; }
}

// ---------- session
async function login(email, password) {
  const tok = await api("/auth/login", { method: "POST", form: { username: email, password } });
  state.token = tok.access_token;
  sessionStorage.setItem("labtrack_token", state.token);
}
function logout(message) {
  state.token = null; state.me = null;
  sessionStorage.removeItem("labtrack_token");
  $("#app-view").hidden = true; $("#login-view").hidden = false;
  const err = $("#login-error");
  if (message) { err.textContent = message; err.hidden = false; } else err.hidden = true;
}

async function boot() {
  state.me = await api("/auth/me");
  $("#me-name").textContent = state.me.full_name;
  $("#me-role").textContent = state.me.role === "admin" ? "Koordinator" : "Asisten";
  document.querySelectorAll("[data-admin]").forEach((el) => { el.hidden = state.me.role !== "admin"; });
  await loadCourses();
  $("#login-view").hidden = true; $("#app-view").hidden = false;
  fetch("/health").then((r) => r.json()).then((d) => { $("#version").textContent = `v${d.version}`; }).catch(() => {});
  render();
}

async function loadCourses() {
  state.courses = await api("/courses");
  const sel = $("#course-select");
  sel.replaceChildren(...state.courses.map((c) => h("option", { value: c.id, text: `${c.code} · ${c.name} (${c.semester})` })));
  if (!state.courses.length) sel.append(h("option", { value: "", text: "Belum ada mata kuliah" }));
  const saved = Number(sessionStorage.getItem("labtrack_course"));
  state.courseId = state.courses.some((c) => c.id === saved) ? saved : (state.courses[0] || {}).id || null;
  if (state.courseId) sel.value = state.courseId;
}

// ---------- views
const views = { rekap: viewRekap, kehadiran: viewKehadiran, mahasiswa: viewMahasiswa, laporan: viewLaporan, admin: viewAdmin };

async function render() {
  $("#flash").hidden = true;
  document.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", b.dataset.view === state.view));
  const root = $("#view");
  root.replaceChildren(h("p", { class: "muted", text: "Memuat..." }));
  try { root.replaceChildren(...(await views[state.view]())); } catch (e) { root.replaceChildren(); fail(e); }
}
function needCourse() {
  return [h("div", { class: "card" }, h("p", { class: "empty", text: "Belum ada mata kuliah. Koordinator dapat membuatnya di menu Kelola." }))];
}
const sessionLabel = (s) => `Modul ${s.session_no}: ${s.title} (${new Date(s.scheduled_at).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" })})`;

async function viewRekap() {
  if (!state.courseId) return needCourse();
  const threshold = Number(sessionStorage.getItem("labtrack_threshold") || 75);
  const s = await api(`/courses/${state.courseId}/attendance-summary?threshold=${threshold}`);
  const risk = s.students.filter((r) => r.at_risk);
  const thInput = h("input", { type: "number", min: 0, max: 100, value: threshold, id: "threshold", "aria-label": "Ambang kehadiran" });
  const apply = h("button", { text: "Terapkan", onclick: () => { sessionStorage.setItem("labtrack_threshold", thInput.value); render(); } });
  const rows = s.students.map((r) => h("tr", { class: r.at_risk ? "risk" : null },
    h("td", { text: r.nim }), h("td", { text: r.full_name }),
    h("td", { class: "num", text: r.present }), h("td", { class: "num", text: r.late }),
    h("td", { class: "num", text: r.excused }), h("td", { class: "num", text: r.absent }),
    h("td", { class: "num" }, h("div", { class: `bar ${r.at_risk ? "low" : ""}`, title: `${r.attendance_rate}%` }, h("i", { style: `width:${r.attendance_rate}%` })), `${r.attendance_rate}%`),
    h("td", {}, h("span", { class: `chip ${r.at_risk ? "bad" : "ok"}`, text: r.at_risk ? "Berisiko" : "Aman" }))));
  return [
    h("div", { class: "stats" },
      h("div", { class: "stat" }, h("b", { text: s.sessions_held }), h("span", { text: "sesi sudah berlangsung" })),
      h("div", { class: "stat" }, h("b", { text: s.students.length }), h("span", { text: "mahasiswa terdaftar" })),
      h("div", { class: "stat" }, h("b", { text: risk.length }), h("span", { text: `di bawah ambang ${s.threshold}%` }))),
    h("div", { class: "card" },
      h("div", { class: "row" }, h("h2", { text: "Rekap kehadiran", style: "flex:1" }),
        h("div", { class: "field narrow" }, h("label", { for: "threshold", text: "Ambang (%)" }), thInput), apply),
      h("p", { class: "muted", text: "Persentase = (hadir + terlambat) / sesi yang sudah berlangsung. Mahasiswa tanpa catatan pada sesi yang berlangsung dihitung tidak hadir." }),
      rows.length ? h("div", { class: "table-wrap" }, h("table", {},
        h("thead", {}, h("tr", {}, ...["NIM", "Nama", "Hadir", "Terlambat", "Izin", "Alpa", "Kehadiran", "Status"].map((t, i) => h("th", { class: i >= 2 && i <= 6 ? "num" : null, text: t })))),
        h("tbody", {}, rows))) : h("p", { class: "empty", text: "Belum ada mahasiswa terdaftar di mata kuliah ini." })),
  ];
}

async function sessionPicker(onPick) {
  const sessions = await api(`/sessions?course_id=${state.courseId}`);
  const sel = h("select", { id: "session-select", "aria-label": "Pilih sesi" }, sessions.map((s) => h("option", { value: s.id, text: sessionLabel(s) })));
  const saved = Number(sessionStorage.getItem("labtrack_session"));
  if (sessions.some((s) => s.id === saved)) sel.value = saved;
  sel.addEventListener("change", () => { sessionStorage.setItem("labtrack_session", sel.value); onPick(Number(sel.value)); });
  return { sessions, sel };
}

async function viewKehadiran() {
  if (!state.courseId) return needCourse();
  const box = h("div", { class: "card" });
  const { sessions, sel } = await sessionPicker((id) => fill(id));
  const head = h("div", { class: "card" }, h("div", { class: "row" }, h("div", { class: "field" }, h("label", { for: "session-select", text: "Sesi praktikum" }), sel)));
  if (!sessions.length) return [head, h("div", { class: "card" }, h("p", { class: "empty", text: "Belum ada sesi untuk mata kuliah ini." }))];
  const statuses = [["present", "Hadir"], ["late", "Terlambat"], ["excused", "Izin"], ["absent", "Alpa"]];

  async function fill(sessionId) {
    box.replaceChildren(h("p", { class: "muted", text: "Memuat daftar peserta..." }));
    const [students, existing] = await Promise.all([api(`/courses/${state.courseId}/students`), api(`/sessions/${sessionId}/attendance`)]);
    const prev = new Map(existing.map((a) => [a.student_id, a]));
    const rows = students.map((st) => {
      const cur = (prev.get(st.id) || {}).status || "present";
      const seg = h("div", { class: "seg", role: "radiogroup", "aria-label": `Status ${st.full_name}` },
        statuses.map(([v, t]) => h("label", {}, h("input", { type: "radio", name: `s-${st.id}`, value: v, checked: v === cur }), h("span", { text: t }))));
      const note = h("input", { type: "text", placeholder: "Catatan (opsional)", value: (prev.get(st.id) || {}).note || "", maxlength: 255, "aria-label": `Catatan ${st.full_name}` });
      return { st, seg, note, tr: h("tr", {}, h("td", { text: st.nim }), h("td", { text: st.full_name }), h("td", {}, seg), h("td", {}, note)) };
    });
    const save = h("button", { class: "primary", text: "Simpan kehadiran" });
    save.addEventListener("click", () => busy(save, async () => {
      const records = rows.map(({ st, seg, note }) => ({ student_id: st.id, status: seg.querySelector("input:checked").value, note: note.value.trim() || null }));
      const res = await api(`/sessions/${sessionId}/attendance`, { method: "PUT", json: { records } });
      flash(`Kehadiran ${res.length} mahasiswa tersimpan.`, true);
      hint.textContent = `Sesi ini sudah tercatat untuk ${res.length} mahasiswa. Menyimpan lagi akan memperbarui catatan, bukan menggandakannya.`;
    }));
    const allPresent = h("button", { text: "Tandai semua hadir", onclick: () => rows.forEach(({ seg }) => { seg.querySelector("input[value=present]").checked = true; }) });
    const hint = h("p", { class: "muted", text: existing.length ? `Sesi ini sudah tercatat untuk ${existing.length} mahasiswa. Menyimpan lagi akan memperbarui catatan, bukan menggandakannya.` : "Sesi ini belum dicatat. Status awal semua Hadir." });
    box.replaceChildren(
      h("div", { class: "row" }, h("h2", { text: `Peserta (${students.length})`, style: "flex:1" }), allPresent, save),
      hint,
      students.length ? h("div", { class: "table-wrap" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", { text: "NIM" }), h("th", { text: "Nama" }), h("th", { text: "Status" }), h("th", { text: "Catatan" }))), h("tbody", {}, rows.map((r) => r.tr))))
        : h("p", { class: "empty", text: "Belum ada peserta. Daftarkan mahasiswa di menu Mahasiswa." }));
  }
  fill(Number(sel.value));
  return [head, box];
}

async function viewMahasiswa() {
  const list = h("div", { class: "table-wrap" });
  const q = h("input", { type: "search", id: "q", placeholder: "Cari NIM atau nama", value: sessionStorage.getItem("labtrack_q") || "" });
  const enrolled = state.courseId ? new Set((await api(`/courses/${state.courseId}/students`)).map((s) => s.id)) : new Set();

  async function search() {
    sessionStorage.setItem("labtrack_q", q.value);
    const page = await api(`/students?limit=100${q.value.trim() ? `&q=${encodeURIComponent(q.value.trim())}` : ""}`);
    list.replaceChildren(page.items.length ? h("table", {},
      h("thead", {}, h("tr", {}, h("th", { text: "NIM" }), h("th", { text: "Nama" }), h("th", { text: "Kelas" }), h("th", { text: "Email" }), h("th", { text: "Mata kuliah ini" }))),
      h("tbody", {}, page.items.map((s) => {
        const cell = h("td");
        if (enrolled.has(s.id)) cell.append(h("span", { class: "chip ok", text: "Terdaftar" }));
        else if (state.courseId) {
          const b = h("button", { text: "Daftarkan" });
          b.addEventListener("click", () => busy(b, async () => {
            await api(`/courses/${state.courseId}/enrollments`, { method: "POST", json: { student_ids: [s.id] } });
            enrolled.add(s.id); cell.replaceChildren(h("span", { class: "chip ok", text: "Terdaftar" }));
            flash(`${s.full_name} terdaftar di mata kuliah ini.`, true);
          }));
          cell.append(b);
        }
        return h("tr", {}, h("td", { text: s.nim }), h("td", { text: s.full_name }), h("td", { text: s.class_name || "-" }), h("td", { text: s.email || "-" }), cell);
      })))
      : h("p", { class: "empty", text: "Tidak ada mahasiswa yang cocok." }));
    list.prepend(h("p", { class: "muted", text: `${page.total} mahasiswa ditemukan.` }));
  }
  const find = h("button", { text: "Cari", onclick: (e) => busy(e.currentTarget, search) });
  q.addEventListener("keydown", (e) => { if (e.key === "Enter") busy(find, search); });

  const f = { nim: h("input", { id: "nim", required: true, pattern: "\\d{8,15}", placeholder: "8 sampai 15 digit" }), full_name: h("input", { id: "full_name", required: true, minlength: 2 }), class_name: h("input", { id: "class_name", placeholder: "SI-47-01" }), email: h("input", { id: "email", type: "email" }) };
  const add = h("button", { class: "primary", type: "submit", text: "Tambah" });
  const enrollToo = h("input", { type: "checkbox", id: "enroll-too", checked: !!state.courseId, style: "width:auto" });
  const form = h("form", { class: "card" }, h("h2", { text: "Tambah mahasiswa" }),
    h("div", { class: "row" },
      h("div", { class: "field" }, h("label", { for: "nim", text: "NIM" }), f.nim),
      h("div", { class: "field" }, h("label", { for: "full_name", text: "Nama lengkap" }), f.full_name),
      h("div", { class: "field narrow" }, h("label", { for: "class_name", text: "Kelas" }), f.class_name),
      h("div", { class: "field" }, h("label", { for: "email", text: "Email" }), f.email)),
    h("div", { class: "row" }, h("label", { for: "enroll-too", style: "display:flex;gap:6px;align-items:center;flex:1" }, enrollToo, "Langsung daftarkan ke mata kuliah yang dipilih"), add));
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    busy(add, async () => {
      const s = await api("/students", { method: "POST", json: { nim: f.nim.value.trim(), full_name: f.full_name.value.trim(), class_name: f.class_name.value.trim() || null, email: f.email.value.trim() || null } });
      if (enrollToo.checked && state.courseId) { await api(`/courses/${state.courseId}/enrollments`, { method: "POST", json: { student_ids: [s.id] } }); enrolled.add(s.id); }
      form.reset(); enrollToo.checked = !!state.courseId;
      flash(`${s.full_name} (${s.nim}) ditambahkan.`, true);
      await search();
    });
  });
  await search();
  return [h("div", { class: "card" }, h("div", { class: "row" }, h("div", { class: "field" }, h("label", { for: "q", text: "Cari mahasiswa" }), q), find), list), form];
}

async function viewLaporan() {
  if (!state.courseId) return needCourse();
  const box = h("div", { class: "card" });
  const { sessions, sel } = await sessionPicker((id) => fill(id));
  const head = h("div", { class: "card" }, h("div", { class: "row" }, h("div", { class: "field" }, h("label", { for: "session-select", text: "Sesi praktikum" }), sel)));
  if (!sessions.length) return [head, h("div", { class: "card" }, h("p", { class: "empty", text: "Belum ada sesi untuk mata kuliah ini." }))];
  const students = await api(`/courses/${state.courseId}/students`);
  const byId = new Map(students.map((s) => [s.id, s]));

  async function fill(sessionId) {
    const reports = await api(`/sessions/${sessionId}/reports`);
    const who = h("select", { id: "report-student" }, students.map((s) => h("option", { value: s.id, text: `${s.nim} · ${s.full_name}` })));
    const file = h("input", { type: "file", id: "report-file", accept: "application/pdf,.pdf" });
    const up = h("button", { class: "primary", text: "Unggah PDF" });
    up.addEventListener("click", () => busy(up, async () => {
      if (!file.files.length) { flash("Pilih berkas PDF terlebih dahulu."); return; }
      const fd = new FormData(); fd.append("student_id", who.value); fd.append("file", file.files[0]);
      await api(`/sessions/${sessionId}/reports`, { method: "POST", body: fd });
      flash("Laporan tersimpan. Unggahan ulang mengganti berkas lama dan mengosongkan nilai.", true);
      fill(sessionId);
    }));
    const rows = reports.map((r) => {
      const st = byId.get(r.student_id) || { nim: "-", full_name: `ID ${r.student_id}` };
      const score = h("input", { type: "number", min: 0, max: 100, step: "0.5", value: r.score ?? "", style: "width:90px", "aria-label": `Nilai ${st.full_name}` });
      const fb = h("input", { type: "text", value: r.feedback || "", placeholder: "Umpan balik", "aria-label": `Umpan balik ${st.full_name}` });
      const dl = h("button", { text: "Unduh" });
      dl.addEventListener("click", () => busy(dl, async () => { const u = await api(`/reports/${r.id}/download-url`); window.open(u.url, "_blank", "noopener"); }));
      const save = h("button", { text: "Simpan nilai" });
      save.addEventListener("click", () => busy(save, async () => {
        await api(`/reports/${r.id}/grade`, { method: "PATCH", json: { score: Number(score.value), feedback: fb.value.trim() || null } });
        flash(`Nilai ${st.full_name} tersimpan.`, true);
      }));
      return h("tr", {}, h("td", { text: st.nim }), h("td", { text: st.full_name }), h("td", { text: r.original_filename }),
        h("td", { class: "num", text: `${Math.max(1, Math.round(r.size_bytes / 1024))} KB` }),
        h("td", {}, r.score === null ? h("span", { class: "chip warn", text: "Belum dinilai" }) : h("span", { class: "chip ok", text: `${r.score}` })),
        h("td", {}, score), h("td", {}, fb), h("td", {}, h("div", { class: "actions" }, dl, save)));
    });
    box.replaceChildren(
      h("h2", { text: `Laporan masuk (${reports.length} dari ${students.length})` }),
      h("div", { class: "row" }, h("div", { class: "field" }, h("label", { for: "report-student", text: "Mahasiswa" }), who), h("div", { class: "field" }, h("label", { for: "report-file", text: "Berkas PDF (maks. 10 MB)" }), file), up),
      reports.length ? h("div", { class: "table-wrap" }, h("table", {}, h("thead", {}, h("tr", {}, ...["NIM", "Nama", "Berkas", "Ukuran", "Status", "Nilai", "Umpan balik", ""].map((t, i) => h("th", { class: i === 3 ? "num" : null, text: t })))), h("tbody", {}, rows)))
        : h("p", { class: "empty", text: "Belum ada laporan untuk sesi ini." }));
  }
  await fill(Number(sel.value));
  return [head, box];
}

async function viewAdmin() {
  if (state.me.role !== "admin") return [h("div", { class: "card" }, h("p", { class: "empty", text: "Menu ini hanya untuk koordinator." }))];
  const users = await api("/auth/users");
  const mk = (id, attrs = {}) => h("input", { id, ...attrs });
  const formCard = (title, fields, submitText, onSubmit) => {
    const btn = h("button", { class: "primary", type: "submit", text: submitText });
    const form = h("form", { class: "card" }, h("h2", { text: title }),
      h("div", { class: "row" }, fields.map(([label, input, narrow]) => h("div", { class: `field ${narrow ? "narrow" : ""}` }, h("label", { for: input.id, text: label }), input)), btn));
    form.addEventListener("submit", (e) => { e.preventDefault(); busy(btn, async () => { await onSubmit(); form.reset(); }); });
    return form;
  };
  const c = { code: mk("c-code", { required: true, placeholder: "SIDM-2026" }), name: mk("c-name", { required: true }), semester: mk("c-sem", { required: true, placeholder: "Ganjil 2026/2027" }) };
  const s = { no: mk("s-no", { type: "number", min: 1, max: 30, required: true }), title: mk("s-title", { required: true }), at: mk("s-at", { type: "datetime-local", required: true }), room: mk("s-room") };
  const u = { email: mk("u-email", { type: "email", required: true }), name: mk("u-name", { required: true }), pw: mk("u-pw", { type: "password", required: true, minlength: 8 }) };
  const role = h("select", { id: "u-role" }, h("option", { value: "assistant", text: "Asisten" }), h("option", { value: "admin", text: "Koordinator" }));
  return [
    formCard("Mata kuliah baru", [["Kode", c.code, true], ["Nama", c.name], ["Semester", c.semester]], "Buat", async () => {
      const r = await api("/courses", { method: "POST", json: { code: c.code.value.trim(), name: c.name.value.trim(), semester: c.semester.value.trim() } });
      await loadCourses(); state.courseId = r.id; $("#course-select").value = r.id; flash(`Mata kuliah ${r.code} dibuat.`, true);
    }),
    formCard("Sesi untuk mata kuliah terpilih", [["No.", s.no, true], ["Judul modul", s.title], ["Jadwal", s.at], ["Ruang", s.room, true]], "Buat sesi", async () => {
      if (!state.courseId) throw new Error("Pilih mata kuliah terlebih dahulu");
      const r = await api("/sessions", { method: "POST", json: { course_id: state.courseId, session_no: Number(s.no.value), title: s.title.value.trim(), scheduled_at: new Date(s.at.value).toISOString(), room: s.room.value.trim() || null } });
      flash(`Sesi modul ${r.session_no} dibuat.`, true);
    }),
    formCard("Akun staf baru", [["Email", u.email], ["Nama", u.name], ["Kata sandi sementara", u.pw], ["Peran", role, true]], "Buat akun", async () => {
      const r = await api("/auth/users", { method: "POST", json: { email: u.email.value.trim(), full_name: u.name.value.trim(), password: u.pw.value, role: role.value } });
      flash(`Akun ${r.email} dibuat. Sampaikan kata sandi sementara lewat kanal terpisah.`, true); render();
    }),
    h("div", { class: "card" }, h("h2", { text: `Akun staf (${users.length})` }), h("div", { class: "table-wrap" }, h("table", {},
      h("thead", {}, h("tr", {}, h("th", { text: "Nama" }), h("th", { text: "Email" }), h("th", { text: "Peran" }), h("th", { text: "Status" }))),
      h("tbody", {}, users.map((x) => h("tr", {}, h("td", { text: x.full_name }), h("td", { text: x.email }), h("td", { text: x.role === "admin" ? "Koordinator" : "Asisten" }),
        h("td", {}, h("span", { class: `chip ${x.is_active ? "ok" : "bad"}`, text: x.is_active ? "Aktif" : "Nonaktif" })))))))),
  ];
}

// ---------- wiring
$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = $("#login-submit"), err = $("#login-error");
  btn.disabled = true; err.hidden = true;
  try {
    await login($("#login-email").value.trim(), $("#login-password").value);
    await boot();
  } catch (ex) {
    err.replaceChildren(h("span", { text: ex instanceof ApiError ? (ex.status === 401 ? "Email atau kata sandi salah." : ex.message) : "Tidak dapat terhubung ke server." }));
    if (ex instanceof ApiError && ex.requestId) err.append(h("span", {}, "Kode: ", h("code", { class: "rid", text: ex.requestId })));
    err.hidden = false;
  } finally { btn.disabled = false; }
});
$("#logout").addEventListener("click", () => logout());
$("#course-select").addEventListener("change", (e) => { state.courseId = Number(e.target.value); sessionStorage.setItem("labtrack_course", state.courseId); render(); });
document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => { state.view = b.dataset.view; render(); }));

(async () => {
  state.token = sessionStorage.getItem("labtrack_token");
  if (!state.token) { logout(); return; }
  try { await boot(); } catch { logout(); }
})();
