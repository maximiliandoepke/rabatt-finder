"use strict";

const PAGE = 50;
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const norm = (s) => String(s ?? "").toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/ß/g, "ss");
const NEW_DAYS = 7; // so lange gilt ein Angebot nach dem ersten Auftauchen als „neu“
const toDate = (s) => {
  const m = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(s || "");
  return m ? new Date(+m[3], m[2] - 1, +m[1]) : null;
};
const daysSince = (s) => {
  const d = toDate(s);
  return d ? Math.floor((Date.now() - d) / 864e5) : Infinity;
};
const isNew = (o) => daysSince(o.seit) <= NEW_DAYS;

let DATA = null;
const VOCAB = new Set(); // alle Wörter aus den Angeboten – für die Tippfehler-Toleranz
const WEIGHTS = [10, 6, 4, 3, 1];
let OFFERS = [];
let PLAT = [];
let shown = PAGE;

const state = { tab: "suche", q: "", kat: "", plat: "", kanal: "", sort: "relevanz", neu: false };

// ---------- Laden ----------
fetch("offers.json", { cache: "no-cache" })
  .then((r) => {
    if (!r.ok) throw new Error(r.status);
    return r.json();
  })
  .then(init)
  .catch(() => {
    $("meta").textContent = "Die Angebote konnten nicht geladen werden.";
  });

function init(data) {
  DATA = data;
  PLAT = data.plattformen;
  OFFERS = data.offers.map((o) => ({
    ...o,
    // Suchfelder mit Gewichtung: Anbieter > Angebot > Schlagworte > Kategorie > Beschreibung/Hinweis
    f: [norm(o.a), norm(o.o), norm(o.s), norm(o.k + " " + o.u), norm(o.d + " " + o.h)],
  }));
  OFFERS.forEach((o) => o.f.join(" ").split(/[^a-z0-9]+/).forEach((t) => t.length >= 4 && VOCAB.add(t)));

  const total = OFFERS.length.toLocaleString("de-DE");
  const parts = PLAT.map((p, i) => `${p} ${data.anzahl[i].toLocaleString("de-DE")}`).join(" · ");
  const neu = OFFERS.filter(isNew).length;
  $("meta").textContent = `Stand ${data.stand} · ${total} Angebote · ${parts}` + (neu ? ` · ${neu} neu` : "");
  $("foot").textContent = data.entfallen.length ? `${data.entfallen.length} Angebote seit dem letzten Update entfallen.` : "";
  $("neu-wrap").hidden = !neu;

  const kats = [...new Set(OFFERS.map((o) => o.k))].sort((a, b) => a.localeCompare(b, "de"));
  $("kat").insertAdjacentHTML("beforeend", kats.map((k) => `<option>${esc(k)}</option>`).join(""));
  $("plat").insertAdjacentHTML("beforeend", PLAT.map((p, i) => `<option value="${i}">${esc(p)}</option>`).join(""));

  readHash();
  bind();
  renderAll();
  showStatus();
}

// Hinweis, falls das letzte automatische Update nicht vollständig war
const CB_REMIND_DAYS = 14;

function showStatus() {
  fetch("status.json", { cache: "no-cache" })
    .then((r) => (r.ok ? r.json() : null))
    .then((s) => {
      const names = { cb: "Corporate Benefits", sb: "Student Beans", ud: "UNiDAYS" };
      const pl = (s && s.plattformen) || {};
      const notes = [];
      const failed = Object.entries(pl).filter(([k, v]) => k !== "cb" && !v.ok).map(([k]) => names[k] || k);
      if (failed.length) {
        notes.push(`Beim letzten automatischen Update konnte ${esc(failed.join(", "))} nicht aktualisiert werden – dort werden die Angebote vom vorherigen Stand angezeigt.`);
      }
      const cb = pl.cb && pl.cb.ok ? pl.cb.stand : null;
      if (!cb) {
        notes.push(`Corporate Benefits wurde noch nicht eingespielt. <a href="lesezeichen.html">So geht's</a>`);
      } else if (daysSince(cb) > CB_REMIND_DAYS) {
        notes.push(`Corporate Benefits ist vom ${esc(cb)}. <a href="lesezeichen.html">Jetzt aktualisieren</a>`);
      }
      const stands = Object.entries(pl).filter(([, v]) => v.stand).map(([k, v]) => `${names[k] || k}: ${v.stand}`);
      if (stands.length) $("foot").textContent = [`Datenstand – ${stands.join(", ")}`, $("foot").textContent].filter(Boolean).join(" · ");
      if (!notes.length) return;
      $("status").innerHTML = notes.join("<br>");
      $("status").hidden = false;
    })
    .catch(() => {});
}

