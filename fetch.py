"""
Fetches raw catalogue HTML into corpus/raw, resumable via the manifest.

Course pages come over plain HTTP; program pages sit behind an AWS-WAF
challenge and need a headless browser.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import httpx

import config
import util

class CourseFetcher:
    def __init__(self, manifest: dict[str, dict], force: bool):
        self.manifest = manifest
        self.force = force
        self.client = httpx.Client(
            headers={"User-Agent": config.USER_AGENT},
            follow_redirects=True,
            timeout=config.REQUEST_TIMEOUT,
        )
        self.fetched = 0
        self.skipped = 0
        self.failed: list[tuple[str, str]] = []

    def close(self) -> None:
        self.client.close()

    # Retry transient transport and 5xx/429 errors with exponential backoff.
    def _get(self, url: str) -> httpx.Response | None:
        delay = config.BACKOFF_BASE
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                resp = self.client.get(url)
            except httpx.HTTPError as exc:
                if attempt == config.MAX_RETRIES:
                    self.failed.append((url, f"transport: {exc}"))
                    return None
                time.sleep(min(delay, config.BACKOFF_CAP))
                delay *= 2
                continue
            if resp.status_code in (429, 500, 502, 503, 504):
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if (retry_after and retry_after.isdigit()) else min(delay, config.BACKOFF_CAP)
                if attempt == config.MAX_RETRIES:
                    self.failed.append((url, f"http {resp.status_code} (exhausted retries)"))
                    return None
                time.sleep(wait)
                delay *= 2
                continue
            return resp
        return None

    def fetch(self, url: str, dest: Path, kind: str, **extra) -> str | None:
        # Honour robots, then skip anything already cached unless forced.
        if not util.apps_path_allowed(url):
            self.failed.append((url, "robots-disallowed"))
            return None
        if not self.force and url in self.manifest and dest.exists():
            self.skipped += 1
            return util.read_html(dest)

        resp = self._get(url)
        time.sleep(config.APPS_DELAY)
        if resp is None:
            return None
        if resp.status_code != 200:
            self.failed.append((url, f"http {resp.status_code}"))
            util.append_manifest(
                {"url": url, "ok": False, "status": resp.status_code, "kind": kind, **extra}
            )
            return None

        html = resp.text
        util.write_text(dest, html)
        self.fetched += 1
        rec = {
            "url": url,
            "ok": True,
            "status": 200,
            "kind": kind,
            "path": str(dest.relative_to(config.ROOT)).replace("\\", "/"),
            "bytes": len(html),
            "fetched_at": util.now_iso(),
            **extra,
        }
        util.append_manifest(rec)
        self.manifest[url] = rec
        return html

    def crawl(self, subjects_filter: set[str] | None, limit: int | None) -> None:
        idx_html = self.fetch(
            config.COURSE_INDEX_URL, config.RAW_INDEX / "course.html", "index"
        )
        if idx_html is None:
            print("FATAL: could not fetch subject index", file=sys.stderr)
            return
        subjects = self._subjects(idx_html)
        if subjects_filter:
            subjects = [s for s in subjects if s in subjects_filter]
        print(f"[courses] {len(subjects)} subjects to crawl")

        for si, subj in enumerate(subjects, 1):
            sub_url = f"{config.COURSE_INDEX_URL}/{subj}"
            sub_html = self.fetch(sub_url, config.RAW_SUBJECT / f"{subj}.html", "subject", subject=subj)
            if sub_html is None:
                continue
            courses = self._courses(sub_html, subj)
            if limit:
                courses = courses[:limit]
            print(f"  [{si}/{len(subjects)}] {subj}: {len(courses)} courses")
            for subj_code, number in courses:
                cu = f"{config.COURSE_INDEX_URL}/{subj_code}/{number}"
                dest = config.RAW_COURSE / f"{subj_code}__{number}.html"
                self.fetch(cu, dest, "course", subject=subj_code, number=number)

    @staticmethod
    def _subjects(html: str) -> list[str]:
        found = re.findall(r'href="/catalogue/course/([a-z0-9_]+)"', html)
        return sorted(set(found))

    @staticmethod
    def _courses(html: str, subj: str) -> list[tuple[str, str]]:
        pat = re.compile(rf'href="/catalogue/course/({re.escape(subj)})/([0-9][0-9a-z]*)"', re.I)
        seen: dict[tuple[str, str], None] = {}
        for s, n in pat.findall(html):
            seen[(s.lower(), n.lower())] = None
        return sorted(seen.keys())

# Programs live on calendar.ualberta.ca behind an AWS-WAF JS challenge, so this
# fetcher drives a real browser instead of a plain HTTP client.
class ProgramFetcher:
    # Strings that only appear while the WAF interstitial is still showing.
    CHALLENGE_MARKERS = ("challenge-container", "awsWafCookieDomainList", "AwsWafIntegration")

    def __init__(self, manifest: dict[str, dict], force: bool):
        self.manifest = manifest
        self.force = force
        self.fetched = 0
        self.skipped = 0
        self.failed: list[tuple[str, str]] = []
        self._pw = None
        self._browser = None
        self._page = None

    def __enter__(self):
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)
        self._page = self._browser.new_context(user_agent=config.USER_AGENT).new_page()
        return self

    def __exit__(self, *exc):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()

    def _render(self, url: str) -> str | None:
        page = self._page
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as exc:
            self.failed.append((url, f"goto: {exc}"))
            return None

        # The challenge JS reloads the page, so page.content() can race the
        # navigation. Poll until the markers are gone and real content has
        # loaded, swallowing the transient errors in between.
        html = ""
        for _ in range(60):
            try:
                html = page.content()
            except Exception:

                time.sleep(1)
                continue
            if "Resource Not Found" in html:
                return html
            if not any(m in html for m in self.CHALLENGE_MARKERS) and len(html) > 8000:
                return html
            time.sleep(1)

        if any(m in html for m in self.CHALLENGE_MARKERS):
            self.failed.append((url, "waf-challenge-unresolved"))
            return None
        return html or None

    def fetch(self, url: str, dest: Path, kind: str, **extra) -> str | None:
        if not util.cal_path_allowed(url):
            self.failed.append((url, "robots-disallowed"))
            return None
        if not self.force and url in self.manifest and dest.exists():
            self.skipped += 1
            return util.read_html(dest)

        html = self._render(url)
        time.sleep(config.CAL_DELAY)
        if html is None:
            util.append_manifest({"url": url, "ok": False, "status": None, "kind": kind, **extra})
            return None
        is_404 = "Resource Not Found" in html and len(html) < 3000
        if is_404:
            self.failed.append((url, "404 Resource Not Found"))
            util.append_manifest({"url": url, "ok": False, "status": 404, "kind": kind, **extra})
            return None

        util.write_text(dest, html)
        self.fetched += 1
        rec = {
            "url": url,
            "ok": True,
            "status": 200,
            "kind": kind,
            "path": str(dest.relative_to(config.ROOT)).replace("\\", "/"),
            "bytes": len(html),
            "fetched_at": util.now_iso(),
            **extra,
        }
        util.append_manifest(rec)
        self.manifest[url] = rec
        return html

    def discover_silver_poids(self) -> list[tuple[str, str]]:
        url = config.CONTENT_URL_TMPL.format(
            catoid=config.CATOID, navoid=config.UNDERGRAD_PROGRAMS_NAVOID
        )
        dest = config.RAW_INDEX / f"programs_navoid_{config.UNDERGRAD_PROGRAMS_NAVOID}.html"
        html = self.fetch(url, dest, "program_index")
        if html is None:
            return []
        from selectolax.parser import HTMLParser

        tree = HTMLParser(html)
        pairs: dict[str, str] = {}
        for a in tree.css("a"):
            m = re.search(r"poid=(\d+)", a.attributes.get("href", ""))
            if m:
                pairs.setdefault(m.group(1), re.sub(r"\s+", " ", a.text()).strip())
        return sorted(pairs.items(), key=lambda kv: int(kv[0]))

    def crawl(self, mode: str, max_programs: int | None) -> None:
        if mode == "gold":
            targets = [(poid, name, "gold") for poid, name in config.GOLD_POIDS.items()]
        else:
            discovered = self.discover_silver_poids()
            gold = set(config.GOLD_POIDS)
            targets = [(poid, name, "gold" if poid in gold else "silver") for poid, name in discovered]
            if max_programs:
                targets = targets[:max_programs]
        print(f"[programs] mode={mode}: {len(targets)} programs to fetch")
        for i, (poid, name, tier) in enumerate(targets, 1):
            url = config.PROGRAM_URL_TMPL.format(catoid=config.CATOID, poid=poid)
            dest = config.RAW_PROGRAM / f"{poid}.html"
            print(f"  [{i}/{len(targets)}] poid={poid} ({tier}) {name[:50]}")
            self.fetch(url, dest, "program", poid=poid, tier=tier, name=name)

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fetch UAlberta catalogue/calendar HTML into corpus/raw/.")
    ap.add_argument("--module", choices=["courses", "programs", "all"], default="all")
    ap.add_argument("--mode", choices=["gold", "silver"], default="gold", help="program tier to fetch")
    ap.add_argument("--term", default="all", help="informational; live pages already carry all terms")
    ap.add_argument("--subjects", default=None, help="comma-separated subject codes to limit the course crawl")
    ap.add_argument("--limit", type=int, default=None, help="max courses per subject (testing)")
    ap.add_argument("--max-programs", type=int, default=None, help="cap silver program count")
    ap.add_argument("--force", action="store_true", help="ignore the cache/manifest and refetch")
    args = ap.parse_args(argv)

    util.ensure_dirs()
    manifest = {} if args.force else util.load_manifest()
    subjects_filter = (
        {s.strip().lower() for s in args.subjects.split(",") if s.strip()} if args.subjects else None
    )

    if args.module in ("courses", "all"):
        cf = CourseFetcher(manifest, args.force)
        try:
            cf.crawl(subjects_filter, args.limit)
        finally:
            cf.close()
        print(f"[courses] fetched={cf.fetched} skipped={cf.skipped} failed={len(cf.failed)}")
        for u, why in cf.failed[:20]:
            print(f"    FAIL {why}: {u}")

    if args.module in ("programs", "all"):
        with ProgramFetcher(manifest, args.force) as pf:
            pf.crawl(args.mode, args.max_programs)
        print(f"[programs] fetched={pf.fetched} skipped={pf.skipped} failed={len(pf.failed)}")
        for u, why in pf.failed[:20]:
            print(f"    FAIL {why}: {u}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
