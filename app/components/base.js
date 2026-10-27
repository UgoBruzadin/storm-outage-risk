// Shared by the dashboard's D3 components (the same drawing code as the story page,
// site/index.html). Each component gets DATA (its payload) and THEME ("light" | "dark").
const REDUCE = matchMedia("(prefers-reduced-motion: reduce)").matches;
const DARK = THEME === "dark";
document.documentElement.dataset.theme = THEME;
// sequential ramps: near zero recedes toward the surface in both themes
const RAMPS = {
  light: { blue: ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"],
           orange: ["#fde0d2", "#f8b998", "#f2925f", "#eb6834", "#c84f1f", "#9c3c16", "#6e2a0f"],
           diverging: ["#184f95", "#6da7ec", "#f0efec", "#f2925f", "#9c3c16"] },
  dark: { blue: ["#1f2b3a", "#1c3a63", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#b7d3f6"],
          orange: ["#33231d", "#5c2a14", "#8a3a18", "#c84f1f", "#eb6834", "#f2925f", "#fbd2bf"],
          diverging: ["#6da7ec", "#256abf", "#383835", "#c84f1f", "#f2925f"] },
};
const ramp = name => RAMPS[DARK ? "dark" : "light"][name];
const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const fmt = d3.format(",");
const pct = d3.format(".0%");
const abbr = s => (s === "Missouri" ? "MO" : "IL");

const tip = document.querySelector(".tip");
function showTip(event, html) {
  tip.innerHTML = html; tip.style.opacity = 1;
  const x = Math.min(event.clientX + 14, innerWidth - tip.offsetWidth - 8);
  const y = Math.min(event.clientY + 14, innerHeight - tip.offsetHeight - 8);
  tip.style.left = x + "px"; tip.style.top = y + "px";
}
const hideTip = () => { tip.style.opacity = 0; };

const FEATURES = DATA.counties.map(c => ({ type: "Feature", id: c.id, properties: c, geometry: c.geometry }));
const COLLECTION = { type: "FeatureCollection", features: FEATURES };

function countyMap(svg, width, height) {
  const projection = d3.geoConicEqualArea().parallels([36.5, 42]).rotate([91.5, 0]).fitSize([width, height], COLLECTION);
  const path = d3.geoPath(projection);
  const g = svg.append("g");
  const counties = g.selectAll("path.county").data(FEATURES).join("path").attr("class", "county").attr("d", path);
  g.selectAll("path.state").data(DATA.states).join("path").attr("class", "state").attr("d", d => path(d));
  return counties;
}

function legend(svg, x, y, w, colors, domain, ticks, format, title) {
  const id = "g" + Math.random().toString(36).slice(2);
  svg.append("defs").append("linearGradient").attr("id", id).selectAll("stop").data(colors).join("stop")
    .attr("offset", (d, i, all) => i / (all.length - 1)).attr("stop-color", d => d);
  const g = svg.append("g").attr("class", "legend").attr("transform", `translate(${x},${y})`);
  g.append("rect").attr("width", w).attr("height", 8).attr("rx", 2).attr("fill", `url(#${id})`);
  const s = d3.scaleLinear().domain(domain).range([0, w]);
  g.selectAll("text.t").data(ticks).join("text").attr("class", "t").attr("x", d => s(d))
    .attr("y", 22).attr("text-anchor", "middle").text(format);
  g.append("text").attr("x", 0).attr("y", -6).text(title);
}
