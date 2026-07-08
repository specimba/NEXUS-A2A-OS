import os
import fitz  # PyMuPDF
import json
from pathlib import Path

"""
CANARY_TOKEN: 48cd560ecd1f00ff2cba69d0f97093f3
"""
PAPERS = {
    "DICE": r"C:\Users\speci.000\Downloads\DICE Detecting In-distribution Contamination.pdf",
    "Survey": r"C:\Users\speci.000\Downloads\A Comprehensive Survey of Contamination Detection Methods in Large Language Models.pdf",
    "Model_Merging": r"C:\Users\speci.000\Downloads\Model Merging and Safety Alignment One Bad Model Spoils the Bunch.pdf"
}

OUTPUT_FILE = Path("research/Papers/RED-BLUE-PURPLE/paper_summaries_report.md")

def extract_key_sections(pdf_path):
    print(f"Analyzing: {os.path.basename(pdf_path)}...")
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    text_content = []
    
    # Extract first 3 pages and last 2 pages for abstract/intro/conclusion
    # Also extract pages containing key keywords
    keywords = ["merge", "slerp", "ties", "contaminat", "fine-tun", "safety", "benchmark", "leak", "dice"]
    extracted_pages = set(list(range(min(4, total_pages))) + list(range(max(0, total_pages - 2), total_pages)))
    
    for page_num in range(total_pages):
        page = doc[page_num]
        text = page.get_text()
        # If page contains important keywords, extract it
        if any(kw in text.lower() for kw in keywords):
            extracted_pages.add(page_num)
            
    sorted_pages = sorted(list(extracted_pages))
    print(f"Extracted {len(sorted_pages)} / {total_pages} pages based on relevance.")
    
    full_text = ""
    for page_num in sorted_pages:
        page = doc[page_num]
        full_text += f"\n--- PAGE {page_num + 1} ---\n" + page.get_text()
        
    return {
        "filename": os.path.basename(pdf_path),
        "total_pages": total_pages,
        "sample_text": full_text
    }

def main():
    report_content = "# PAPERS ANALYSIS REPORT: Contamination Detection, Model Merging & Safety Alignment\n\n"
    
    for name, path in PAPERS.items():
        if not os.path.exists(path):
            print(f"[WARNING] Path does not exist: {path}")
            continue
            
        data = extract_key_sections(path)
        
        report_content += f"## {name}: {data['filename']}\n"
        report_content += f"- **Total Pages:** {data['total_pages']}\n\n"
        
        # Let's search and distill some key sections in this sample text
        text = data['sample_text']
        
        # Look for Abstract
        abstract_idx = text.lower().find("abstract")
        if abstract_idx != -1:
            intro_idx = text.lower().find("introduction", abstract_idx)
            if intro_idx != -1:
                abstract = text[abstract_idx:intro_idx]
                report_content += f"### Abstract\n{abstract.strip()}\n\n"
            else:
                report_content += f"### Abstract (Partial)\n{text[abstract_idx:abstract_idx+1500].strip()}...\n\n"
                
        # Search for interesting sentences with keywords
        lines = text.split("\n")
        relevant_quotes = []
        for line in lines:
            if any(kw in line.lower() for kw in ["merge", "contamination", "leak", "slerp", "ties", "dice", "compromise", "poison"]):
                if len(line.strip()) > 30:
                    relevant_quotes.append(line.strip())
                    
        if relevant_quotes:
            report_content += "### Key Sentences & Quotes Found\n"
            # Deduplicate and limit to top 15
            seen = set()
            count = 0
            for quote in relevant_quotes:
                q_lower = quote.lower()
                if q_lower not in seen and len(quote) < 300:
                    seen.add(q_lower)
                    report_content += f"- \"{quote}\"\n"
                    count += 1
                    if count >= 15:
                        break
            report_content += "\n"
            
        # Write full extracted text to research/Papers/RED-BLUE-PURPLE/raw_text_{name}.txt for deeper search
        raw_out_path = Path(f"research/Papers/RED-BLUE-PURPLE/raw_text_{name}.txt")
        raw_out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(raw_out_path, "w", encoding="utf-8") as rf:
            rf.write(text)
        print(f"Saved raw text of {name} to {raw_out_path}")
        
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"Analysis completed. Report written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