// ---------- Zustand <-> URL ----------
function readHash() {
  const h = new URLSearchParams(location.hash.slice(1));
  for (const k of Object.keys(state)) if (h.has(k)) state[k] = k === "neu" ? h.get(k) === "1" : h.get(k);
  syncInputs();
}

function syncInputs() {
  $("q").value = state.q;
  $("kat").value = state.kat;
  $("plat").value = state.plat;
  $("kanal").value = state.kanal;
  $("sort").value = state.sort;
  $("nurneu").checked = state.neu;
}

function writeHash() {
  const h = new URLSearchParams();
  for (const [k, v] of Object.entries(state)) {
    if (k === "tab" ? v !== "suche" : k === "sort" ? v !== "relevanz" : v) h.set(k, v === true ? "1" : v);
  }
  history.replaceState(null, "", h.toString() ? "#" + h : location.pathname);
}

function bind() {
  document.querySelectorAll(".tabs button").forEach((b) =>
    b.addEventListener("click", () => {
      state.tab = b.dataset.tab;
      writeHash();
      renderTabs();
    })
  );
  let t;
  $("q").addEventListener("input", () => {
    clearTimeout(t);
    t = setTimeout(() => update("q", $("q").value), 150);
  });
  for (const id of ["kat", "plat", "kanal", "sort"]) $(id).addEventListener("change", () => update(id, $(id).value));
  $("nurneu").addEventListener("change", () => update("neu", $("nurneu").checked));
  $("reset").addEventListener("click", () => {
    Object.assign(state, { q: "", kat: "", plat: "", kanal: "", sort: "relevanz", neu: false });
    syncInputs();
    update();
  });
  $("more").addEventListener("click", () => {
    shown += PAGE;
    renderResults();
  });
  $("vq").addEventListener("input", renderCompare);
  window.addEventListener("hashchange", () => {
    readHash();
    renderTabs();
    update();
  });
}

function update(key, value) {
  if (key) state[key] = value;
  shown = PAGE;
  writeHash();
  renderResults();
}

function renderAll() {
  renderTabs();
  renderResults();
  renderOverview();
  renderTop();
  renderCompare();
}

function renderTabs() {
  document.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", b.dataset.tab === state.tab));
  document.querySelectorAll(".tab").forEach((s) => (s.hidden = s.id !== "tab-" + state.tab));
}

// ---------- Suche ----------
// Einfache deutsche Wortstamm-Bildung: "schuhe" -> "schuh", "fernseher" -> "fernseh"
function stem(w) {
  if (w.length <= 4) return w;
  const s = w.replace(/(ern|en|er|es|e|n|s)$/, "");
  return s.length >= 4 ? s : w;
}

function editDistance(a, b, max) {
  if (Math.abs(a.length - b.length) > max) return max + 1;
  let prev = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    const cur = [i];
    let rowMin = i;
    for (let j = 1; j <= b.length; j++) {
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      rowMin = Math.min(rowMin, cur[j]);
    }
    if (rowMin > max) return max + 1;
    prev = cur;
  }
  return prev[b.length];
}

// Je Suchwort: das Wort selbst (zählt voll), dazu Varianten (Wortstamm oder bei Tippfehlern ähnliche Wörter)
const variantCache = new Map();
const existsAnywhere = (s) => OFFERS.some((o) => o.f.some((f) => f.includes(s)));

function variants(word) {
  if (variantCache.has(word)) return variantCache.get(word);
  let result;
  const st = stem(word);
  if (existsAnywhere(st)) {
    result = { full: word, alts: [st] };
  } else {
    // Tippfehler: ähnlichste Wörter aus den Angeboten (ganzes Wort oder Wortanfang)
    const max = word.length >= 7 ? 2 : 1;
    let bestD = max + 1;
    let cands = [];
    for (const t of VOCAB) {
      const d = Math.min(editDistance(word, t, max), editDistance(word, t.slice(0, word.length), max) + 0.5);
      if (d < bestD) {
        bestD = d;
        cands = [t];
      } else if (d === bestD) cands.push(t);
    }
    result = { full: null, alts: bestD <= max ? cands.slice(0, 8) : [st] };
  }
  variantCache.set(word, result);
  return result;
}

function scoreOffer(o, groups) {
  let total = 0, matched = 0;
  for (const g of groups) {
    let best = 0;
    o.f.forEach((field, i) => {
      if (g.full && field.includes(g.full)) best = Math.max(best, WEIGHTS[i]);
      else if (g.alts.some((v) => field.includes(v))) best = Math.max(best, WEIGHTS[i] * 0.6);
    });
    if (best) {
      matched++;
      total += best;
    }
  }
  return { total, matched };
}

let fallbackUsed = false;

