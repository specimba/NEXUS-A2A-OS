
import fitz, os, re
P = r"C:\Users\speci.000\Downloads\ARCHIVIST\PAPERS"
themes = {
 "injection_defense": r"promptshield|secalign|commandsans|injecagent|argus|indirect prompt|signed up for|prompt.?inject|sanitiz|wasp",
 "privilege_access": r"progent|privilege|access control|least.?privilege|capability",
 "verification_validation": r"verification and validation|trustworthiness.*verif|formal verif|runtime monitor",
 "human_oversight": r"oversight|human.?in.?the.?loop|interactive oversight",
 "threat_taxonomy": r"navigating the risks|survey.*(agent|trustworthy).*threat|threats",
 "governance": r"governance|principled|responsible|regime|compliance",
 "adversarial_method": r"colored teaming|proactive defense|red.?team",
}
pdfs=[]
for root,_,fs in os.walk(P):
    for f in fs:
        if f.lower().endswith(".pdf"): pdfs.append(os.path.join(root,f))
def first_text(path,n=1600):
    try:
        d=fitz.open(path); t=""
        for pg in d[:2]:
            t+=pg.get_text()
            if len(t)>n: break
        d.close(); t=re.sub(r"\s+"," ",t).strip(); return t[:n]
    except Exception as e: return "[err] "+str(e)[:60]
out=[]; seen=set()
for theme,kw in themes.items():
    rx=re.compile(kw,re.I)
    matches=[p for p in pdfs if rx.search(os.path.basename(p))][:3]
    out.append("\n########## "+theme.upper()+" ##########")
    for p in matches:
        nm=os.path.basename(p)
        if nm in seen: continue
        seen.add(nm)
        out.append("\n### "+nm+"\n"+first_text(p))
with open(r"C:\Users\speci.000\Documents\NEXUS\_tools\_abstracts.txt","w",encoding="utf-8") as fh:
    fh.write("TOTAL PDFS: %d\n"%len(pdfs))
    fh.write("\n".join(out))
print("done; pdfs=%d picked=%d"%(len(pdfs),len(seen)))
