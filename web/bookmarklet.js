(async () => {
  const S = "__ORIGIN__";
  if (!/(^|\.)mitarbeiterangebote\.de$/.test(location.hostname)) {
    alert("Rabatt-Finder: Bitte zuerst Corporate Benefits öffnen und einloggen, dann den Knopf erneut klicken.");
    return;
  }
  const w = window.open(S + "/angebote/upload.html", "rabattfinder", "width=560,height=480");
  if (!w) {
    alert("Rabatt-Finder: Das Fenster wurde blockiert. Bitte Pop-ups für diese Seite erlauben und erneut klicken.");
    return;
  }
  let ready = false;
  addEventListener("message", (e) => {
    if (e.origin === S && e.data === "rf-ready") ready = true;
  });
  const T = (e) => (e ? e.textContent.replace(/\s+/g, " ").trim() : "");
  const cats = {};
  document.querySelectorAll('a[href^="/overview/"]').forEach((a) => {
    const h = a.getAttribute("href");
    const t = a.textContent.trim();
    if (!h.includes("#") && t.startsWith("Alle Angebote")) cats[h.split("/")[2]] = t.replace("Alle Angebote", "").trim();
  });
  const out = {};
  for (const [cid, name] of Object.entries(cats)) {
    const res = await fetch("/overview/" + cid, { credentials: "include" });
    const doc = new DOMParser().parseFromString(await res.text(), "text/html");
    let sub = "";
    doc.querySelectorAll("main h2, main .cbg3-list-item").forEach((el) => {
      if (el.tagName === "H2") {
        sub = T(el);
        return;
      }
      const a = el.querySelector('a[href*="/offer/"]');
      if (!a) return;
      const id = (a.getAttribute("href").match(/offer\/(\d+)/) || [])[1];
      const o = out[id] || (out[id] = {
        id,
        title: T(el.querySelector("h3")),
        copy: T(el.querySelector(".cbg3-list-item--copy")),
        disc: T(el.querySelector(".cbg3-list-item--discount")),
        info: T(el.querySelector(".cbg3-offerlistitem--infos")),
        rest: T(el.querySelector(".cbg3-offer-list-item--rest-days")),
        cats: [],
        subs: [],
      });
      if (!o.cats.includes(name)) o.cats.push(name);
      if (sub && sub !== "ANGEBOT DES MONATS" && !o.subs.includes(sub)) o.subs.push(sub);
    });
    if (ready) w.postMessage({ type: "rf-progress", text: name }, S);
  }
  for (let i = 0; i < 600 && !ready; i++) await new Promise((r) => setTimeout(r, 500));
  if (!ready) {
    alert("Rabatt-Finder: Das Upload-Fenster hat nicht geantwortet. Bitte dort anmelden und den Knopf erneut klicken.");
    return;
  }
  w.postMessage({ type: "rf-cb", offers: Object.values(out), kategorien: Object.keys(cats).length }, S);
})();
