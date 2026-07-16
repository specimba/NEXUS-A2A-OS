#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scripts/fetch_huggingnews_digest.py — HuggingNews Scraper & DB Ingest Script

Usage:
  python scripts/fetch_huggingnews_digest.py --limit 15
"""

import sys
import os
import argparse
import urllib.request
import re
import html
import json
import sqlite3
from datetime import datetime

def fetch_huggingnews():
    url = 'https://huggingnews.com/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    print("Fetching HuggingNews trending stories...")
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            html_content = response.read().decode('utf-8')
            return html_content
    except Exception as e:
        print(f"Error fetching HuggingNews: {e}")
        return None

def parse_stories(html_content, limit_per_day=15):
    if not html_content:
        return {}
        
    sections = re.split(r'<h2[^>]+class="[^"]*day-date[^"]*"[^>]*>', html_content)
    
    story_regex = re.compile(
        r'<a[^>]+class="[^"]*story-row-link[^"]*"[^>]+href="([^"]+)"[^>]*>'
        r'[\s\S]*?'
        r'<div[^>]+class="[^"]*story-title[^"]*"[^>]*>'
        r'([\s\S]*?)'
        r'</div>',
        re.IGNORECASE
    )
    
    digest_data = {}
    
    for i in range(1, len(sections)):
        section = sections[i]
        date_end = section.find('</h2>')
        date_str = section[:date_end].strip()
        
        matches = story_regex.findall(section)
        parsed_stories = []
        for href, title_html in matches[:limit_per_day]:
            # Clean title
            title = re.sub(r'<[^>]+>', '', title_html)
            title = html.unescape(title).replace('↩︎', '').strip()
            # Remove leading "NEW" or tags
            if title.startswith("NEW"):
                title = title[3:].strip()
                
            full_href = f"https://huggingnews.com{href}" if href.startswith('/') else href
            
            parsed_stories.append({
                "title": title,
                "url": full_href,
                "slug": href.split('/')[-1] if '/' in href else href
            })
            
        digest_data[date_str] = parsed_stories
        
    return digest_data

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

def save_news_to_db(digest_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    saved_count = 0
    skipped_count = 0
    
    for date_str, stories in digest_data.items():
        for story in stories:
            title = story["title"]
            url = story["url"]
            slug = story["slug"]
            
            # Check if story already exists by URL or title
            cursor.execute("SELECT id FROM Paper WHERE repoUrl = ? OR title = ?", (url, title))
            existing = cursor.fetchone()
            
            if existing:
                skipped_count += 1
                continue
                
            story_uuid = f"news-{slug}"
            now_str = datetime.now().isoformat()
            
            try:
                # We save stories to the Paper table with type='news'
                cursor.execute("""
                    INSERT INTO Paper (
                        id, externalId, type, title, pdfUrl, repoUrl, abstractSummary, 
                        admissionTier, sourceFamily, sourceSubtype,
                        relevanceScore, dgFinalScore, priorityTier, promotable, isVetted, 
                        provenanceSource, createdAt, updatedAt
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    story_uuid, slug, 'news', title, url, url, f"Trending story from HuggingNews on {date_str}.",
                    'source_stub', 'social', 'huggingnews_story',
                    0.6, 0, 'P1', 0, 0, 'huggingnews', now_str, now_str
                ))
                saved_count += 1
            except Exception as e:
                print(f"Failed to insert story {slug}: {e}")
                
    conn.commit()
    conn.close()
    
    print(f"HuggingNews DB Ingestion: {saved_count} new stories saved, {skipped_count} skipped/duplicates.")
    return saved_count

def generate_markdown_report(digest_data):
    if not digest_data:
        return "### No trending stories found on HuggingNews."
        
    md = []
    md.append("### HuggingNews AI Trending Stories Digest")
    md.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    for date_str, stories in digest_data.items():
        md.append(f"#### Curation Date: {date_str}")
        for i, story in enumerate(stories, 1):
            md.append(f"{i}. [{story['title']}]({story['url']})")
        md.append("")
        
    return "\n".join(md)

def main():
    parser = argparse.ArgumentParser(description="Fetch HuggingNews trending stories and save them to custom.db.")
    parser.add_argument("--limit", type=int, default=15, help="Max stories to fetch per day.")
    parser.add_argument("--save", action="store_true", default=True, help="Save to SQLite database.")
    args = parser.parse_args()
    
    html_content = fetch_huggingnews()
    if not html_content:
        print("Failed to fetch HuggingNews.")
        return
        
    digest_data = parse_stories(html_content, args.limit)
    
    if args.save and digest_data:
        save_news_to_db(digest_data)
        
    report = generate_markdown_report(digest_data)
    
    # Save report
    output_dir = os.path.join(os.getcwd(), 'docs', 'curation')
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, "huggingnews_latest.md")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
        
    print(f"\nMarkdown report generated at: {report_path}")
    print("\n--- Top Stories ---")
    first_date = list(digest_data.keys())[0] if digest_data else None
    if first_date:
        print(f"\nDate: {first_date}")
        for story in digest_data[first_date][:5]:
            print(f"- {story['title']}")

if __name__ == "__main__":
    main()
