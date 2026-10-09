#!/usr/bin/env python3
"""Screenshots with headless Chromium (Playwright).
Usage: python3 screenshots.py [BASE_URL] [PREFIX]
  local: (cd docs && python3 -m http.server 8765) & python3 screenshots.py http://127.0.0.1:8765/ local
  live:  python3 screenshots.py https://theodoruszq.github.io/x-digest/ live
"""
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/"
PREFIX = sys.argv[2] if len(sys.argv) > 2 else "local"
OUT = Path(__file__).resolve().parent / "screenshots"
OUT.mkdir(exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 900}, device_scale_factor=2, color_scheme="light")
    pg = ctx.new_page()
    pg.goto(BASE); pg.wait_for_load_state("networkidle")
    pg.screenshot(path=OUT / f"{PREFIX}-desktop-home.png")
    day = pg.locator(".day-entry h2 a").first.get_attribute("href")
    pg.goto(BASE + day); pg.wait_for_load_state("networkidle")
    fonts = pg.evaluate("[...document.fonts].filter(f => f.family.includes('Lato')).map(f => f.weight + ':' + f.status)")
    print("Lato font faces:", fonts, "| check Lato 400:", pg.evaluate("document.fonts.check('16px Lato')"))
    pg.screenshot(path=OUT / f"{PREFIX}-desktop-day.png")
    pg.click("[data-toggle-zh]"); pg.wait_for_timeout(200)
    pg.screenshot(path=OUT / f"{PREFIX}-desktop-day-glosses-on.png")
    pg.evaluate("window.scrollTo(0, document.querySelector('#p8').offsetTop - 20)")
    pg.screenshot(path=OUT / f"{PREFIX}-desktop-day-glosses-on-scrolled.png")
    pg.reload(); pg.wait_for_load_state("networkidle")
    print("glosses remembered after reload:", pg.evaluate("document.documentElement.classList.contains('show-zh')"))
    ctx.close()
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, color_scheme="dark", is_mobile=True, has_touch=True)
    pg = ctx.new_page()
    pg.goto(BASE + day); pg.wait_for_load_state("networkidle")
    pg.screenshot(path=OUT / f"{PREFIX}-mobile-dark-day.png")
    pg.tap("[data-toggle-zh]"); pg.wait_for_timeout(200)
    pg.evaluate("window.scrollTo(0, document.querySelector('#p6').offsetTop - 10)")
    pg.screenshot(path=OUT / f"{PREFIX}-mobile-dark-day-glosses-on.png")
    b.close()
print("saved to", OUT)
