
from __future__ import annotations

from playwright.sync_api import Page, expect


def open_nav(page: Page, value: str, *, group: str | None = None) -> None:
    """Open a Studio module by its stable Shiny data-value contract.

    Human-facing labels are intentionally free to evolve. Dropdown modules first
    open their product-level navigation group, then activate the stable module ID.
    """
    nav = page.locator("#main_nav")
    link = nav.locator(f'a[data-value="{value}"]')
    if group is not None and not link.is_visible():
        nav.get_by_text(group, exact=True).click()
        expect(link).to_be_visible(timeout=10_000)
    expect(link).to_be_visible(timeout=10_000)
    link.click()
