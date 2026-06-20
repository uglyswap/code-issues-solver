import pytest
from browser.app.driver import PlaywrightDriver


@pytest.mark.asyncio
async def test_driver_lifecycle():
    driver = PlaywrightDriver()
    await driver.start(headless=True)
    assert driver.page is not None
    await driver.goto("about:blank")
    assert driver.page.url == "about:blank"
    await driver.stop()
