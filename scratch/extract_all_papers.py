import os
import sys
import pypdf

# Reconfigure stdout to use UTF-8 on Windows
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

papers_dir = r"C:\Users\speci.000\Downloads\ARCHIVIST\PAPERS\papers10"
output_dir = "scratch/extracted_papers"
os.makedirs(output_dir, exist_ok=True)

target_papers = [
    "Progent Securing AI Agents with Privilege Control.pdf",
    "Tandem Riding Together with Large and Small Language Models.pdf",
    "Evolutionary Optimization of Model Merging Recipes.pdf",
    "VibeThinker-3B Exploring the Frontier of Verifiable Reasoning.pdf",
    "Fugu_technical_report.pdf",
    "CommandSans SECURING AI AGENTS WITH SURGICAL.pdf",
    "AGENT SECURITY BENCH (ASB) FORMALIZING AND BENCHMARKING.pdf"
]

for paper_name in target_papers:
    pdf_path = os.path.join(papers_dir, paper_name)
    if not os.path.exists(pdf_path):
        print(f"Paper not found: {paper_name}")
        continue
    
    txt_name = paper_name.replace(".pdf", "_extracted.txt")
    txt_path = os.path.join(output_dir, txt_name)
    
    print(f"Extracting {paper_name}...")
    try:
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        # Extract first 4 pages
        for i in range(min(4, len(reader.pages))):
            text += f"\n================ PAGE {i+1} ================\n"
            text += reader.pages[i].extract_text()
        
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Saved to {txt_path}")
    except Exception as e:
        print(f"Failed to extract {paper_name}: {e}")
