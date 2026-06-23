import sys

try:
    import pypdf
    print("pypdf is installed")
except ImportError:
    try:
        import PyPDF2 as pypdf
        print("PyPDF2 is installed")
    except ImportError:
        pypdf = None
        print("No PDF libraries found")

if pypdf:
    pdf_path = r"C:\Users\speci.000\Downloads\ARCHIVIST\PAPERS\papers10\BEYOND FAST AND SLOW COGNITIVE-INSPIRED ELASTIC REASONING FOR LARGE LANGUAGE MODELS.pdf"
    try:
        if hasattr(pypdf, "PdfReader"):
            reader = pypdf.PdfReader(pdf_path)
            text = ""
            for i in range(min(5, len(reader.pages))):
                text += f"--- Page {i+1} ---\n"
                text += reader.pages[i].extract_text()
        else:
            reader = pypdf.PdfFileReader(pdf_path)
            text = ""
            for i in range(min(5, reader.numPages)):
                text += f"--- Page {i+1} ---\n"
                text += reader.getPage(i).extractText()
        
        with open("scratch/coger_extracted.txt", "w", encoding="utf-8") as out:
            out.write(text)
        print("Extracted text saved to scratch/coger_extracted.txt")
    except Exception as e:
        print(f"Error parsing PDF: {e}")
else:
    print("Cannot parse PDF without libraries.")
