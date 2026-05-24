"""
Map Service — fully self-contained HTML maps.

All JS and CSS are INLINED from local npm packages so the map works
when opened as a file:// URL with no CDN dependency.

Map tiles are fetched from OpenStreetMap tile servers at render time
(these load fine from browsers even via file:// due to no CORS restriction on tiles).

Road routing uses OSRM's public API called from the browser JS —
falls back to straight dashed lines when offline.
"""

import os
import base64
import webbrowser
from datetime import datetime
from typing import List

# ── Asset paths ────────────────────────────────────────────────────────────────
_ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
MAPS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")
os.makedirs(MAPS_DIR, exist_ok=True)


def _read_asset(filename: str) -> str:
    path = os.path.join(_ASSETS, filename)
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    return ""


def _img_b64(filename: str) -> str:
    path = os.path.join(_ASSETS, "images", filename)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


def _patch_leaflet_css(css: str) -> str:
    """Replace image url() references in Leaflet CSS with inline base64."""
    imgs = {
        "marker-icon.png":    _img_b64("marker-icon.png"),
        "marker-icon-2x.png": _img_b64("marker-icon-2x.png"),
        "marker-shadow.png":  _img_b64("marker-shadow.png"),
        "layers.png":         _img_b64("layers.png"),
        "layers-2x.png":      _img_b64("layers-2x.png"),
    }
    for fname, b64 in imgs.items():
        if b64:
            css = css.replace(f"url(images/{fname})", f"url(data:image/png;base64,{b64})")
            css = css.replace(f'url("images/{fname}")', f'url(data:image/png;base64,{b64})')
    return css


def _patch_lrm_css(css: str) -> str:
    """Replace LRM icon references with inline base64."""
    icons_b64 = _img_b64("leaflet.routing.icons.png")
    if icons_b64:
        css = css.replace(
            "url(leaflet.routing.icons.png)",
            f"url(data:image/png;base64,{icons_b64})"
        )
        css = css.replace(
            "url('leaflet.routing.icons.png')",
            f"url(data:image/png;base64,{icons_b64})"
        )
    return css


# ── Build shared JS/CSS block (cached after first call) ───────────────────────
_BUNDLE_CACHE: str = ""


def _get_bundle() -> str:
    global _BUNDLE_CACHE
    if _BUNDLE_CACHE:
        return _BUNDLE_CACHE

    leaflet_css = _patch_leaflet_css(_read_asset("leaflet.css"))
    lrm_css     = _patch_lrm_css(_read_asset("leaflet-routing-machine.css"))
    leaflet_js  = _read_asset("leaflet.js")
    lrm_js      = _read_asset("leaflet-routing-machine.js")

    if not leaflet_js:
        # Assets missing — fall back to CDN (won't work from file:// but better than nothing)
        _BUNDLE_CACHE = """
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.js"></script>
"""
    else:
        _BUNDLE_CACHE = f"""<style>
{leaflet_css}
{lrm_css}
</style>
<script>
{leaflet_js}
</script>
<script>
{lrm_js}
</script>"""

    return _BUNDLE_CACHE


# ── Map generators ─────────────────────────────────────────────────────────────

