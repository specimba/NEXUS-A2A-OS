#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scripts/fetch_hf_papers_digest.py — Hugging Face Daily Papers & alphaXiv Curation Script

Usage:
  python scripts/fetch_hf_papers_digest.py --date 2026-07-14
  python scripts/fetch_hf_papers_digest.py (defaults to today's date)
"""

import sys
import os
import argparse
import urllib.request
import json
import sqlite3
from datetime import datetime, timedelta

def get_current_date_string():
    # Use timezone-aware or simple UTC date
    # In Windows local time is: 2026-07-15T11:02:57+03:00, so 2026-07-15
    return datetime.now().strftime("%Y-%m-%d")

def fetch_hf_daily_papers(date_str):
    url = f"https://huggingface.co/api/daily_papers?date={date_str}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    print(f"Fetching Hugging Face Daily Papers for {date_str}...")
    print(f"URL: {url}")
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    except Exception as e:
        print(f"Error fetching from Hugging Face: {e}")
        return []

def get_db_connection():
    # Locate db/custom.db
    # If called from root, it is db/custom.db. If called from scripts, search parent.
    possible_paths = [
        os.path.join(os.getcwd(), 'db', 'custom.db'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'db', 'custom.db')
    ]
    db_path = None
    for p in possible_paths:
        if os.path.exists(p):
            db_path = p
            break
    if not db_path:
        # Fallback to creating it in root db/custom.db
        db_path = possible_paths[0]
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    print(f"Connecting to database at: {db_path}")
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def save_papers_to_db(papers_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    saved_count = 0
    skipped_count = 0
    
    for item in papers_data:
        paper_obj = item.get('paper', {})
        arxiv_id = paper_obj.get('id')
        if not arxiv_id:
            continue
            
        title = item.get('title', 'Untitled Paper')
        summary = item.get('summary', '')
        published_date = item.get('publishedAt', '')
        
        # Format authors JSON array
        authors_list = [a.get('name') for a in paper_obj.get('authors', []) if a.get('name')]
        authors_json = json.dumps(authors_list, ensure_ascii=False)
        
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        repo_url = f"https://alphaxiv.org/abs/{arxiv_id}" # alphaXiv URL
        
        # Check if paper already exists
        cursor.execute("SELECT id FROM Paper WHERE externalId = ? OR title = ?", (arxiv_id, title))
        existing = cursor.fetchone()
        
        if existing:
            skipped_count += 1
            continue
            
        # Insert new paper
        paper_uuid = f"paper-{arxiv_id}"
        now_str = datetime.now().isoformat()
        
        try:
            cursor.execute("""
                INSERT INTO Paper (
                    id, externalId, type, title, pdfUrl, repoUrl, abstractSummary, 
                    authors, publishedDate, admissionTier, sourceFamily, sourceSubtype,
                    relevanceScore, dgFinalScore, priorityTier, promotable, isVetted, 
                    provenanceSource, createdAt, updatedAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper_uuid, arxiv_id, 'paper', title, pdf_url, repo_url, summary,
                authors_json, published_date, 'source_stub', 'paper', 'hf_paper',
                0.5, 0, 'P1', 0, 0, 'huggingface_daily_papers', now_str, now_str
            ))
            saved_count += 1
        except Exception as e:
            print(f"Failed to insert paper {arxiv_id}: {e}")
            
    conn.commit()
    conn.close()
    
    print(f"DB Ingestion complete: {saved_count} new papers saved, {skipped_count} skipped/duplicates.")
    return saved_count

def generate_markdown_report(papers_data, date_str):
    if not papers_data:
        return f"### No daily papers found on Hugging Face for {date_str}."
        
    md = []
    md.append(f"### Hugging Face Daily Papers Curation — {date_str}")
    md.append(f"Found {len(papers_data)} trending papers on Hugging Face Daily Papers.\n")
    
    for i, item in enumerate(papers_data, 1):
        paper_obj = item.get('paper', {})
        arxiv_id = paper_obj.get('id')
        title = item.get('title', 'Untitled')
        summary = item.get('summary', '')
        authors_list = [a.get('name') for a in paper_obj.get('authors', []) if a.get('name')]
        authors_str = ", ".join(authors_list) if authors_list else "Unknown"
        
        # alphaXiv link
        alphaxiv_url = f"https://alphaxiv.org/abs/{arxiv_id}"
        arxiv_pdf = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        hf_url = f"https://huggingface.co/papers/{arxiv_id}"
        
        md.append(f"#### {i}. {title}")
        md.append(f"- **Authors**: {authors_str}")
        md.append(f"- **arXiv ID**: `{arxiv_id}`")
        md.append(f"- **Abstract**: {summary[:300]}...")
        md.append(f"- **Curation Links**: [alphaXiv Discussion]({alphaxiv_url}) | [arXiv PDF]({arxiv_pdf}) | [Hugging Face Hub]({hf_url})")
        md.append("")
        
    return "\n".join(md)

def main():
    parser = argparse.ArgumentParser(description="Fetch Hugging Face Daily Papers & construct alphaXiv links.")
    parser.add_argument("--date", type=str, default=None, help="Target date in YYYY-MM-DD format.")
    parser.add_argument("--save", action="store_true", default=True, help="Save parsed papers to database.")
    args = parser.parse_args()
    
    date_str = args.date if args.date else get_current_date_string()
    
    papers = fetch_hf_daily_papers(date_str)
    
    if args.save and papers:
        save_papers_to_db(papers)
        
    report = generate_markdown_report(papers, date_str)
    
    # Save report to a markdown file for the curation loop
    output_dir = os.path.join(os.getcwd(), 'docs', 'curation')
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, f"hf_papers_{date_str}.md")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
        
    print(f"\nMarkdown report generated at: {report_path}")
    print("\n--- Summary Report ---")
    print("\n".join(report.split("\n")[:20])) # Print first 20 lines to console

if __name__ == "__main__":
    main()
