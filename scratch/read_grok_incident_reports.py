import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

def extract_text_from_docx(docx_path):
    try:
        with zipfile.ZipFile(docx_path, 'r') as z:
            with z.open('word/document.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
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

def main():
    downloads_dir = Path("C:/Users/speci.000/Downloads")
    scratch_dir = Path("C:/Users/speci.000/Documents/NEXUS/scratch")
    scratch_dir.mkdir(parents=True, exist_ok=True)
    
    files_to_extract = [
        "16专家交叉共识主策略v2.0.docx",
        "GROK_INCIDENT_13EXPERT_FINAL_REPORT_EN.docx",
        "第1章执行摘要.docx",
        "第2章事件全景还原.docx",
        "第3章云端删除方案深度分析.docx",
        "第4章创新AI自纠方案.docx",
        "第5章声誉保护与合规响应.docx",
        "第6章实施路线图.docx"
    ]
    
    for filename in files_to_extract:
        src_path = downloads_dir / filename
        if src_path.exists():
            text = extract_text_from_docx(src_path)
            out_filename = filename.replace(".docx", "_extracted.md")
            dest_path = scratch_dir / out_filename
            dest_path.write_text(text, encoding='utf-8')
            print(f"Extracted {len(text)} chars")
        else:
            print(f"File not found: {filename}")

if __name__ == "__main__":
    main()
