import asyncio
from playwright.async_api import async_playwright

async def verify_notifications():
    async with async_playwright() as p:
        # Launching browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("Logging into eCourse2...")
        try:
            await page.goto("https://ecourse2.ccu.edu.tw/login/index.php")
            
            # Use the "Other Users" login locators identified from HTML
            await page.fill("#username_temp", "ccu414410903")
            await page.fill("#password", "Hari@2004")
            await page.click("#submit")
            await page.wait_for_load_state("networkidle")
            
            # Check if login was successful by looking for a logout link or dashboard element
            if await page.locator(".logininfo").get_by_text("Logout").count() == 0:
                 # Check the specific text "You are logged in as"
                 if "You are logged in as" not in await page.content():
                    print("Login failed. Please check credentials or portal status.")
                    await browser.close()
                    return

            print("Navigating to Notifications...")
            await page.goto("https://ecourse2.ccu.edu.tw/message/output/popup/notifications.php")
            
            # Wait for dynamic content to load
            notification_selector = "div[data-region='notification-content-item-container']"
            await page.wait_for_selector(notification_selector, timeout=15000)

            print("\nNotifications from the last 3 days:")
            print("-" * 50)

            notifications = await page.locator(notification_selector).all()
            found_any = False
            
            for item in notifications:
                try:
                    title = await item.locator(".notification-message").inner_text()
                    timestamp_elem = item.locator(".timestamp")
                    
                    if await timestamp_elem.count() > 0:
                        timestamp = await timestamp_elem.inner_text()
                    else:
                        timestamp = "Unknown time"

                    # Simple filter for last 3 days
                    if "day" in timestamp.lower():
                        parts = timestamp.lower().split("day")
                        try:
                            days_val = int(parts[0].strip())
                            if days_val > 3:
                                continue
                        except ValueError:
                            # Might be "a day ago" or similar
                            pass
                    
                    print(f"[{timestamp}] {title.strip()}")
                    found_any = True
                except Exception as e:
                    continue

            if not found_any:
                print("No notifications found within the last 3 days.")

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_notifications())
