"""YOLO inference and lane assignment against lane_polygons.json."""
import json
from pathlib import Path
from ultralytics import YOLO
class SmartFlowDetector:
 def __init__(self,weights,polygon_file,confidence=.25):
  self.model=YOLO(weights); self.polygons=json.loads(Path(polygon_file).read_text())["lanes"]; self.confidence=confidence
 def detect(self,image):
  r=self.model.predict(image,conf=self.confidence,verbose=False)[0]; counts={k:{t:0 for t in ("bike","car","bus","truck")} for k in self.polygons}
  for b in r.boxes:
   name=self.model.names[int(b.cls[0])]
   if name not in ("bike","car","bus","truck"): continue
   x,y=map(float,b.xywh[0][:2])
   for lane,poly in self.polygons.items():
    if min(p[0] for p in poly)<=x<=max(p[0] for p in poly) and min(p[1] for p in poly)<=y<=max(p[1] for p in poly): counts[lane][name]+=1; break
  return counts
if __name__=="__main__":
 import argparse
 p=argparse.ArgumentParser(); p.add_argument("image"); p.add_argument("--weights",default="yolov8n.pt"); a=p.parse_args(); d=SmartFlowDetector(a.weights,Path(__file__).resolve().parents[2]/"sumo/lane_polygons.json"); print(json.dumps(d.detect(a.image),indent=2))
