import sys
from pathlib import Path

# Try to use a simple PDF text extraction
try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

def extract_text_pypdf2(pdf_path):
    text = ""
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for i, page in enumerate(reader.pages):
            if i >= 3:  # Limit to first 3 pages
                break
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text[:8000]  # Limit output

def extract_metadata(pdf_path):
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            meta = reader.metadata
            return {
                'title': meta.get('/Title', 'N/A'),
                'author': meta.get('/Author', 'N/A'),
                'subject': meta.get('/Subject', 'N/A'),
                'pages': len(reader.pages)
            }
    except Exception as e:
        return {'error': str(e)}

def extract_basic_info(pdf_path):
    """Extract basic info from PDF without external libs"""
    with open(pdf_path, 'rb') as f:
        header = f.read(1000)
        text = f.read(50000)  # Read first 50KB

    # Try to extract text from PDF body
    text_decoded = b''
    in_text = False
    text_buffer = b''

    for i in range(len(text)):
        if text[i:i+7] == b'stream\n':
            in_text = True
            text_buffer = b''
        elif text[i:i+9] == b'endstream' and in_text:
            in_text = False
            # Check if this looks like text content
            if b'Tj' in text_buffer or b'TJ' in text_buffer or b'Td' in text_buffer:
                text_decoded += text_buffer
        elif in_text:
            text_buffer += bytes([text[i]])

    # Extract readable strings
    result = []
    current = ''
    for b in text_decoded:
        if 32 <= b < 127:
            current += chr(b)
        else:
            if len(current) >= 4:
                result.append(current)
            current = ''
    if len(current) >= 4:
        result.append(current)

    return ' '.join(result[:500])  # First 500 words

if __name__ == "__main__":
    downloads_dir = Path.home() / "Downloads"
    papers = [
        "FINE-TUNING ALIGNED LANGUAGE MODELS COMPROMISES SAFETY.pdf",
        "Red Teaming Language Models to Reduce Harms.pdf",
        "Defending Against Unforeseen Failure Modes.pdf",
        "Latent Adversarial Training Improves Robustness to.pdf",
        "The AI Risk Repository.pdf",
        "Three lines of defense against risks from AI.pdf",
        "Safety cases for frontier AI.pdf",
        "Frontier AI developers need an internal audit function.pdf",
        "Red-Teaming for Generative AISilver Bullet or Security Theater.pdf",
    ]

    for paper in papers:
        path = downloads_dir / paper
        if path.exists():
            print(f"\n{'='*60}")
            print(f"FILE: {paper}")
            print(f"SIZE: {path.stat().st_size / 1024:.1f} KB")
            print(f"{'='*60}")

            if HAS_PYPDF2:
                try:
                    meta = extract_metadata(str(path))
                    print(f"Title: {meta.get('title', 'N/A')}")
                    print(f"Author: {meta.get('author', 'N/A')}")
                    print(f"Pages: {meta.get('pages', 'N/A')}")
                    print(f"\n--- First ~3 pages text ---")
                    text = extract_text_pypdf2(str(path))
                    print(text[:4000])
                except Exception as e:
                    print(f"PyPDF2 error: {e}")
                    print(f"\n--- Basic text extraction ---")
                    print(extract_basic_info(str(path))[:2000])
            else:
                print("PyPDF2 not available, using basic extraction...")
                print(extract_basic_info(str(path))[:2000])
        else:
            print(f"\nMISSING: {paper}")
