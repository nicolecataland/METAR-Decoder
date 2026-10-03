#!/usr/bin/env python3
"""Generate data/stations.json from the Aviation Weather Center daily station cache."""
from __future__ import annotations
import gzip, json, math, sys, urllib.request
from pathlib import Path
from timezonefinder import TimezoneFinder

AWC_URL = "https://aviationweather.gov/data/cache/stations.cache.json.gz"
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "stations.json"
USER_AGENT = "METAR-Decoder-Station-Updater/3.0 (+GitHub Pages static site)"

def clean(v):
    if v is None: return None
    s=str(v).strip()
    return s or None

def number(v):
    try:
        n=float(v)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError): return None

def first(d,*keys):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None

def valid_coords(lat,lon):
    return lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180

def download():
    print(f"Downloading {AWC_URL}")
    req=urllib.request.Request(AWC_URL,headers={"User-Agent":USER_AGENT,"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=120) as r:
        raw=r.read()
    print(f"Downloaded {len(raw)/1024:.1f} KiB")
    try: return gzip.decompress(raw)
    except gzip.BadGzipFile: return raw

def records_from(payload):
    if isinstance(payload,list): return payload
    if isinstance(payload,dict):
        # Ordinary wrappers
        for key in ("data","stations","station"):
            if isinstance(payload.get(key),list): return payload[key]
        # GeoJSON FeatureCollection
        if payload.get("type")=="FeatureCollection" and isinstance(payload.get("features"),list):
            return payload["features"]
    raise ValueError("Unrecognized AWC station-cache JSON structure")

def flatten(rec):
    if not isinstance(rec,dict): return None
    if rec.get("type")!="Feature": return rec
    out=dict(rec.get("properties") or {})
    geom=rec.get("geometry") or {}
    coords=geom.get("coordinates")
    if isinstance(coords,(list,tuple)) and len(coords)>=2:
        out.setdefault("lon",coords[0]); out.setdefault("lat",coords[1])
    return out

def normalize(rec,tf):
    rec=flatten(rec)
    if not rec: return None
    sid=clean(first(rec,"icaoId","icao","stationId","station_id","id"))
    if not sid: return None
    sid=sid.upper()
    lat=number(first(rec,"lat","latitude")); lon=number(first(rec,"lon","lng","longitude"))
    if not valid_coords(lat,lon): lat=lon=None
    tz=None
    if lat is not None:
        try: tz=tf.timezone_at(lat=lat,lng=lon)
        except (ValueError,TypeError): pass
    elev=number(first(rec,"elev","elevation","elevationM"))
    # AWC station-info elevation is metres; preserve an explicit feet field if a future schema supplies one.
    elev_ft=number(first(rec,"elevationFt","elevFt"))
    if elev_ft is None and elev is not None and elev > -500: elev_ft=round(elev*3.28084)
    name=clean(first(rec,"site","name","stationName","siteName"))
    state=clean(first(rec,"state","region")); country=clean(first(rec,"country","countryCode"))
    city=clean(first(rec,"city"))
    out={"name":name,"city":city,"region":state,"country":country,"timezone":tz,
         "latitude":round(lat,6) if lat is not None else None,
         "longitude":round(lon,6) if lon is not None else None,
         "elevationFt":int(round(elev_ft)) if elev_ft is not None else None}
    # Retain useful identifiers when supplied by AWC.
    for src,dst in (("iataId","iataId"),("faaId","faaId"),("wmoId","wmoId"),("siteType","siteType")):
        v=clean(rec.get(src))
        if v: out[dst]=v
    return sid,out

def main():
    print("="*68); print("METAR Decoder — Station Database Updater"); print("="*68)
    try:
        payload=json.loads(download().decode("utf-8-sig"))
        records=records_from(payload)
    except Exception as e:
        print(f"ERROR: {e}",file=sys.stderr); return 1
    print(f"AWC records: {len(records):,}")
    tf=TimezoneFinder(in_memory=True)
    stations={}; skipped=bad_coords=no_tz=0
    for i,rec in enumerate(records,1):
        item=normalize(rec,tf)
        if item is None: skipped+=1; continue
        sid,station=item
        if station["latitude"] is None: bad_coords+=1
        if station["timezone"] is None: no_tz+=1
        stations[sid]=station
        # Add common FAA aliases only when unambiguous and not already present.
        faa=station.get("faaId")
        if faa and len(faa)==3 and station.get("country") in ("US","USA"):
            stations.setdefault(faa.upper(),station)
            stations.setdefault(("K"+faa).upper(),station)
        if i%5000==0: print(f"Processed {i:,}/{len(records):,}")
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(stations,ensure_ascii=False,separators=(",",":"),sort_keys=True)+"\n",encoding="utf-8")
    print(f"Stations/aliases written: {len(stations):,}")
    print(f"Skipped records: {skipped:,}; invalid coordinates: {bad_coords:,}; no timezone: {no_tz:,}")
    print(f"Output: {OUTPUT} ({OUTPUT.stat().st_size/1024/1024:.2f} MiB)")
    return 0

if __name__=="__main__": raise SystemExit(main())
