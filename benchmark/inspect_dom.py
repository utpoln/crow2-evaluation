"""One-off DOM inspection helper: loads a real URL headlessly and prints
candidate repeating-row containers so we can hand-author accurate row/column
XPath for the benchmark wrapper configs (same positional/class style a human
CroW user would produce via the two-click tool + optional manual refinement).
Not part of the reproducibility package; a throwaway authoring aid.
"""
import asyncio, sys
from playwright.async_api import async_playwright

async def main(url, candidates):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3000)
        for sel in candidates:
            count = await page.locator(sel).count()
            print(f"{sel!r}: {count} matches")
            if count:
                html = await page.locator(sel).first.evaluate("el => el.outerHTML.slice(0, 600)")
                print("  sample:", html.replace("\n", " ")[:600])
        await browser.close()

if __name__ == "__main__":
    url = sys.argv[1]
    candidates = sys.argv[2:]
    asyncio.run(main(url, candidates))