function filtered() {
  fallbackUsed = false;
  const base = OFFERS.filter(
    (o) =>
      (!state.kat || o.k === state.kat) &&
      (state.plat === "" || o.p === Number(state.plat)) &&
      (!state.kanal || o.ch.includes(state.kanal)) &&
      (!state.neu || isNew(o))
  );
  const words = [...new Set(norm(state.q).split(/[^a-z0-9]+/).filter((w) => w.length >= 2))];
  if (!words.length) {
    base.forEach((o) => (o._score = 0));
    return base;
  }
  const groups = words.map(variants);
  for (const o of base) {
    const s = scoreOffer(o, groups);
    o._score = s.total;
    o._matched = s.matched;
  }
  const all = base.filter((o) => o._matched === groups.length);
  if (all.length || groups.length === 1) return all;
  // Keine Treffer mit allen Wörtern: Angebote zeigen, die möglichst viele der Wörter enthalten
  fallbackUsed = true;
  return base.filter((o) => o._matched > 0).map((o) => ((o._score += o._matched * 100), o));
}

function sortOffers(list) {
  const byPct = (a, b) => (b.r ?? -1) - (a.r ?? -1) || a.p - b.p;
  if (state.sort === "name") return list.sort((a, b) => a.a.localeCompare(b.a, "de") || byPct(a, b));
  if (state.sort === "neu") return list.sort((a, b) => (toDate(b.seit) || 0) - (toDate(a.seit) || 0) || byPct(a, b));
  if (state.sort === "rabatt") return list.sort(byPct);
  return list.sort((a, b) => b._score - a._score || byPct(a, b)); // Relevanz, ohne Suchbegriff = nach Rabatt
}

function renderResults() {
  const list = sortOffers(filtered());
  const best = Math.max(-1, ...list.map((o) => o.r ?? -1));

  // Zusammenfassung je Plattform
  const per = PLAT.map((_, i) => {
    const l = list.filter((o) => o.p === i);
    return { n: l.length, best: Math.max(-1, ...l.map((o) => o.r ?? -1)) };
  });
  $("summary").innerHTML =
    per
      .map(
        (s, i) => `<div class="sum ${best > 0 && s.best === best ? "best" : ""}" style="--pc:var(--p${i})">
        <div class="n">${esc(PLAT[i])} · ${s.n} Treffer</div>
        <div class="v">${s.best > 0 ? "bis " + s.best + " %" : "–"}</div></div>`
      )
      .join("") + `<p class="count" style="grid-column:1/-1">${
        fallbackUsed ? "Kein Angebot enthält alle Suchwörter – hier die Angebote mit den meisten Übereinstimmungen. " : ""
      }${list.length.toLocaleString("de-DE")} Treffer${best > 0 ? " · bester Rabatt grün markiert" : ""}</p>`;

  $("results").innerHTML = list.length
    ? list.slice(0, shown).map((o) => offerHtml(o, best > 0 && o.r === best)).join("")
    : `<li class="empty">Keine Angebote gefunden. Weniger Wörter oder einen anderen Filter versuchen.</li>`;
  $("more").hidden = list.length <= shown;
  $("more").textContent = `Mehr anzeigen (${(list.length - shown).toLocaleString("de-DE")} weitere)`;
}

function offerHtml(o, isBest) {
  const tags = [
    `<span class="tag plat" style="--pc:var(--p${o.p})">${esc(PLAT[o.p])}</span>`,
    `<span class="tag">${esc(o.k)}</span>`,
    o.ch !== "online" ? `<span class="tag">${esc(o.ch)}</span>` : "",
    isNew(o) ? `<span class="tag neu">neu</span>` : "",
    o.h ? `<span>${esc(o.h)}</span>` : "",
  ].join("");
  return `<li class="offer ${isBest ? "best" : ""}">
    <div class="pct ${o.r == null ? "none" : ""}">${o.r == null ? esc(o.ra) : o.r + "&nbsp;%"}</div>
    <div class="title">${esc(o.a)} <span class="what">– ${esc(o.o)}</span></div>
    <a class="go" href="${esc(o.l)}" target="_blank" rel="noopener noreferrer">Zum Angebot ↗</a>
    <div class="tags">${tags}</div>
    ${o.d ? `<p class="desc">${esc(o.d)}</p>` : ""}
  </li>`;
}

// ---------- Übersicht ----------
function bestOf(list) {
  return list.reduce((m, o) => (o.r != null && (!m || o.r > m.r) ? o : m), null);
}

