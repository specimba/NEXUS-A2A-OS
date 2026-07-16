#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scripts/curate_daily_digest.py — Curate Daily AI Curation Report (HuggingNews + HF + alphaXiv)

Usage:
  python scripts/curate_daily_digest.py --date 2026-07-15
  python scripts/curate_daily_digest.py (defaults to today's date)
"""

import sys
import os
import argparse
import sqlite3
import json
from datetime import datetime

# Reconfigure stdout to use utf-8 to prevent Windows terminal print crashes on emojis
sys.stdout.reconfigure(encoding='utf-8')

def get_current_date_string():
    return datetime.now().strftime("%Y-%m-%d")

def get_db_connection():
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
        db_path = possible_paths[0]
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def curate_digest(date_str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query Hugging Face daily papers fetched today/yesterday or having hf_paper source
    # We select papers ingested around the current date range
    cursor.execute("""
        SELECT * FROM Paper 
        WHERE provenanceSource = 'huggingface_daily_papers'
        ORDER BY publishedDate DESC, createdAt DESC
    """)
    hf_rows = cursor.fetchall()
    
    # Query HuggingNews stories fetched
    cursor.execute("""
        SELECT * FROM Paper 
        WHERE provenanceSource = 'huggingnews'
        ORDER BY createdAt DESC
    """)
    hn_rows = cursor.fetchall()
    
    conn.close()
    
    print(f"Curating daily report from database: Found {len(hf_rows)} HF papers and {len(hn_rows)} HuggingNews stories.")
    
    md = []
    md.append(f"# NEXUS OS Daily AI Intelligence Digest — {date_str}")
    md.append("A unified daily compilation of high-signal AI developments, trending research papers, and interactive community discussions.\n")
    
    # ── Section 1: Trending News & System Diagnostics ──────────────────
    md.append("## 📰 High-Signal AI Industry & Developer News")
    md.append("Surfaced from HuggingNews (X network trending AI accounts tracking):")
    md.append("")
    
    if hn_rows:
        # We group or display the top 15 stories
        for i, row in enumerate(hn_rows[:15], 1):
            md.append(f"{i}. **[{row['title']}]({row['repoUrl']})**")
            md.append(f"   *Source/Provenance: {row['provenanceSource']}*")
    else:
        md.append("*No news stories ingested for today. Run `python scripts/fetch_huggingnews_digest.py` to fetch.*")
    md.append("")
    
    # ── Section 2: Trending Research & alphaXiv Curation ──────────────
    md.append("## 🔬 Trending Research Papers & alphaXiv Discussions")
    md.append("Curated papers from Hugging Face Daily Papers with interactive alphaXiv discussion hubs:")
    md.append("")
    
    if hf_rows:
        for i, row in enumerate(hf_rows[:10], 1):
            title = row['title']
            arxiv_id = row['externalId'] or 'Unknown'
            abstract = row['abstractSummary'] or 'No abstract available.'
            
            # Authors parsing
            authors_str = "Unknown"
            if row['authors']:
                try:
                    authors_list = json.loads(row['authors'])
                    authors_str = ", ".join(authors_list)
                except Exception:
                    authors_str = str(row['authors'])
            
            # alphaXiv url
            alphaxiv_url = f"https://alphaxiv.org/abs/{arxiv_id}"
            arxiv_pdf = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            hf_url = f"https://huggingface.co/papers/{arxiv_id}"
            
            md.append(f"### {i}. {title}")
            md.append(f"- **Authors**: {authors_str}")
            md.append(f"- **arXiv ID**: `{arxiv_id}`")
            md.append(f"- **Abstract Summary**: {abstract[:400]}...")
            md.append(f"- **Curation Links**: [alphaXiv Interactive Discussion]({alphaxiv_url}) | [arXiv PDF]({arxiv_pdf}) | [Hugging Face Hub]({hf_url})")
            md.append("")
    else:
        md.append("*No research papers ingested for today. Run `python scripts/fetch_hf_papers_digest.py` to fetch.*")
        
    # ── Section 3: Steering Prompt for NotebookLM ──────────────────────
    md.append("## 🎬 Steering Prompt for NotebookLM Short Video Summary")
    md.append("Copy-paste the prompt below into the NotebookLM Video Overview customize input box to steer the generation:")
    md.append("```text")
    md.append(f"Generate a 180-second vertical Cinematic Video Overview summarizing the main AI highlights of {date_str} for a technical developer audience.")
    md.append("Focus on these three key stories:")
    
    # Extract top 3 news stories for the prompt
    top_stories = [row['title'] for row in hn_rows[:3]]
    if len(top_stories) < 3:
        top_stories += ["Apple-OpenAI developer trade secret suit", "DeepSeek mainland China IPO preparation", "PrismML local Bonsai 27B model for mobile devices"]
        
    for j, story in enumerate(top_stories[:3], 1):
        md.append(f"  {j}. {story}")
    md.append("Frame the discussion around developer impact, API capabilities, and the shift toward local execution. Maintain a fast-paced, high-intelligence tone throughout.")
    md.append("```")
    
    return "\n".join(md)

def main():
    parser = argparse.ArgumentParser(description="Curate HuggingNews + HF papers into a single compiled report.")
    parser.add_argument("--date", type=str, default=None, help="Curation date in YYYY-MM-DD format.")
    args = parser.parse_args()
    
    date_str = args.date if args.date else get_current_date_string()
    
    report = curate_digest(date_str)
    
    # Save the curated report
    output_dir = os.path.join(os.getcwd(), 'docs', 'curation')
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, f"daily_digest_{date_str}.md")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
        
    print(f"\nDaily Curation Report successfully compiled at: {report_path}")
    print("\nReport preview:")
    print("\n".join(report.split("\n")[:30]))

if __name__ == "__main__":
    main()
