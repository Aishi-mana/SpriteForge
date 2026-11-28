"""Real Chromium smoke checks with deterministic mocked local-engine responses.
Run explicitly: python tests/browser_smoke.py
Install once: python -m pip install playwright && python -m playwright install chromium
No model downloads, GPU, or live project writes.
"""
import base64, json, threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from functools import partial
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
PNG="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
JOINTS={"head":[0,0],"neck":[0,0],"hips":[0,0]}
RESULT={"sprite":PNG,"info":{"size":[1,1],"seed":123}}
JOB={"id":"smoke","kind":"generate","params":{"kind":"sprite","prompt":"fixture"},"results":[RESULT],"images":{},"note":"","status":"done","created":1700000000}
class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def main():
    server=ThreadingHTTPServer(("127.0.0.1",0),partial(Handler,directory=str(ROOT/"ui")))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            page=browser.new_page(viewport={"width":1440,"height":1000})
            errors=[];requests=[]
            page.on("pageerror",lambda e:errors.append(str(e)))
            def route(r):
                url=r.request.url.split("/api/",1)[1].split("?",1)[0]
                requests.append(url)
                data={"state":{"gpu":None,"models_dir":"","models_dir_ok":False,"checkpoints":[],"loras":[],"palettes":[]},"queue":{"jobs":[],"paused":False},"history":{"jobs":[{"id":"smoke","thumb":PNG,"status":"done","kind":"generate","prompt":"fixture","created":1700000000,"n_results":1}],"total":1},"jobs/smoke":JOB,"projects":{"projects":[]},"full-frame/video/models":{"models":[]}}.get(url)
                if url=="full-frame/validate":data=r.request.post_data_json
                if url=="rig/autoplace":
                    r.fulfill(status=400,json={"detail":"Fixture rig rejected"});return
                r.fulfill(status=200,json=data if data is not None else {})
            page.route("**/api/**",route)
            page.goto(f"http://127.0.0.1:{server.server_port}/index.html")
            page.locator("#t9").click()
            page.locator("#hgrid img").first.click()
            assert page.locator("#hres [data-a=anim]").is_visible()
            assert not page.locator("#hres [data-a=alpha]").is_visible()
            page.locator("#hres .sf62resultMore summary").click()
            assert page.locator("#hres [data-a=alpha]").is_visible()
            print("ok  advanced result actions expand on demand")
            page.locator("#hres [data-a=anim]").click()
            page.wait_for_function("mode===4 && document.getElementById('status').textContent.includes('Fixture rig rejected')")
            assert "rig/autoplace" in requests
            print("ok  queue history to rig, backend error surfaced")
            page.locator("#t9").click()
            page.locator("#hgrid img").first.click()
            page.locator("#hres [data-a=fullframe]").click()
            page.wait_for_function("mode===20 && FF.doc.reference && !FF.busy")
            assert page.evaluate("FF.doc.reference")==PNG
            print("ok  queue history to full-frame reference")
            page.evaluate("setAnim('data:image/png;base64,invalid')")
            page.wait_for_function("document.getElementById('status').textContent.includes('Cannot decode')")
            print("ok  image decode failure visible")
            for mode in (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20):
                group=next((i for i,ids in enumerate([[1,2,7],[16,5,8,11,3,6],[20,4,13,14],[18,10],[17,19],[12,15]]) if mode in ids),None)
                if group is not None and page.locator("#nav62g"+str(group)).get_attribute("aria-expanded")!="true":
                    page.locator("#nav62g"+str(group)).click()
                page.locator("#t"+str(mode)).click()
                assert page.evaluate("mode")==mode
            print("ok  all 20 navigation buttons")
            assert not errors,errors
            print("ok  no uncaught browser errors")
            browser.close()
    finally:server.shutdown()
if __name__=="__main__":main()