function renderOverview() {
  const kats = [...new Set(OFFERS.map((o) => o.k))].sort((a, b) => a.localeCompare(b, "de"));
  const head = `<tr><th>Kategorie</th>${PLAT.map((p) => `<th class="num">${esc(p)}</th>`).join("")}<th class="num">Gesamt</th><th>Bestes Angebot</th></tr>`;
  const rows = kats.map((k) => {
    const items = OFFERS.filter((o) => o.k === k);
    const bests = PLAT.map((_, i) => bestOf(items.filter((o) => o.p === i)));
    const top = bestOf(bests.filter(Boolean));
    const cells = PLAT.map((_, i) => {
      const n = items.filter((o) => o.p === i).length;
      const b = bests[i];
      if (!n) return `<td class="num dim">–</td>`;
      const isTop = top && b && b.r === top.r;
      return `<td class="num ${isTop ? "best" : ""}">${n}<br><small>${b ? "bis " + b.r + " %" : "ohne %"}</small></td>`;
    });
    return `<tr><td><button class="catlink" data-kat="${esc(k)}">${esc(k)}</button></td>${cells.join("")}
      <td class="num">${items.length}</td>
      <td>${top ? `${esc(top.a)} <span class="dim">(${esc(PLAT[top.p])})</span><br><small>${esc(top.o)}</small>` : ""}</td></tr>`;
  });
  const sum = `<tr class="sum-row"><td>Gesamt</td>${DATA.anzahl.map((n) => `<td class="num">${n}</td>`).join("")}<td class="num">${OFFERS.length}</td><td></td></tr>`;
  $("ov").innerHTML = `<thead>${head}</thead><tbody>${rows.join("")}${sum}</tbody>`;
  $("ov").querySelectorAll(".catlink").forEach((b) =>
    b.addEventListener("click", () => {
      Object.assign(state, { q: "", kat: b.dataset.kat, plat: "", kanal: "", neu: false, tab: "suche" });
      syncInputs();
      update();
      renderTabs();
      scrollTo(0, 0);
    })
  );
}

// ---------- Top-Angebote ----------
function renderTop() {
  const kats = [...new Set(OFFERS.map((o) => o.k))].sort((a, b) => a.localeCompare(b, "de"));
  $("top").innerHTML = kats
    .map((k) => {
      const seen = new Set();
      const top = OFFERS.filter((o) => o.k === k && o.r != null)
        .sort((a, b) => b.r - a.r || a.p - b.p)
        .filter((o) => {
          const key = o.p + "|" + o.a.toLowerCase();
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        })
        .slice(0, 5);
      if (!top.length) return "";
      return `<div class="card"><h2>${esc(k)}</h2><ol>${top
        .map(
          (o, i) => `<li class="${i === 0 ? "first" : ""}"><a href="${esc(o.l)}" target="_blank" rel="noopener noreferrer">${esc(o.a)}</a>
          – ${o.r} %<br><span class="small">${esc(PLAT[o.p])} · ${esc(o.o)}</span></li>`
        )
        .join("")}</ol></div>`;
    })
    .join("");
}

// ---------- Anbieter-Vergleich ----------
let GROUPS = null;

function renderCompare() {
  if (!GROUPS) {
    const g = new Map();
    for (const o of OFFERS) if (o.b.length >= 2) (g.get(o.b) || g.set(o.b, []).get(o.b)).push(o);
    GROUPS = [...g.values()]
      .filter((l) => new Set(l.map((o) => o.p)).size >= 2)
      .map((l) => ({ name: l.map((o) => o.a).sort((a, b) => a.length - b.length)[0], items: l }))
      .sort((a, b) => a.name.localeCompare(b.name, "de"));
  }
  const f = norm($("vq").value.trim());
  const list = GROUPS.filter((g) => !f || norm(g.name).includes(f));
  $("vhint").textContent = `${GROUPS.length} Anbieter gibt es auf mehreren Plattformen. Grün = Plattform mit dem höchsten Rabatt; „ohne %“ = Angebot vorhanden, aber ohne Prozentrabatt.`;
  const head = `<tr><th>Anbieter</th>${PLAT.map((p) => `<th class="num">${esc(p)}</th>`).join("")}<th>Bestes Angebot</th></tr>`;
  const rows = list.map((g) => {
    const bests = PLAT.map((_, i) => bestOf(g.items.filter((o) => o.p === i)));
    const top = bestOf(bests.filter(Boolean));
    const cells = PLAT.map((_, i) => {
      const has = g.items.some((o) => o.p === i);
      const b = bests[i];
      if (!has) return `<td class="num dim">–</td>`;
      if (!b) return `<td class="num dim">ohne %</td>`;
      return `<td class="num ${top && b.r === top.r ? "best" : ""}">${b.r} %</td>`;
    });
    return `<tr><td>${esc(g.name)}</td>${cells.join("")}<td>${
      top ? `<a href="${esc(top.l)}" target="_blank" rel="noopener noreferrer">${esc(PLAT[top.p])}</a>: ${esc(top.o)}` : `<span class="dim">kein %-Rabatt</span>`
    }</td></tr>`;
  });
  $("cmp").innerHTML = `<thead>${head}</thead><tbody>${rows.join("") || `<tr><td colspan="5" class="dim">Kein Anbieter gefunden.</td></tr>`}</tbody>`;
}
