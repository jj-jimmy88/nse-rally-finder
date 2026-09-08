"""Build index.html (GitHub Pages) from the template + live data."""
import json, os, re
R=os.path.dirname(os.path.abspath(__file__)); D=os.path.join(R,"data")
S=json.load(open(os.path.join(D,"signals.json"))); L=json.load(open(os.path.join(D,"latest.json"))); H=json.load(open(os.path.join(D,"history.json")))
t=open(os.path.join(R,"template.html")).read()
t=t.replace("/*__SIGNALS__*/","const SIG="+json.dumps(S)+";\nconst LATEST="+json.dumps(L)+";")
t=re.sub(r"const DATA=\[.*?\];\n","const DATA="+json.dumps(H)+";\n",t,count=1,flags=re.S)
open(os.path.join(R,"index.html"),"w").write(t); print("index.html written",len(t))