def generate_route_map(
    routes,
    run_id: int,
    best_distance: float,
    open_browser: bool = False,
) -> str:
    """
    Generate a self-contained HTML route map.
    - All JS/CSS inlined — works from file:// with no CDN
    - OSM tiles loaded from browser (work fine via file://)
    - Road routing via OSRM called from browser JS
    - Fallback: dashed straight lines when offline
    """
    if not routes:
        return ""

    lats = [r.latitude for r in routes if r.latitude]
    lons = [r.longitude for r in routes if r.longitude]
    if not lats:
        return ""

    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)

    # Waypoints JS (close loop)
    wp_parts = [f"L.latLng({r.latitude},{r.longitude})" for r in routes if r.latitude]
    if wp_parts:
        wp_parts.append(wp_parts[0])
    waypoints_str = ",\n        ".join(wp_parts)

    # Numbered marker JS
    markers = []
    for idx, stop in enumerate(routes):
        if not stop.latitude or not stop.longitude:
            continue
        color    = "#4CAF50" if idx == 0 else "#00D4FF"
        txt_col  = "#000000"
        label    = str(idx + 1)
        dist_txt = "START / END" if idx == 0 else f"Leg: {stop.distance_from_prev_km:.2f} km"
        name     = (stop.customer_name or "").replace("'", "`").replace('"', '`')
        addr     = (stop.address or "")[:65].replace("'", "`").replace('"', '`')
        popup    = (
            f"<div style='font-family:Segoe UI,sans-serif;min-width:180px'>"
            f"<b style='color:{color}'>Stop #{idx+1}</b><br>"
            f"<b style='font-size:14px'>{name}</b><br>"
            f"<span style='color:#888;font-size:12px'>{addr}</span><br>"
            f"<b style='color:{color}'>{dist_txt}</b></div>"
        )
        markers.append(f"""
(function(){{
  var d=document.createElement('div');
  d.style.cssText='background:{color};color:{txt_col};font-weight:bold;font-size:13px;'
    +'width:30px;height:30px;border-radius:50%;text-align:center;line-height:30px;'
    +'border:2.5px solid white;box-shadow:0 2px 10px rgba(0,0,0,0.55);';
  d.textContent='{label}';
  var icon=L.divIcon({{html:d.outerHTML,iconSize:[30,30],iconAnchor:[15,15],className:''}});
  L.marker([{stop.latitude},{stop.longitude}],{{icon:icon,zIndexOffset:1000}})
    .bindPopup(`{popup}`,{{maxWidth:260}})
    .bindTooltip('#{idx+1}: {name}')
    .addTo(map);
}})();""")

    fallback_coords = "[" + ",".join(f"[{r.latitude},{r.longitude}]" for r in routes if r.latitude) + f",[{routes[0].latitude},{routes[0].longitude}]]"

    bundle = _get_bundle()

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Route Map — Run #{run_id}</title>
{bundle}
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:#080818;font-family:'Segoe UI',Ubuntu,Arial,sans-serif;overflow:hidden;}}
#map{{width:100vw;height:100vh;}}
.panel{{
  position:fixed;bottom:14px;right:14px;z-index:9000;
  background:rgba(8,8,26,0.96);color:#e0e0ff;
  padding:16px 20px;border-radius:14px;
  border:1px solid #1A4A5A;
  min-width:220px;font-size:14px;
  box-shadow:0 6px 32px rgba(0,0,0,0.8);
  backdrop-filter:blur(8px);
}}
.panel h3{{color:#00D4FF;font-size:17px;margin-bottom:12px;font-weight:700;}}
.row{{display:flex;justify-content:space-between;align-items:center;margin:6px 0;font-size:13px;}}
.val{{color:#00D4FF;font-weight:700;font-size:14px;}}
.status{{
  margin-top:12px;padding:8px 12px;border-radius:8px;
  background:#0f0f2a;font-size:12px;color:#888;
  border:1px solid #1E1E4A;line-height:1.5;
}}
.leaflet-routing-container{{display:none!important;}}
.leaflet-control-layers{{font-size:13px;}}
</style>
</head>
<body>
<div id="map"></div>
<div class="panel">
  <h3>&#128666; Route Summary</h3>
  <div class="row"><span>Run ID</span><span class="val">#{run_id}</span></div>
  <div class="row"><span>Total Stops</span><span class="val">{len(routes)}</span></div>
  <div class="row"><span>GA Distance</span><span class="val">{best_distance:.2f} km</span></div>
  <div class="row"><span>Generated</span><span class="val">{datetime.now().strftime('%d %b %H:%M')}</span></div>
  <div class="status" id="status">&#8987; Fetching road route from OSRM...</div>
</div>

<script>
// ── Fix Leaflet default icon paths (inlined — no external images needed) ──────
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({{
  iconRetinaUrl: 'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==',
  iconUrl:       'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==',
  shadowUrl:     'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==',
}});

// ── Map init ─────────────────────────────────────────────────────────────────
var map = L.map('map', {{zoomControl:true, attributionControl:true}})
           .setView([{center_lat},{center_lon}], 12);

var darkTile = L.tileLayer(
  'https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',
  {{attribution:'&copy; <a href="https://openstreetmap.org">OSM</a> &copy; <a href="https://carto.com">CARTO</a>',
    maxZoom:19, subdomains:'abcd'}}
);
var osmTile = L.tileLayer(
  'https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
  {{attribution:'&copy; <a href="https://openstreetmap.org/copyright">OSM contributors</a>',
    maxZoom:19}}
);
var lightTile = L.tileLayer(
  'https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png',
  {{attribution:'&copy; OSM &copy; CARTO', maxZoom:19, subdomains:'abcd'}}
);

darkTile.addTo(map);
L.control.layers({{
  '&#127760; Dark (CARTO)': darkTile,
  '&#9728;&#65039; Light (CARTO)': lightTile,
  '&#128506;&#65039; OpenStreetMap': osmTile
}}, null, {{collapsed: false}}).addTo(map);

// ── Numbered stop markers ────────────────────────────────────────────────────
{''.join(markers)}

// ── Road routing via OSRM (called from browser — works even from file://) ───
try {{
  var routingCtrl = L.Routing.control({{
    waypoints: [
      {waypoints_str}
    ],
    router: new L.Routing.OSRMv1({{
      serviceUrl: 'https://router.project-osrm.org/route/v1',
      profile: 'driving',
      useHints: false
    }}),
    routeWhileDragging: false,
    addWaypoints:       false,
    draggableWaypoints: false,
    showAlternatives:   false,
    fitSelectedRoutes:  true,
    lineOptions: {{
      styles: [
        {{color:'#001820', opacity:0.7, weight:11}},
        {{color:'#00D4FF', opacity:1.0,  weight:5}}
      ],
      extendToWaypoints:    true,
      missingRouteTolerance: 10
    }},
    createMarker: function(){{ return null; }}
  }}).addTo(map);

  routingCtrl.on('routesfound', function(e) {{
    var r   = e.routes[0];
    var km  = (r.summary.totalDistance / 1000).toFixed(2);
    var min = Math.round(r.summary.totalTime / 60);
    document.getElementById('status').innerHTML =
      '&#10003; Road route loaded: <b>' + km + ' km</b> &middot; ~' + min + ' min driving';
    document.getElementById('status').style.color = '#4CAF50';
  }});

  routingCtrl.on('routingerror', function(e) {{
    console.warn('OSRM error:', e);
    _drawFallback();
  }});

}} catch(err) {{
  console.warn('LRM init failed:', err);
  _drawFallback();
}}

function _drawFallback() {{
  document.getElementById('status').innerHTML =
    '&#9888; Offline &mdash; showing straight-line route<br>'
    + '<small>Open with internet to see road routing</small>';
  document.getElementById('status').style.color = '#FFB347';
  var coords = {fallback_coords};
  L.polyline(coords, {{color:'#00D4FF',weight:4,opacity:0.8,dashArray:'12,7'}}).addTo(map);
}}
</script>
</body>
</html>"""

    filename = f"route_run_{run_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(MAPS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    if open_browser:
        webbrowser.open(f"file:///{os.path.abspath(filepath).replace(os.sep, '/')}")

    return filepath


def generate_delivery_overview_map(deliveries, open_browser: bool = False) -> str:
    """Generate overview map of all delivery pins."""
    if not deliveries:
        return ""

    lats = [d.latitude for d in deliveries if d.latitude]
    lons = [d.longitude for d in deliveries if d.longitude]
    if not lats:
        return ""

    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)

    markers = []
    for d in deliveries:
        if d.latitude and d.longitude:
            name = (d.customer_name or "").replace("'", "`").replace('"', '`')
            addr = (d.address or "")[:55].replace("'", "`").replace('"', '`')
            markers.append(
                f"L.circleMarker([{d.latitude},{d.longitude}],"
                f"{{radius:10,color:'#FF6B6B',fillColor:'#FF6B6B',fillOpacity:0.85,weight:2}})"
                f".bindPopup('<b>{d.delivery_id}</b><br><b>{name}</b><br><small style=\"color:#888\">{addr}</small>')"
                f".bindTooltip('{name}').addTo(map);"
            )

    bundle = _get_bundle()

    html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<title>Delivery Locations</title>
{bundle}
<style>
*{{margin:0;padding:0;}} 
#map{{width:100vw;height:100vh;}} 
body{{background:#0d0d1a;overflow:hidden;}}
.leaflet-control-layers{{font-size:13px;}}
</style>
</head><body>
<div id="map"></div>
<script>
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({{
  iconUrl:'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==',
  shadowUrl:'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=='
}});

var map = L.map('map').setView([{center_lat},{center_lon}],11);
var dark  = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',
  {{attribution:'&copy; OSM &copy; CARTO',maxZoom:19,subdomains:'abcd'}});
var osm   = L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
  {{attribution:'&copy; OSM',maxZoom:19}});
dark.addTo(map);
L.control.layers({{'Dark':dark,'Street':osm}}).addTo(map);
{chr(10).join(markers)}
</script></body></html>"""

    filename = f"delivery_overview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(MAPS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    if open_browser:
        webbrowser.open(f"file:///{os.path.abspath(filepath).replace(os.sep, '/')}")

    return filepath
