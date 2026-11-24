// Shared by the USA pages (site/usa/): live data, the county map, search, the county card. Needs d3 (7.9.0).
// The live forecast is storm-outage-live's usa/latest.json (hourly); alert levels are that repo's alerts/config.json,
// keyed by the model that made the forecast, so the page and the alerts always use the same cut-offs.
"use strict";

const USA = (() => {
  const ROOT = (document.currentScript && document.currentScript.src || "").replace(/usa\.js.*$/, "");
  const LIVE = "https://raw.githubusercontent.com/UgoBruzadin/storm-outage-live/main";
  const FALLBACK_LEVELS = [{ name: "Elevated", chance: 0.10 }, { name: "High", chance: 0.20 }];
  const cache = {};

  const json = (url, opts) => cache[url] || (cache[url] = fetch(url, opts).then(r => {
    if (!r.ok) throw new Error(`${r.status} ${url}`);
    return r.json();
  }));
  const data = name => json(`${ROOT}data/${name}`);

  // ---------- the live forecast ----------
  // {latest, levels, sample}: sample is true when the USA feed isn't up yet and the page shows a saved forecast
  async function live() {
    let latest, sample = false;
    try { latest = await json(`${LIVE}/usa/latest.json`, { cache: "no-cache" }); }
    catch (e) { latest = await data("sample_latest.json"); sample = true; }
    let levels = FALLBACK_LEVELS;
    try {
      const cfg = await json(`${LIVE}/alerts/config.json`, { cache: "no-cache" });
      const lv = cfg.levels && cfg.levels[latest.model_trained];
      if (lv && lv.length) levels = lv.map(l => ({ name: l.label || l.name, chance: l.chance, meaning: l.meaning }));
    } catch (e) { /* the fallback levels are the same as config.json's for this model */ }
    levels = levels.slice().sort((a, b) => a.chance - b.chance);
    const byId = new Map(latest.counties.map(([id, p, low, high]) => [id, { p, low, high }]));
    return { latest, levels, sample, byId, drivers: latest.drivers || {} };
  }

  function levelOf(p, levels) {
    let lv = null;
    for (const l of levels) if (p >= l.chance) lv = l;
    return lv;
  }

  // chance -> fill: below 2% idle, then four steps; the two alert levels are the darker two
  function fill(p, levels) {
    if (p == null) return "var(--idle)";
    const [el, hi] = [levels[0].chance, levels[levels.length - 1].chance];
    if (p >= hi * 1.75) return "var(--c5)";
    if (p >= hi) return "var(--c4)";
    if (p >= el) return "var(--c3)";
    if (p >= 0.05) return "var(--c2)";
    if (p >= 0.02) return "var(--c1)";
    return "var(--idle)";
  }
  const legendItems = levels => [
    ["var(--idle)", "under 2%"], ["var(--c1)", "2–5%"], ["var(--c2)", `5–${pct(levels[0].chance)}`],
    ["var(--c3)", `${levels[0].name} (${pct(levels[0].chance)}+)`],
    ["var(--c4)", `${levels[levels.length - 1].name} (${pct(levels[levels.length - 1].chance)}+)`],
  ];

  const pct = p => (p == null ? "–" : p < 0.01 && p > 0 ? "<1%" : `${Math.round(p * 100)}%`);
  const slug = id => id.replace(/\+/g, "-");
  const countyUrl = id => `${ROOT}county/${slug(id)}.html`;
  const feedUrl = id => `${LIVE}/usa/feeds/${slug(id)}.xml`;

  const parseIso = s => new Date(/T\d\d:\d\dZ$/.test(s) ? s.replace("Z", ":00Z") : /T\d\dZ$/.test(s) ? s.replace("Z", ":00:00Z") : s);
  function windowText(latest, tz) {
    const [a, b] = latest.window.map(parseIso);
    const f = (d, day) => d.toLocaleString("en-US", { hour: "numeric", timeZone: tz, ...(day ? { weekday: "short" } : {}) })
      .replace(" AM", " am").replace(" PM", " pm");
    const zone = b.toLocaleString("en-US", { timeZone: tz, timeZoneName: "short" }).split(" ").pop();
    return `${f(a, true)} to ${f(b)} ${zone}`;
  }
  function ago(iso) {
    const m = Math.round((Date.now() - parseIso(iso)) / 60000);
    if (m < 2) return "just now";
    if (m < 90) return `${m} min ago`;
    const h = Math.round(m / 60);
    return h < 48 ? `${h} hours ago` : `${Math.round(h / 24)} days ago`;
  }

  // ---------- the map ----------
  // draw(svg, map, {width, height}) -> {counties, path, projection, zoomTo(id), reset()}
  function drawMap(svgNode, map, { width = 975, height = 610, fit = null } = {}) {
    const svg = d3.select(svgNode).attr("viewBox", `0 0 ${width} ${height}`);
    svg.selectAll("*").remove();
    const defs = svg.append("defs");
    defs.append("pattern").attr("id", "hatch").attr("patternUnits", "userSpaceOnUse").attr("width", 4).attr("height", 4)
      .attr("patternTransform", "rotate(45)").append("rect").attr("width", 1.4).attr("height", 4).style("fill", "var(--warn)");
    const counties = map.counties.map(c => ({ type: "Feature", id: c.id, geometry: c.g }));
    const states = map.states.map(s => ({ type: "Feature", properties: { name: s.name }, geometry: s.g }));
    const fc = { type: "FeatureCollection", features: fit || states };
    const projection = d3.geoConicEqualArea().parallels([29.5, 45.5]).rotate([96, 0]).fitSize([width, height], fc);
    const path = d3.geoPath(projection);
    const g = svg.append("g");
    const sel = g.append("g").selectAll("path").data(counties).join("path").attr("class", "county").attr("d", path)
      .style("fill", "var(--idle)");
    const overlay = g.append("g");
    g.append("g").selectAll("path").data(states).join("path").attr("class", "state").attr("d", path);
    const zoom = d3.zoom().scaleExtent([1, 14]).translateExtent([[0, 0], [width, height]])
      .filter(e => e.type === "wheel" ? (e.ctrlKey || e.metaKey) : (e.type !== "touchstart" || e.touches.length > 1) && !e.button)
      .on("zoom", e => {
        g.attr("transform", e.transform);
        g.selectAll("path.county").style("stroke-width", 0.25 / e.transform.k);
        g.selectAll("path.state").style("stroke-width", 1 / e.transform.k);
        g.selectAll("path.out").style("stroke-width", 1.1 / e.transform.k);
        g.selectAll("path.county.sel").style("stroke-width", 1.6 / e.transform.k);
      });
    svg.call(zoom).on("dblclick.zoom", null);
    const byId = new Map(counties.map(f => [f.id, f]));
    return {
      svg, g, counties: sel, overlay, path, projection, byId, features: counties,
      zoomTo(id, k = 5) {
        const f = byId.get(id);
        if (!f) return;
        const [x, y] = path.centroid(f);
        svg.transition().duration(600).call(zoom.transform, d3.zoomIdentity.translate(width / 2, height / 2)
          .scale(k).translate(-x, -y));
      },
      zoomBy(f) { svg.transition().duration(300).call(zoom.scaleBy, f); },
      reset() { svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity); },
      select(id) {
        sel.classed("sel", f => f.id === id).filter(f => f.id === id).raise()
          .style("stroke-width", function () { return 1.6 / d3.zoomTransform(svgNode).k; });
      },
    };
  }

  function tip() {
    let el = document.querySelector(".tip");
    if (!el) { el = document.createElement("div"); el.className = "tip"; document.body.appendChild(el); }
    return {
      show(e, html) {
        el.innerHTML = html; el.style.display = "block";
        const x = Math.min(e.clientX + 14, innerWidth - el.offsetWidth - 8);
        el.style.left = `${x}px`; el.style.top = `${e.clientY + 14}px`;
      },
      hide() { el.style.display = "none"; },
    };
  }

  // ---------- search: county names, and ZIP codes ----------
  function search(input, counties, onPick) {
    const list = document.createElement("ul");
    list.hidden = true;
    list.setAttribute("role", "listbox");
    input.after(list);
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    const all = Object.entries(counties).map(([id, c]) => ({ id, name: c.n, st: c.s, key: `${c.n} ${c.s}`.toLowerCase() }));
    let items = [], active = 0;
    const render = () => {
      list.innerHTML = items.map((it, i) => `<li role="option" aria-selected="${i === active}" data-i="${i}">` +
        `<b>${esc(it.label)}</b><span>${esc(it.hint || "")}</span></li>`).join("");
      list.hidden = !items.length;
    };
    input.addEventListener("input", async () => {
      const q = input.value.trim().toLowerCase().replace(/ county$/, "").replace(/,/g, " ").replace(/\s+/g, " ");
      active = 0;
      if (/^\d{5}$/.test(q)) {
        const zip = await data("zip.json");
        const id = zip[q];
        items = id && counties[id] ? [{ id, label: `${counties[id].n}, ${counties[id].s}`, hint: `ZIP ${q}` }]
          : [{ id: null, label: "No county found for that ZIP code", hint: "" }];
      } else if (q.length >= 2) {
        const words = q.split(" ");
        items = all.filter(c => words.every(w => c.key.includes(w)))
          .sort((a, b) => (a.key.startsWith(q) ? 0 : 1) - (b.key.startsWith(q) ? 0 : 1) || a.key.localeCompare(b.key))
          .slice(0, 8).map(c => ({ id: c.id, label: `${c.name}, ${c.st}`, hint: "" }));
        if (!items.length) items = [{ id: null, label: "No county by that name", hint: "try a ZIP code" }];
      } else items = [];
      render();
    });
    const pick = i => {
      const it = items[i];
      if (!it || !it.id) return;
      input.value = it.label; items = []; render(); onPick(it.id);
    };
    input.addEventListener("keydown", e => {
      if (list.hidden) return;
      if (e.key === "ArrowDown") { active = Math.min(active + 1, items.length - 1); render(); e.preventDefault(); }
      else if (e.key === "ArrowUp") { active = Math.max(active - 1, 0); render(); e.preventDefault(); }
      else if (e.key === "Enter") { pick(active); e.preventDefault(); }
      else if (e.key === "Escape") { items = []; render(); }
    });
    list.addEventListener("mousedown", e => { const li = e.target.closest("li"); if (li) { pick(+li.dataset.i); e.preventDefault(); } });
    input.addEventListener("blur", () => setTimeout(() => { list.hidden = true; }, 150));
  }

  const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ---------- the county card ----------
  function card(id, county, L, { link = true } = {}) {
    const f = L.byId.get(id);
    const name = `${esc(county.n)}, ${esc(county.s)}`;
    const head = link ? `<a href="${countyUrl(id)}">${name}</a>` : name;
    if (!f) {
      return `<p class="where">${head}</p><p class="when">No forecast for this county this hour (no weather for it in
        the newest HRRR runs).</p>`;
    }
    const lv = levelOf(f.p, L.levels);
    const drivers = (L.drivers[id] || []).map(([g]) => `<li>${esc(g)}</li>`).join("");
    return `<p class="where">${head}</p>
      <p class="when">New outages ${esc(windowText(L.latest, county.tz))}${L.sample ? " · sample" : ` · updated ${ago(L.latest.generated_at)}`}</p>
      <div><span class="big num">${pct(f.p)}</span><span class="level ${lv ? lv.name.toLowerCase() : ""}">${lv ? esc(lv.name) : "Low"}</span></div>
      <p class="range">Chance of a new outage reaching 5% of the ${county.cust.toLocaleString()} customers the outage record tracks here.
        The five weather runs give ${pct(f.low)} to ${pct(f.high)}.</p>
      ${drivers ? `<p class="kicker" style="margin:0 0 6px">Raising the chance</p><ul class="drivers">${drivers}</ul>` : ""}
      ${county.unreliable ? `<p class="flag"><strong>Outage record unreliable.</strong> This county's outage reports
        show outages in many calm hours, so the model learned to expect them: its chance here runs high in any weather.</p>` : ""}
      <div class="actions">
        ${link ? `<a class="btn primary" href="${countyUrl(id)}">County page</a>` : ""}
        <a class="btn" href="${feedUrl(id)}" title="RSS feed of this county's alerts">Alerts (RSS)</a>
      </div>`;
  }

  // ---------- theme ----------
  function theme(button) {
    if (!button) return;
    const dark = () => (document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")) === "dark";
    const label = () => { button.textContent = dark() ? "☀" : "☾"; button.title = dark() ? "Light mode" : "Dark mode"; };
    button.addEventListener("click", () => {
      document.documentElement.dataset.theme = dark() ? "light" : "dark";
      try { localStorage.setItem("theme", document.documentElement.dataset.theme); } catch (e) { /* private window */ }
      label();
    });
    label();
  }

  function banner(el, L) {
    if (!el) return;
    if (L.sample) {
      el.innerHTML = `<strong>Sample forecast.</strong> The hourly USA feed hasn't started yet, so this page shows a
        past storm hour run through the live code: ${esc(L.latest.decision_hour.replace("T", " ").replace(":00Z", ":00 UTC"))}.`;
      el.hidden = false;
    } else el.hidden = true;
  }

  return { ROOT, LIVE, data, live, levelOf, fill, legendItems, pct, slug, countyUrl, feedUrl, windowText, ago,
    parseIso, drawMap, tip, search, card, theme, banner, esc };
})();
