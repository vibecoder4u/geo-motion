#!/usr/bin/env python3
"""Geo Motion v2: clipped, projected and editorially composed geographic documentary maps."""
import argparse, json, math, subprocess, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import shape, box, Polygon, MultiPolygon, GeometryCollection, LineString
from pyproj import Transformer

W, H, FPS = 1280, 720, 24
LAND_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_land.geojson"
ROUTE = [(4.48,51.92),(-5.6,36.0),(12.0,34.0),(32.55,29.97),(43.0,12.0),(55.0,12.0),(80.0,6.0),(103.82,1.3)]
SCENES = [
 {"title":"THE WORLD'S MOST IMPORTANT SHORTCUT","sub":"A narrow passage connects two major oceans","box":[-20,-5,125,72],"focus":"global","caption":"A maritime corridor linking Europe and Asia","stat":"~ 9,000 km","statlabel":"potential distance saved"},
 {"title":"THE SUEZ CANAL","sub":"A man-made passage through the Isthmus of Suez","box":[25,22,42,39],"focus":"regional","caption":"The Mediterranean meets the Red Sea","stat":"193 km","statlabel":"canal length"},
 {"title":"WHEN THE ROUTE STOPS","sub":"A disruption here can ripple across global supply chains","box":[-5,-2,115,58],"focus":"global","caption":"One chokepoint. Consequences across continents.","stat":"12%","statlabel":"illustrative share of global trade"}
]
NARRATION = ("Look at the distance between Europe and Asia. For centuries, ships travelling between these markets had to take the long route around the southern tip of Africa. The Suez Canal changed that geography. Cut through Egypt, it links the Mediterranean Sea to the Red Sea and creates a direct passage between the Mediterranean and the Indian Ocean. The canal is only one narrow corridor, but it sits inside a vast network of ports, ships, factories and consumers. When traffic through this passage is interrupted, vessels may divert thousands of kilometres. The extra distance means more time, fuel and pressure on supply chains around the world. This is why a thin line on the map can matter to the entire planet.")
def font(size,bold=False):
 p=Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
 return ImageFont.truetype(str(p),size) if p.exists() else ImageFont.load_default()
def smooth(t):
 t=max(0,min(1,t)); return t*t*(3-2*t)
def project_factory(bbox,focus):
 crs="EPSG:8857" if focus=="global" else "EPSG:3395"
 tr=Transformer.from_crs("EPSG:4326",crs,always_xy=True)
 x0,y0=tr.transform(bbox[0],bbox[1]); x1,y1=tr.transform(bbox[2],bbox[3])
 pad=0.045
 dx=(x1-x0)*pad; dy=(y1-y0)*pad
 x0-=dx; x1+=dx; y0-=dy; y1+=dy
 scale=min(W/(x1-x0),H/(y1-y0))
 ox=(W-(x1-x0)*scale)/2; oy=(H-(y1-y0)*scale)/2
 def xy(lon,lat):
  x,y=tr.transform(lon,lat)
  return (int(ox+(x-x0)*scale),int(H-(oy+(y-y0)*scale)))
 return tr,xy
def polygons(g):
 if isinstance(g,Polygon): return [g]
 if isinstance(g,MultiPolygon): return list(g.geoms)
 if isinstance(g,GeometryCollection):
  return [p for q in g.geoms for p in polygons(q)]
 return []
def draw_gradient(im):
 strip=Image.new("RGB",(1,H))
 strip.putdata([(int(5+3*y/H),int(21+10*y/H),int(39+15*y/H)) for y in range(H)])
 im.paste(strip.resize((W,H)),(0,0))
