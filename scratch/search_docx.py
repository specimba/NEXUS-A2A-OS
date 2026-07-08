import docx
from pathlib import Path

archivist_dir = Path("C:/Users/speci.000/Downloads/ARCHIVIST")
print("Searching docx files for ASMRtempLLM...")

for f in archivist_dir.glob("*.docx"):
    try:
        doc = docx.Document(f)
        fullText = []
        for para in doc.paragraphs:
            fullText.append(para.text)
        text = "\n".join(fullText)
        if "ASMRtempLLM" in text or "ASMR" in text:
            print(f"Found in {f.name}!")
    except Exception as e:
        print(f"Error reading {f.name}: {e}")
