#!/usr/bin/env python3
"""Animated geography-documentary proof of concept: Europe-to-Asia via Suez."""
import argparse,json,math,subprocess,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
W,H,FPS=1280,720,15
URL="https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_land.geojson"
ROUTE=[(4.48,51.92),(-5.6,36),(12,34),(32.55,29.97),(43,12),(55,12),(80,6),(103.82,1.3)]
SCENES=[
("THE WORLD'S MOST IMPORTANT SHORTCUT","A shipping route that reshaped global trade",[-20,-5,125,72],.28,"A journey between Europe and Asia can cross half the world."),
("THE SUEZ CANAL","A narrow passage between the Mediterranean and Red Sea",[25,22,42,39],.56,"The canal cuts thousands of kilometres from the journey."),
("ONE ROUTE. GLOBAL CONSEQUENCES.","Trade, energy and supply chains converge here",[-5,-2,115,58],1.,"When this corridor is disrupted, the effects travel worldwide.")]
NARRATION=("A vast share of global trade moves by sea. Ships travelling between Europe and Asia once faced a long journey around the southern tip of Africa. The Suez Canal created a much shorter passage, linking the Mediterranean Sea with the Red Sea. That narrow corridor connects continents, supply chains and energy markets. When traffic is interrupted, the impact can be felt far beyond Egypt.")
def ft(n,b=False):
 p=Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if b else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
 return ImageFont.truetype(str(p),n) if p.exists() else ImageFont.load_default()
def xy(lon,lat,b):
 x0,y0,x1,y1=b; return int((lon-x0)/(x1-x0)*W),int((y1-lat)/(y1-y0)*H)
def rings(g):
 return g["coordinates"] if g["type"]=="Polygon" else [r for p in g["coordinates"] for r in p] if g["type"]=="MultiPolygon" else []
def frame(land,s,idx,sec):
 title,sub,target,route_end,caption=s; start=[-20,-5,125,72] if idx==0 else target
 t=min(1,sec/1.8); t=t*t*(3-2*t); b=[start[i]+(target[i]-start[i])*t for i in range(4)]
 im=Image.new("RGB",(W,H),(7,18,35)); d=ImageDraw.Draw(im,"RGBA")
 for lon in range(math.ceil(b[0]/10)*10,int(b[2])+1,10):
  x,_=xy(lon,b[1],b); d.line((x,0,x,H),fill=(58,91,119,55))
 for lat in range(math.ceil(b[1]/10)*10,int(b[3])+1,10):
  _,y=xy(b[0],lat,b); d.line((0,y,W,y),fill=(58,91,119,55))
 for f in land["features"]:
  for r in rings(f["geometry"]):
   pts=[xy(p[0],p[1],b) for p in r if b[0]-5<=p[0]<=b[2]+5 and b[1]-5<=p[1]<=b[3]+5]
   if len(pts)>=3: d.polygon(pts,fill=(35,69,79,255)); d.line(pts+[pts[0]],fill=(83,139,139,180),width=2)
 prog=route_end*min(1,max(0,(sec-1.2)/10)); seg=[]
 for i in range(1,len(ROUTE)):
  a=(i-1)/(len(ROUTE)-1); z=i/(len(ROUTE)-1)
  if prog<=a: break
  q=min(1,(prog-a)/(z-a)); p0,p1=ROUTE[i-1],ROUTE[i]
  seg.append((xy(*p0,b),xy(p0[0]+(p1[0]-p0[0])*q,p0[1]+(p1[1]-p0[1])*q,b)))
  if q<1: break
 for p0,p1 in seg: d.line((p0,p1),fill=(15,211,220,65),width=15); d.line((p0,p1),fill=(34,231,235,245),width=4)
 if seg:
  x,y=seg[-1][1]; d.ellipse((x-10,y-10,x+10,y+10),fill=(255,209,102,255),outline="white",width=3)
 for label,(lon,lat) in [("ROTTERDAM",ROUTE[0]),("SUEZ CANAL",ROUTE[3]),("SINGAPORE",ROUTE[-1])]:
  if b[0]<=lon<=b[2] and b[1]<=lat<=b[3]:
   x,y=xy(lon,lat,b); d.ellipse((x-5,y-5,x+5,y+5),fill=(255,209,102,255)); d.text((x+12,y-24),label,font=ft(17,True),fill="white",stroke_width=2,stroke_fill=(7,18,35))
 d.rectangle((0,0,W,118),fill=(4,13,27,225)); d.text((62,32),title,font=ft(31,True),fill=(246,249,252)); d.text((64,80),sub,font=ft(18),fill=(130,220,224))
 d.rectangle((0,H-116,W,H),fill=(4,13,27,225)); d.text((62,H-82),caption,font=ft(22),fill=(235,241,247)); d.text((W-180,H-42),f"FIELD NOTES / 0{idx+1}",font=ft(14,True),fill=(126,163,181))
 return im
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--output",default="output/suez-canal-documentary.mp4"); ap.add_argument("--seconds",type=int,default=36); a=ap.parse_args()
 out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); cache=out.parent/"ne_110m_land.geojson"
 if not cache.exists():
  req=urllib.request.Request(URL,headers={"User-Agent":"geo-motion-prototype"})
  with urllib.request.urlopen(req,timeout=45) as r: cache.write_bytes(r.read())
 land=json.loads(cache.read_text()); per=max(1,a.seconds//3*FPS); silent=out.with_suffix(".silent.mp4")
 cmd=["ffmpeg","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-an","-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p",str(silent)]
 p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
 for i,s in enumerate(SCENES):
  for n in range(per): p.stdin.write(frame(land,s,i,n/FPS).tobytes())
  print(f"Rendered scene {i+1}/3 ({per} frames)",flush=True)
 p.stdin.close(); err=p.stderr.read().decode("utf-8","replace"); rc=p.wait()
 if rc: raise RuntimeError(err[-2500:])
 wav=out.with_suffix(".wav")
 try:
  subprocess.run(["espeak-ng","-s","145","-v","en-us","-w",str(wav),NARRATION],check=True,timeout=45)
  subprocess.run(["ffmpeg","-y","-i",str(silent),"-i",str(wav),"-c:v","copy","-c:a","aac","-b:a","160k","-shortest",str(out)],check=True,timeout=90,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 except (FileNotFoundError,subprocess.SubprocessError):
  subprocess.run(["ffmpeg","-y","-i",str(silent),"-c:v","copy","-an",str(out)],check=True,timeout=90)
  print("WARNING: narration unavailable; rendered without audio",flush=True)
 silent.unlink(missing_ok=True); wav.unlink(missing_ok=True)
 v=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_name,width,height","-of","json",str(out)],capture_output=True,text=True,check=True)
 print("OUTPUT_VALIDATION "+v.stdout,flush=True); print(f"Created {out} ({out.stat().st_size} bytes)",flush=True)
if __name__=="__main__": main()
