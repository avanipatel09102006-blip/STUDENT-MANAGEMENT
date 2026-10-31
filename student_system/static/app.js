const $ = id => document.getElementById(id);
const F = {q: "", course: "", sort: "name"};
let editId = null, tt;
const toast = m => { const t = $("toast"); t.textContent = m; t.classList.add("show"); clearTimeout(tt); tt = setTimeout(() => t.classList.remove("show"), 2400); };
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
const initials = n => n.split(/\s+/).slice(0, 2).map(w => w[0]).join("").toUpperCase();

async function load() {
  const p = new URLSearchParams(F);
  const d = await (await fetch("/api/students?" + p)).json();
  $("sTotal").textContent = d.stats.total; $("sGpa").textContent = d.stats.avg_cgpa;
  $("sAtt").textContent = d.stats.avg_attendance + "%"; $("sLow").textContent = d.stats.low_attendance;
  renderCourses(d.courses); renderRows(d.students);
}

function renderCourses(list) {
  const box = $("courseBars"), cur = $("courseFilter").value;
  const sel = $("courseFilter"); sel.innerHTML = ""; sel.append(new Option("All courses", ""));
  list.forEach(c => sel.append(new Option(c.course, c.course))); sel.value = F.course;
  $("courseList").innerHTML = ""; list.forEach(c => { const o = document.createElement("option"); o.value = c.course; $("courseList").append(o); });
  box.hidden = !list.length; box.innerHTML = "";
  if (!list.length) return;
  box.append(el("h2", "", "Students per course"));
  const max = Math.max(...list.map(c => c.count));
  list.forEach(c => {
    const r = el("div", "cbar"), t = el("div", "t"), i = el("i");
    i.style.width = c.count / max * 100 + "%"; t.append(i);
    r.append(el("span", "", c.course), t, el("span", "", c.count)); box.append(r);
  });
}

function cell(label, ...kids) { const td = el("td"); td.dataset.l = label; td.append(...kids); return td; }

function renderRows(list) {
  const body = $("rows"); body.innerHTML = "";
  $("empty").hidden = list.length > 0;
  $("empty").textContent = F.q || F.course ? "No students match your search." : "No students yet. Press Add student to create the first record.";
  list.forEach(s => {
    const tr = el("tr");
    const who = el("div", "who"), info = el("div"), nm = el("b", "", s.name);
    info.append(nm, el("small", "", s.email)); who.append(el("div", "av", initials(s.name)), info);
    const first = cell("", who); first.className = "first";
    const gcls = s.cgpa >= 8 ? "good" : s.cgpa >= 6 ? "mid" : "low";
    const acls = s.attendance >= 75 ? "good" : "low";
    const acts = el("div", "acts");
    const eb = el("button", "", "Edit"); eb.onclick = () => openForm(s);
    const db = el("button", "del", "Delete"); db.onclick = () => remove(s);
    acts.append(eb, db);
    const last = cell("", acts); last.className = "last";
    tr.append(first, cell("Enrollment", s.enrollment), cell("Course", s.course), cell("Sem", String(s.semester)),
      cell("CGPA", el("span", "pill " + gcls, s.cgpa.toFixed(2))),
      cell("Attendance", el("span", "pill " + acls, s.attendance + "%")), last);
    body.append(tr);
  });
}

function openForm(s) {
  editId = s ? s.id : null; $("formErr").textContent = "";
  $("dlgTitle").textContent = s ? "Edit student" : "Add student";
  const f = $("form"); f.reset();
  if (s) ["name","enrollment","email","phone","course","semester","cgpa","attendance"].forEach(k => f.elements[k].value = s[k] ?? "");
  $("dlg").showModal(); f.elements.name.focus();
}

$("form").addEventListener("submit", async e => {
  e.preventDefault();
  const f = e.target;
  if (!f.checkValidity()) { f.reportValidity(); return; }
  const body = Object.fromEntries(new FormData(f));
  const r = await fetch(editId ? `/api/students/${editId}` : "/api/students", {
    method: editId ? "PUT" : "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
  const d = await r.json();
  if (!r.ok) { $("formErr").textContent = d.error; return; }
  $("dlg").close(); toast(editId ? "Student updated" : "Student added"); load();
});

async function remove(s) {
  if (!confirm(`Delete ${s.name}? This cannot be undone.`)) return;
  await fetch(`/api/students/${s.id}`, {method: "DELETE"}); toast("Student deleted"); load();
}

$("addBtn").onclick = () => openForm(null);
$("cancel").onclick = () => $("dlg").close();
let st; $("search").oninput = e => { clearTimeout(st); st = setTimeout(() => { F.q = e.target.value.trim(); load(); }, 250); };
$("courseFilter").onchange = e => { F.course = e.target.value; load(); };
$("sort").onchange = e => { F.sort = e.target.value; load(); };
load();
