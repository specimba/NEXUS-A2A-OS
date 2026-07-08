
import fitz, os, re, json
P = r"C:\Users\speci.000\Downloads\ARCHIVIST\PAPERS"
# theme -> regex of filename keywords
themes = {
 "injection_defense": r"promptshield|secalign|commandsans|injecagent|argus|indirect prompt|signed up for|prompt.?inject|sanitiz|wasp",
 "privilege_access": r"progent|privilege|access control|least.?privilege|capability",
 "verification_validation": r"verification and validation|trustworthiness.*verif|formal verif|runtime monitor|verify",
 "human_oversight": r"oversight|human.?in.?the.?loop|scalable.*oversight|interactive oversight|approval",
 "threat_taxonomy": r"threats|navigating the risks|survey.*(agent|trustworthy).*threat|attack.*agent",
 "governance": r"governance|govern|principled|responsible|regime|compliance|audit",
 "adversarial_method": r"colored teaming|red.?team|proactive defense|adversarial",
}
pdfs = []
for root,_,fs in os.walk(P):
    for f in fs:
        if f.lower().endswith(".pdf"): pdfs.append(os.path.join(root,f))

def first_text(path, n=1800):
    try:
        d=fitz.open(path); t=""
        for pg in d[:2]:
            t+=pg.get_text()
            if len(t)>n: break
        d.close()
        t=re.sub(r"\s+"," ",t).strip()
        return t[:n]
    except Exception as e:
        return "[extract error] "+str(e)[:60]

picked={}
for theme,kw in themes.items():
    rx=re.compile(kw,re.I)
    matches=[p for p in pdfs if rx.search(os.path.basename(p))]
    picked[theme]=matches[:3]

out=[]
seen=set()
for theme,paths in picked.items():
    out.append("\n########## THEME: "+theme.upper()+" ##########")
    for p in paths:
        name=os.path.basename(p)
        if name in seen: continue
        seen.add(name)
        out.append("\n### "+name)
        out.append(first_text(p))
print("TOTAL PDFS: %d | themes matched: %s"%(len(pdfs), {k:len(v) for k,v in picked.items()}))
print("\n".join(out)[:9000])
