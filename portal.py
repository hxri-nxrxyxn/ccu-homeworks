import asyncio
from playwright.async_api import async_playwright
from config import PORTAL_USERNAME, PORTAL_PASSWORD

class CoursePortal:
    def __init__(self, headless=True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def stop(self):
        await self.browser.close()
        await self.playwright.stop()

    async def login(self):
        print("Logging into eCourse2...")
        await self.page.goto("https://ecourse2.ccu.edu.tw/login/index.php")
        await self.page.fill("#username_temp", PORTAL_USERNAME)
        await self.page.fill("#password", PORTAL_PASSWORD)
        await self.page.click("#submit")
        await self.page.wait_for_load_state("networkidle")
        
        content = await self.page.content()
        if "You are logged in as" not in content:
            raise Exception("Login failed. Check credentials.")
        print("Login successful.")

    async def fetch_notifications(self, last_n_days=3):
        """Scrapes notifications and returns titles/links."""
        await self.page.goto("https://ecourse2.ccu.edu.tw/message/output/popup/notifications.php")
        
        selector = "div[data-region='notification-content-item-container']"
        await self.page.wait_for_selector(selector, timeout=15000)
        
        notifications = await self.page.locator(selector).all()
        results = []
        
        for item in notifications:
            title = await item.locator(".notification-message").inner_text()
            timestamp = await item.locator(".timestamp").inner_text()
            
            # Simplified filtering
            if "day" in timestamp.lower():
                days = int(timestamp.lower().split("day")[0].strip())
                if days > last_n_days: continue
                
            results.append({
                "title": title.strip(),
                "time": timestamp,
                "element": item
            })
        return results

    async def get_assignment_prompt(self, notification_element):
        """Clicks a notification and extracts the prompt from the right pane."""
        await notification_element.click()
        prompt_selector = "div[data-region='content-area'] div[data-region='content']"
        await self.page.wait_for_selector(prompt_selector)
        await asyncio.sleep(1) # Allow for dynamic rendering
        raw_text = await self.page.inner_text(prompt_selector)
        return raw_text.split("See this post in context")[0].strip()

    async def submit_assignment(self, assignment_url, pdf_path):
        """TODO: Implement after user provides Submission Page HTML."""
        pass
