"""
Cloudflare Bypass Stack — NEXUS OS Bridge Module
=================================================
Local-only research module for Cloudflare-protected API experiments.
Disabled by default unless an explicit operator flag is set.

Stack (in order of preference):
  1. cloudscraper25 — JS challenge solver (fork with v3 support)
  2. curl_cffi — TLS fingerprint impersonation
  3. FlareSolverr — Docker-based headless browser (heavy Cloudflare)
  4. nexCHA — Open-source Turnstile solver (from NopeCHALLC, forked)

All tools are dual-use. This module stays research-only unless local policy
enables it explicitly.

Dependencies:
  pip install cloudscraper25 curl_cffi requests
  # For FlareSolverr: docker run -d -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest
"""

import json
import logging
import os
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Environment flag: set NEXUS_BYPASS_DEBUG=1 for verbose logging
DEBUG = os.environ.get("NEXUS_BYPASS_DEBUG", "0") == "1"
BYPASS_ENABLED_ENV = "NEXUS_ENABLE_CLOUDFLARE_BYPASS"

# FlareSolverr endpoint
FLARESOLVERR_URL = os.environ.get("FLARESOLVERR_URL", "http://127.0.0.1:8191/v1")


@dataclass
class BypassResult:
    """Result from a bypass attempt."""
    success: bool
    status_code: int
    content: str
    cookies: Dict[str, str]
    user_agent: str
    method_used: str
    error: Optional[str] = None
    response_headers: Optional[Dict[str, str]] = None