def render_frame(land,scene,scene_idx,local_t,total_t):
 bbox=scene["box"]; tr,xy=project_factory(bbox,scene["focus"])
 im=Image.new("RGB",(W,H)); draw_gradient(im); d=ImageDraw.Draw(im,"RGBA")
 # Fine geographic graticule.
 for lon in range(math.ceil(bbox[0]/10)*10,int(bbox[2])+1,10):
  pts=[xy(lon,bbox[1]),xy(lon,bbox[3])]
  d.line(pts,fill=(82,137,158,38),width=1)
 for lat in range(math.ceil(bbox[1]/10)*10,int(bbox[3])+1,10):
  d.line([xy(bbox[0],lat),xy(bbox[2],lat)],fill=(82,137,158,38),width=1)
 clip=box(*bbox)
 # True geometry intersection prevents the triangular artefacts in v1.
 for geom in land:
  clipped=geom.intersection(clip)
  for poly in polygons(clipped):
   ext=[xy(x,y) for x,y in poly.exterior.coords]
   if len(ext)>=4:
    d.polygon(ext,fill=(38,78,84,255))
    d.line(ext,fill=(112,165,153,230),width=2,joint="curve")
   for hole in poly.interiors:
    pts=[xy(x,y) for x,y in hole.coords]
    if len(pts)>=4: d.polygon(pts,fill=(8,27,45,255))
 # Route reveal and moving vessel.
 reveal=smooth((local_t-0.10)/0.68)
 line=LineString(ROUTE).intersection(clip)
 if not line.is_empty:
  coords=list(line.coords) if line.geom_type=="LineString" else []
  if len(coords)>1:
   pts=[xy(x,y) for x,y in coords]
   d.line(pts,fill=(12,218,225,65),width=15)
   d.line(pts,fill=(42,230,231,235),width=4)
 # Moving ship along full route, visible where it intersects the current view.
 pos=reveal*(len(ROUTE)-1); k=min(len(ROUTE)-2,int(pos)); frac=pos-k
 a,b=ROUTE[k],ROUTE[k+1]; lon=a[0]+(b[0]-a[0])*frac; lat=a[1]+(b[1]-a[1])*frac
 if bbox[0]<=lon<=bbox[2] and bbox[1]<=lat<=bbox[3]:
  sx,sy=xy(lon,lat); ahead=xy(lon+0.35,lat+0.12); ang=math.atan2(ahead[1]-sy,ahead[0]-sx)
  pts=[]
  for r,off in [(15,0),(-10,2),(-10,-2)]:
   pts.append((sx+math.cos(ang+off)*r,sy+math.sin(ang+off)*r))
  d.polygon(pts,fill=(255,203,112,255),outline=(255,245,220,255))
 # Geographic place labels.
 places=[("ROTTERDAM",4.48,51.92),("SUEZ",32.55,29.97),("SINGAPORE",103.82,1.3),("RED SEA",39,20),("MEDITERRANEAN",18,35)]
 for name,lon,lat in places:
  if bbox[0]<=lon<=bbox[2] and bbox[1]<=lat<=bbox[3]:
   x,y=xy(lon,lat)
   if name in ("RED SEA","MEDITERRANEAN"):
    d.text((x,y),name,font=font(14,True),fill=(130,185,197,185),anchor="mm")
   else:
    d.ellipse((x-5,y-5,x+5,y+5),fill=(255,207,128,255),outline=(7,24,39,255),width=2)
    d.text((x+11,y-19),name,font=font(15,True),fill=(247,250,249,255),stroke_width=2,stroke_fill=(5,20,34,255))
 # Editorial title and information panels.
 d.rectangle((0,0,W,112),fill=(3,12,25,232))
 d.text((58,27),scene["title"],font=font(29,True),fill=(247,249,250,255))
 d.text((60,73),scene["sub"],font=font(17),fill=(143,208,211,255))
 # Stat card.
 d.rounded_rectangle((W-270,H-156,W-54,H-54),radius=12,fill=(4,17,31,225),outline=(75,151,158,160),width=1)
 d.text((W-246,H-139),scene["stat"],font=font(29,True),fill=(255,211,137,255))
 d.text((W-246,H-95),scene["statlabel"],font=font(12),fill=(190,211,219,255))
 d.rectangle((0,H-76,W,H),fill=(3,12,25,232))
 d.text((58,H-52),scene["caption"],font=font(18),fill=(239,244,246,255))
 d.text((W-170,H-50),f"GEOGRAPHY  /  0{scene_idx+1}",font=font(12,True),fill=(119,174,185,255))
 # Scene progress marker.
 d.rounded_rectangle((58,126,58+int(310*local_t),131),radius=2,fill=(41,214,220,230))
 return im
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--output",default="output/suez-canal-documentary.mp4"); ap.add_argument("--seconds",type=int,default=60); a=ap.parse_args()
 if a.seconds<15: raise ValueError("--seconds must be at least 15")
 out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); cache=out.parent/"ne_50m_land.geojson"
 if not cache.exists():
  req=urllib.request.Request(LAND_URL,headers={"User-Agent":"geo-motion/2.0"})
  with urllib.request.urlopen(req,timeout=90) as r: cache.write_bytes(r.read())
 raw=json.loads(cache.read_text()); land=[shape(f["geometry"]) for f in raw["features"] if f.get("geometry")]
 silent=out.with_suffix(".silent.mp4")
 cmd=["ffmpeg","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-an","-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",str(silent)]
 p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
 frames=a.seconds*FPS
 for n in range(frames):
  idx=min(2,int(n/frames*3)); local=(n/frames*3)-idx
  p.stdin.write(render_frame(land,SCENES[idx],idx,local,n/frames).tobytes())
  if n%(FPS*5)==0: print(f"Rendering {n//FPS:02d}/{a.seconds}s",flush=True)
 p.stdin.close(); err=p.stderr.read().decode("utf-8","replace"); rc=p.wait()
 if rc: raise RuntimeError(err[-3000:])
 wav=out.with_suffix(".wav")
 try:
  subprocess.run(["espeak-ng","-s","142","-v","en-us","-w",str(wav),NARRATION],check=True,timeout=90)
  subprocess.run(["ffmpeg","-y","-i",str(silent),"-i",str(wav),"-c:v","copy","-c:a","aac","-b:a","160k","-af","apad","-t",str(a.seconds),str(out)],check=True,timeout=180,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 except (FileNotFoundError,subprocess.SubprocessError):
  subprocess.run(["ffmpeg","-y","-i",str(silent),"-t",str(a.seconds),"-c:v","copy","-an",str(out)],check=True,timeout=180)
  print("WARNING: narration unavailable; rendered without audio",flush=True)
 silent.unlink(missing_ok=True); wav.unlink(missing_ok=True)
 probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_name,width,height,r_frame_rate","-of","json",str(out)],capture_output=True,text=True,check=True)
 print("OUTPUT_VALIDATION "+probe.stdout,flush=True)
 print(f"Created {out} ({out.stat().st_size} bytes)",flush=True)
if __name__=="__main__": main()
