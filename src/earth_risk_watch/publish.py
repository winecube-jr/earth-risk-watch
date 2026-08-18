"""Static, dependency-light publication products."""

import json
from pathlib import Path

import geopandas as gpd


def build_risk_map(screen_path: Path, sampling_points_path: Path, output: Path) -> Path:
    """Build a self-contained data page using Leaflet loaded from its CDN."""
    screen = json.loads(screen_path.read_text(encoding="utf-8"))
    points = json.loads(sampling_points_path.read_text(encoding="utf-8"))
    frame = gpd.read_file(screen_path)
    min_x, min_y, max_x, max_y = frame.total_bounds
    template = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Earth Risk Watch — Pilot pressure screen</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
        integrity="sha256-p4NxAoJBhIINfQ3ynhLZwJMAfMZ7v8Lw3wA+QKf94iM=" crossorigin="">
  <style>
    html, body, #map { height: 100%; margin: 0; font-family: system-ui, sans-serif; }
    .panel { background: white; padding: 10px 12px; border-radius: 4px;
             box-shadow: 0 1px 6px #0005; max-width: 320px; line-height: 1.35; }
    .notice { color: #7f2704; font-weight: 700; }
    .legend i { width: 16px; height: 16px; float: left; margin-right: 7px; opacity: .8; }
    .legend div { clear: both; margin-top: 4px; }
  </style>
</head>
<body><div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script>
const screen = __SCREEN__;
const points = __POINTS__;
const map = L.map('map').fitBounds([[__MIN_Y__, __MIN_X__], [__MAX_Y__, __MAX_X__]]);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 18, attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);
const colours = {'very low':'#ffffcc', low:'#a1dab4', moderate:'#41b6c4',
                 high:'#2c7fb8', 'very high':'#253494'};
function value(v) { return Number(v).toFixed(1); }
function popup(f) {
  const p = f.properties;
  return `<b>${p.cell_id}</b><br>Relative score: ${value(p.screening_score)} (${p.screening_band})`
    + `<br>Sediment pressure: ${value(p.sediment_pressure)}`
    + `<br>Runoff susceptibility: ${value(p.runoff_susceptibility)}`
    + `<br>Condition stress: ${value(p.condition_stress)}`
    + `<br>Top-quintile frequency: ${value(p.top_quintile_frequency * 100)}%`
    + `<br>Weight sensitivity SD: ${value(p.weight_sensitivity_std)}`
    + `<br>Nearest 2024 monitoring: ${value(p.monitoring_distance_km)} km`;
}
L.geoJSON(screen, {style: f => ({color:'#444', weight:.5, fillOpacity:.72,
  fillColor: colours[f.properties.screening_band]}), onEachFeature: (f,l) => l.bindPopup(popup(f))
}).addTo(map);
L.geoJSON(points, {pointToLayer: (f,ll) => L.circleMarker(ll, {radius:3, color:'#111',
  fillColor:'#fff', fillOpacity:.9}), onEachFeature: (f,l) => l.bindTooltip(f.properties.name ||
  f.properties.notation)}).addTo(map);
const info = L.control({position:'topright'}); info.onAdd = () => { const d=L.DomUtil.create('div','panel');
  d.innerHTML='<b>Earth Risk Watch pilot</b><br><span class="notice">Exploratory relative screen — not a validated prediction.</span><br>Click a cell for evidence and sensitivity.'; return d; }; info.addTo(map);
const legend=L.control({position:'bottomright'}); legend.onAdd=()=>{const d=L.DomUtil.create('div','panel legend');
  d.innerHTML='<b>Relative screening band</b>'; for(const k of ['very low','low','moderate','high','very high'])
  d.innerHTML += `<div><i style="background:${colours[k]}"></i>${k}</div>`; return d;}; legend.addTo(map);
</script></body></html>
"""
    html = (
        template.replace("__SCREEN__", json.dumps(screen, separators=(",", ":")))
        .replace("__POINTS__", json.dumps(points, separators=(",", ":")))
        .replace("__MIN_X__", str(min_x))
        .replace("__MIN_Y__", str(min_y))
        .replace("__MAX_X__", str(max_x))
        .replace("__MAX_Y__", str(max_y))
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return output
