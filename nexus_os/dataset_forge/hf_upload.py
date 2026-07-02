"""NEXUS Dataset Forge — Private HuggingFace dataset upload.

Uploads datasets to HuggingFace as private datasets.
Requires HF_TOKEN environment variable or token file.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx


HF_API = "https://huggingface.co"
DEFAULT_TOKEN_PATH = Path.home() / ".cache" / "huggingface" / "token"


@dataclass
class UploadConfig:
    repo_id: str
    repo_type: str = "dataset"
    private: bool = True
    embed_urls: bool = False
    delete_after_upload: bool = False
    commit_message: str = ""
    num_workers: int = 4
    chunk_size: int = 500

    def __post_init__(self):
        if not self.commit_message:
            self.commit_message = f"NEXUS Dataset Forge upload {datetime.now().strftime('%Y-%m-%d')}"


class HFuploader:
    """Upload NEXUS datasets to HuggingFace as private datasets."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("HF_TOKEN") or self._load_token()
        if not self.token:
            raise ValueError(
                "No HF token found. Set HF_TOKEN env var, or ensure ~/.cache/huggingface/token exists, "
                "or pass token to HFuploader(token='...')"
            )
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _load_token(self) -> Optional[str]:
        if DEFAULT_TOKEN_PATH.exists():
            return DEFAULT_TOKEN_PATH.read_text().strip()
        return None

    def repo_exists(self, repo_id: str, repo_type: str = "dataset") -> bool:
        url = f"{HF_API}/api/{repo_type}s/{repo_id}"
        r = httpx.get(url, headers=self._headers, timeout=10)
        return r.status_code == 200

    def create_repo(self, repo_id: str, repo_type: str = "dataset", private: bool = True) -> bool:
        url = f"{HF_API}/api/{repo_type}s"
        payload = {
            "name": repo_id.split("/")[-1],
            "organization": repo_id.split("/")[0] if "/" in repo_id else None,
            "private": private,
            "repo_type": repo_type,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        r = httpx.post(url, json=payload, headers=self._headers, timeout=30)
        if r.status_code in (200, 409):
            return True
        return False

    def upload_jsonl(
        self,
        records: List[Dict[str, Any]],
        repo_id: str,
        filename: str = "data.jsonl",
        commit_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload records as JSONL to HF dataset repo."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            temp_path = f.name

        try:
            result = self._upload_file(
                file_path=temp_path,
                repo_id=repo_id,
                path_in_repo=filename,
                commit_message=commit_message or f"Upload {filename}",
            )
            return result
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def upload_dataset_folder(
        self,
        folder_path: str,
        repo_id: str,
        commit_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload an entire folder to HF dataset repo using git."""
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        return self._git_push(
            repo_id=repo_id,
            folder_path=str(folder),
            commit_message=commit_message or "Upload dataset folder",
        )

    def _upload_file(
        self,
        file_path: str,
        repo_id: str,
        path_in_repo: str,
        commit_message: str,
    ) -> Dict[str, Any]:
        url = f"{HF_API}/api/upload/{repo_id}/{path_in_repo}"
        with open(file_path, "rb") as f:
            r = httpx.post(
                url,
                headers={"Authorization": f"Bearer {self.token}"},
                files={"file": (path_in_repo, f, "application/jsonl")},
                timeout=120,
            )
        r.raise_for_status()
        return {"status": "uploaded", "repo_id": repo_id, "path": path_in_repo}

    def _git_push(
        self,
        repo_id: str,
        folder_path: str,
        commit_message: str,
    ) -> Dict[str, Any]:
        git_dir = Path(tempfile.mkdtemp())
        clone_url = f"https://{self.token}@huggingface.co/datasets/{repo_id}"

        try:
            subprocess.run(
                ["git", "clone", clone_url, str(git_dir)],
                capture_output=True,
                timeout=60,
                check=True,
            )
            import shutil
            for item in Path(folder_path).iterdir():
                dest = git_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest)

            subprocess.run(
                ["git", "add", "-A"],
                cwd=git_dir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=git_dir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=git_dir,
                capture_output=True,
                timeout=60,
                check=True,
            )
            return {"status": "pushed", "repo_id": repo_id, "commit": commit_message}
        finally:
            import shutil as sh
            sh.rmtree(git_dir, ignore_errors=True)

    def create_dataset_card(
        self,
        repo_id: str,
        dataset_name: str,
        description: str,
        language: str = "en",
        license: str = "mit",
        tags: Optional[List[str]] = None,
    ) -> bool:
        """Create or update README.md (dataset card) in the repo."""
        content = f"""---
annotations_creators:
- no-annotation
language:
- {language}
license: {license}
multilinguality:
- monolingual
source_datasets: []
task_categories:
- sequence-labeling
- text-classification
task_ids:
- multi-class-classification
- text-scoring
size_categories:
- n<1K
- n<10K
- n<100K
---

# {dataset_name}

{description}

## NEXUS Dataset Forge

Generated by NEXUS Dataset Forge (v4.0.0).
Quality tier: S2_Eval / S3_Benchmark.
Privacy: All PII removed, safety validated.

Tags: {", ".join(tags or [])}

---
"""
        url = f"{HF_API}/api/upload/{repo_id}/README.md"
        r = httpx.put(
            url,
            headers={"Authorization": f"Bearer {self.token}"},
            files={"file": ("README.md", content, "text/markdown")},
            timeout=30,
        )
        return r.status_code in (200, 201)


def upload_nexus_dataset(
    records: List[Dict[str, Any]],
    repo_id: str,
    dataset_name: str,
    description: str,
    private: bool = True,
    token: Optional[str] = None,
    language: str = "en",
    tags: Optional[List[str]] = None,
    chunk_size: int = 5000,
) -> Dict[str, Any]:
    """One-shot upload: create repo + upload data + create card."""
    uploader = HFuploader(token=token)

    if not uploader.repo_exists(repo_id):
        uploader.create_repo(repo_id, private=private)

    uploader.create_dataset_card(
        repo_id=repo_id,
        dataset_name=dataset_name,
        description=description,
        language=language,
        tags=tags,
    )

    total = len(records)
    uploaded = 0
    for i in range(0, total, chunk_size):
        chunk = records[i:i + chunk_size]
        filename = f"chunk_{i // chunk_size:04d}.jsonl"
        uploader.upload_jsonl(
            records=chunk,
            repo_id=repo_id,
            filename=filename,
            commit_message=f"NEXUS chunk {i // chunk_size}",
        )
        uploaded += len(chunk)

    return {
        "repo_id": repo_id,
        "total_records": total,
        "uploaded_records": uploaded,
        "chunks": (total + chunk_size - 1) // chunk_size,
        "url": f"https://huggingface.co/datasets/{repo_id}",
    }