class CloudflareBypassStack:
    """
    Layered bypass stack for Cloudflare-protected sites.

    Usage:
        bypass = CloudflareBypassStack()
        result = bypass.fetch("https://api.example.com/v1/chat")
        if result.success:
            print(result.content)
    """

    def __init__(
        self,
        proxy: Optional[str] = None,
        delay: int = 10,
        timeout: int = 60,
        max_retries: int = 3,
    ):
        self.proxy = proxy
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries
        self._session_cookies: Dict[str, str] = {}
        self._session_ua: str = ""

    def _is_enabled(self) -> bool:
        return os.environ.get(BYPASS_ENABLED_ENV, "0") == "1"

    # â”€â”€ Layer 1: cloudscraper25 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _try_cloudscraper(self, url: str, method: str = "GET", payload: Optional[Dict] = None) -> Optional[BypassResult]:
        """Attempt bypass using cloudscraper25 (enhanced fork)."""
        try:
            import cloudscraper
        except ImportError:
            logger.debug("cloudscraper not installed, skipping layer 1")
            return None

        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None

        # Try multiple browser profiles
        profiles = [
            {"browser": "chrome", "platform": "windows", "desktop": True},
            {"browser": "chrome", "platform": "android", "mobile": True},
            {"browser": "firefox", "platform": "darwin", "desktop": True},
        ]

        for profile in profiles:
            try:
                scraper = cloudscraper.create_scraper(
                    browser=profile,
                    interpreter="nodejs",
                    delay=self.delay,
                    debug=DEBUG,
                )
                if proxies:
                    scraper.proxies = proxies

                if method.upper() == "POST" and payload is not None:
                    resp = scraper.post(url, json=payload, timeout=self.timeout)
                else:
                    resp = scraper.get(url, timeout=self.timeout)

                if resp.status_code == 200:
                    return BypassResult(
                        success=True,
                        status_code=resp.status_code,
                        content=resp.text,
                        cookies=scraper.cookies.get_dict(),
                        user_agent=scraper.headers.get("User-Agent", ""),
                        method_used=f"cloudscraper25-{profile['browser']}-{profile.get('platform', 'default')}",
                        response_headers=dict(resp.headers),
                    )
            except Exception as e:
                if DEBUG:
                    logger.debug(f"cloudscraper profile {profile} failed: {e}")
                continue

        return None

    # â”€â”€ Layer 2: curl_cffi â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _try_curl_cffi(self, url: str, method: str = "GET", payload: Optional[Dict] = None) -> Optional[BypassResult]:
        """Attempt bypass using curl_cffi (TLS fingerprint impersonation)."""
        try:
            from curl_cffi import requests as curl_requests
        except ImportError:
            logger.debug("curl_cffi not installed, skipping layer 2")
            return None

        # If we have cached cookies from cloudscraper, reuse them with curl_cffi
        cookies = None
        if self._session_cookies:
            cookies = self._session_cookies

        try:
            impersonate_versions = ["chrome124", "chrome", "safari", "edge"]
            for version in impersonate_versions:
                try:
                    if method.upper() == "POST" and payload is not None:
                        resp = curl_requests.post(
                            url,
                            json=payload,
                            impersonate=version,
                            cookies=cookies,
                            timeout=self.timeout,
                        )
                    else:
                        resp = curl_requests.get(
                            url,
                            impersonate=version,
                            cookies=cookies,
                            timeout=self.timeout,
                        )

                    if resp.status_code == 200:
                        return BypassResult(
                            success=True,
                            status_code=resp.status_code,
                            content=resp.text,
                            cookies=dict(resp.cookies) if hasattr(resp, "cookies") else {},
                            user_agent="curl_cffi/" + version,
                            method_used=f"curl_cffi-{version}",
                            response_headers=dict(resp.headers),
                        )
                except Exception as e:
                    if DEBUG:
                        logger.debug(f"curl_cffi version {version} failed: {e}")
                    continue
        except Exception as e:
            logger.debug(f"curl_cffi overall failure: {e}")

        return None

    # â”€â”€ Layer 3: FlareSolverr â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _try_flaresolverr(self, url: str, method: str = "GET", payload: Optional[Dict] = None) -> Optional[BypassResult]:
        """Attempt bypass using FlareSolverr Docker service."""
        try:
            import requests
        except ImportError:
            return None

        cmd_payload = {
            "cmd": "request.get" if method.upper() == "GET" else "request.post",
            "url": url,
            "maxTimeout": self.timeout * 1000,
        }
        if payload is not None:
            cmd_payload["postData"] = json.dumps(payload)

        try:
            resp = requests.post(
                FLARESOLVERR_URL,
                headers={"Content-Type": "application/json"},
                json=cmd_payload,
                timeout=self.timeout + 10,
            )
            result = resp.json()

            if result.get("status") == "ok":
                solution = result["solution"]
                cookies = {c["name"]: c["value"] for c in solution.get("cookies", [])}
                return BypassResult(
                    success=True,
                    status_code=200,
                    content=solution.get("response", ""),
                    cookies=cookies,
                    user_agent=solution.get("userAgent", ""),
                    method_used="flaresolverr",
                    response_headers=None,
                )
        except requests.exceptions.ConnectionError:
            logger.debug("FlareSolverr not reachable — is the Docker container running?")
        except Exception as e:
            logger.debug(f"FlareSolverr failed: {e}")

        return None

    # â”€â”€ Layer 4: nexCHA (from NopeCHALLC open-source) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _try_nexcha(self, url: str, method: str = "GET", payload: Optional[Dict] = None) -> Optional[BypassResult]:
        """
        Attempt bypass using nexCHA (NopeCHALLC open-source Turnstile solver).
        
        This is a placeholder for the actual nexCHA integration.
        To activate:
          1. Clone https://github.com/NopeCHALLC/nopecha-extension
          2. Build the extension or use the Python solver API
          3. Point NEXUS_OS_NEXCHA_PATH to the built solver
        """
        nexcha_path = os.environ.get("NEXUS_OS_NEXCHA_PATH")
        if not nexcha_path:
            logger.debug("nexCHA path not set (NEXUS_OS_NEXCHA_PATH), skipping layer 4")
            return None

        # Placeholder: actual implementation will call the nexCHA solver
        # which is a stripped-down, defensive-only version of the NopeCHA code.
        logger.warning("nexCHA integration is stub — implement solver call here")
        return None

    # â”€â”€ Public API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def fetch(
        self,
        url: str,
        method: str = "GET",
        payload: Optional[Dict] = None,
        fallback_chain: Optional[List[str]] = None,
    ) -> BypassResult:
        """
        Fetch a Cloudflare-protected URL using the layered bypass stack.

        Args:
            url: Target URL
            method: HTTP method (GET or POST)
            payload: JSON payload for POST requests
            fallback_chain: Ordered list of methods to try.
                            Default: ["cloudscraper", "curl_cffi", "flaresolverr", "nexcha"]

        Returns:
            BypassResult with success flag, content, cookies, and metadata.
        """
        if not self._is_enabled():
            return BypassResult(
                success=False,
                status_code=0,
                content="",
                cookies={},
                user_agent="",
                method_used="disabled",
                error=(
                    f"Cloudflare bypass disabled by default. "
                    f"Set {BYPASS_ENABLED_ENV}=1 only for approved local research."
                ),
            )

        chain = fallback_chain or ["cloudscraper", "curl_cffi", "flaresolverr", "nexcha"]
        errors = []

        for layer in chain:
            logger.info("Bypass layer %s starting", layer)
            try:
                if layer == "cloudscraper":
                    result = self._try_cloudscraper(url, method, payload)
                elif layer == "curl_cffi":
                    result = self._try_curl_cffi(url, method, payload)
                elif layer == "flaresolverr":
                    result = self._try_flaresolverr(url, method, payload)
                elif layer == "nexcha":
                    result = self._try_nexcha(url, method, payload)
                else:
                    errors.append(f"Unknown layer: {layer}")
                    continue

                if result and result.success:
                    # Cache cookies for reuse
                    if result.cookies:
                        self._session_cookies = result.cookies
                    if result.user_agent:
                        self._session_ua = result.user_agent
                    logger.info("Bypass succeeded via %s", result.method_used)
                    return result
                elif result:
                    errors.append(f"{layer}: status {result.status_code}")
                else:
                    errors.append(f"{layer}: unavailable or failed")

            except Exception as e:
                errors.append(f"{layer}: exception {e}")
                if DEBUG:
                    logger.exception(f"Bypass layer {layer} crashed")

        # All layers exhausted
        return BypassResult(
            success=False,
            status_code=0,
            content="",
            cookies={},
            user_agent="",
            method_used="none",
            error=f"All bypass layers exhausted. Errors: {'; '.join(errors)}",
        )

    def get_session_headers(self) -> Dict[str, str]:
        """Get headers to reuse a solved session (cookies + UA)."""
        headers = {}
        if self._session_cookies:
            # Format cookies for reuse with requests/httpx
            cookie_str = "; ".join(f"{k}={v}" for k, v in self._session_cookies.items())
            headers["Cookie"] = cookie_str
        if self._session_ua:
            headers["User-Agent"] = self._session_ua
        return headers


# â”€â”€ Standalone Test / CLI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO)
    if len(sys.argv) < 2:
        print("Usage: python cloudflare_bypass.py <URL> [method]")
        sys.exit(1)
    target = sys.argv[1]
    method = sys.argv[2] if len(sys.argv) > 2 else "GET"
    bypass = CloudflareBypassStack()
    result = bypass.fetch(target, method=method)
    print(json.dumps({
        "success": result.success,
        "status_code": result.status_code,
        "method_used": result.method_used,
        "content_preview": result.content[:500] if result.content else "",
        "cookie_names": sorted(result.cookies.keys()),
        "error": result.error,
    }, indent=2))
