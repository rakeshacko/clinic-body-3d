"""
anny_server.py — live Anny parametric-body preview backend.

Loads the Anny model once (~30s, cached after first run) and serves:
  GET /            -> the three.js slider viewer (preview/anny_preview.html)
  GET /labels      -> {phenotypes:[...], locals:[...], vertexCount:N}
  GET /faces       -> static triangle indices (Int32 binary)
  GET /mesh?k=v..  -> skinned vertices for the given params (Float32 binary), ~40ms

Run in the Anny venv:  /tmp/annyenv/bin/python asset-pipeline-v2/anny_server.py
Then open http://localhost:8765/
"""
import os, json, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import numpy as np, torch, anny

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, "preview", "anny_preview.html")
PORT = 8765

print("anny: loading model (first run downloads assets, ~30s)…", flush=True)
model = anny.create_fullbody_model(rig="default", topology="default", local_changes=True)
model = model.to(dtype=torch.float32).eval()
FACES = model.get_triangular_faces().detach().cpu().numpy().astype(np.int32)  # quads -> tris for WebGL
PHENO = list(model.phenotype_labels)
LOCALS = list(model.local_change_labels)
_lock = threading.Lock()
with torch.no_grad():
    V = model.forward(phenotype_kwargs={k: 0.5 for k in PHENO})["vertices"].shape[1]
print(f"anny: ready  V={V}  F={len(FACES)}  phenotypes={PHENO}  locals={len(LOCALS)}", flush=True)

def vertices(phenos, locals_):
    pk = {k: 0.5 for k in PHENO}; pk.update({k: float(v) for k, v in phenos.items() if k in PHENO})
    lk = {k: 0.0 for k in LOCALS}; lk.update({k: float(v) for k, v in locals_.items() if k in LOCALS})
    with _lock, torch.no_grad():
        out = model.forward(phenotype_kwargs=pk, local_changes_kwargs=lk)
    return out["vertices"].squeeze(0).detach().cpu().numpy().astype(np.float32)

class H(BaseHTTPRequestHandler):
    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        try:
            if u.path in ("/", "/index.html"):
                with open(HTML, "rb") as f: self._send(200, "text/html; charset=utf-8", f.read())
            elif u.path == "/labels":
                self._send(200, "application/json",
                           json.dumps({"phenotypes": PHENO, "locals": LOCALS, "vertexCount": V}).encode())
            elif u.path == "/faces":
                self._send(200, "application/octet-stream", FACES.tobytes())
            elif u.path == "/members":
                with open(os.path.join(HERE, "preview", "dxa_members.json"), "rb") as f:
                    self._send(200, "application/json", f.read())
            elif u.path == "/fitted":
                with open(os.path.join(HERE, "preview", "fitted_params.json"), "rb") as f:
                    self._send(200, "application/json", f.read())
            elif u.path == "/mesh":
                ph = {k: v[0] for k, v in q.items() if k in PHENO}
                lo = {k: v[0] for k, v in q.items() if k in LOCALS}
                self._send(200, "application/octet-stream", vertices(ph, lo).tobytes())
            else:
                self._send(404, "text/plain", b"not found")
        except Exception as e:
            self._send(500, "text/plain", str(e).encode())
    def log_message(self, *a): pass

print(f"anny: serving http://localhost:{PORT}/", flush=True)
ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
