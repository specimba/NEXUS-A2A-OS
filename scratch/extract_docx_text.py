import sys
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

def extract_text_from_docx(docx_path):
    """Extract text from .docx using zip/xml parsing (no external libs needed)"""
    try:
        with zipfile.ZipFile(docx_path, 'r') as z:
            with z.open('word/document.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()

                # Word XML namespace
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

                paragraphs = []
                for paragraph in root.findall('.//w:p', ns):
                    texts = []
                    for node in paragraph.findall('.//w:t', ns):
                        if node.text:
                            texts.append(node.text)
                    if texts:
                        paragraphs.append(''.join(texts))

                return '\n'.join(paragraphs)
    except Exception as e:
        return f"ERROR extracting {docx_path}: {e}"

def summarize_docx(docx_path, max_chars=8000):
    text = extract_text_from_docx(docx_path)
    return text[:max_chars] + ("\n...[truncated]" if len(text) > max_chars else "")

if __name__ == "__main__":
    base_dir = Path("C:/Users/speci.000/Downloads/ERNIEsupramacyRESEARCHpaper01/session10")

    # Priority files to extract
    priority_files = [
        "GROK_INCIDENT_13EXPERT_FINAL_REPORT_EN.docx",
        "swarm_final_7expert_master_english.docx",
        "expert7_novel_evasion_25_techniques.docx",
        "swarm_expert1_cloud_security_novel_methods.docx",
        "swarm_expert5_crisis_comm_radical_strategies.docx",
        "swarm_expert7_tech_ops_aggressive_deletion.docx",
        "swarm_expert11_osint_threat_monitoring.docx",
        "expert1_trustkernel_200_scenarios.docx",
        "GROK_UPLOAD_QUEUE_INCIDENT_SWARM_REPORT_FINAL.docx",
        "GROK+Upload+Queue+Security+Incident+Report+-+English+Final+Editi.docx",
    ]

    for filename in priority_files:
        path = base_dir / filename
        if path.exists():
            print(f"\n{'='*60}")
            print(f"FILE: {filename}")
            print(f"SIZE: {path.stat().st_size / 1024:.1f} KB")
            print(f"{'='*60}")
            print(summarize_docx(str(path), 6000))
        else:
            print(f"\nMISSING: {filename}")
