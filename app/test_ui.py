import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            viewport={'width': 414, 'height': 896},
            is_mobile=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        )
        
        errors = []
        page.on("pageerror", lambda err: errors.append(err))
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)
        
        await page.goto("file:///d:/weedverso/index.html")
        await page.wait_for_timeout(2000)
        
        # Click on credit card tab to force render of credit chart too
        try:
            await page.click('button[data-page="credit"]')
            await page.wait_for_timeout(1000)
        except:
            pass
        
        await page.screenshot(path="screenshot.png", full_page=True)
        await browser.close()
        
        if errors:
            print("ERRORS FOUND:")
            for e in errors:
                print(e)
        else:
            print("No errors! Screenshot saved to screenshot.png")

asyncio.run(run())
