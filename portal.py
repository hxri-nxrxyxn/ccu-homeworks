import asyncio
import os
from playwright.async_api import async_playwright
from config import PORTAL_USERNAME, PORTAL_PASSWORD

class CoursePortal:
    def __init__(self, headless=True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def login(self):
        print("logging into ecourse2...")
        await self.page.goto("https://ecourse2.ccu.edu.tw/login/index.php")
        await self.page.fill("#username_temp", PORTAL_USERNAME)
        await self.page.fill("#password", PORTAL_PASSWORD)
        await self.page.click("#submit")
        await self.page.wait_for_load_state("networkidle")
        
        content = await self.page.content()
        if "You are logged in as" not in content:
            raise Exception("login failed. check credentials.")
        print("login successful.")

    async def fetch_notifications(self, last_n_days=3):
        """scrapes notifications and returns titles/links."""
        await self.page.goto("https://ecourse2.ccu.edu.tw/message/output/popup/notifications.php")
        
        selector = "div[data-region='notification-content-item-container']"
        await self.page.wait_for_selector(selector, timeout=15000)
        
        notifications = await self.page.locator(selector).all()
        results = []
        
        for item in notifications:
            title = await item.locator(".notification-message").inner_text()
            timestamp = await item.locator(".timestamp").inner_text()
            
            if "day" in timestamp.lower():
                parts = timestamp.lower().split("day")
                try:
                    days = int(parts[0].strip())
                    if days > last_n_days: continue
                except: pass
                
            results.append({
                "title": title.strip(),
                "time": timestamp,
                "element": item,
                "id": await item.get_attribute("data-id")
            })
        return results

    async def get_assignment_prompt(self, notification_element):
        """clicks a notification and extracts prompt and course/assignment info."""
        await notification_element.click()
        prompt_selector = "div[data-region='content-area'] div[data-region='content']"
        await self.page.wait_for_selector(prompt_selector)
        await asyncio.sleep(1)
        
        # extract prompt text
        raw_text = await self.page.inner_text(prompt_selector)
        prompt = raw_text.split("See this post in context")[0].strip()
        
        # attempt to extract the course/module link to find the assignment id
        # moodle notifications usually have a footer link "Go to: [Assignment Name]"
        link_elem = self.page.locator("div[data-region='footer'] a")
        assignment_url = await link_elem.get_attribute("href") if await link_elem.count() > 0 else None
        
        return {
            "prompt": prompt,
            "url": assignment_url
        }

    async def upload_and_submit(self, assignment_url: str, pdf_path: str):
        """navigates to submission page, uploads file, and clicks save."""
        if not assignment_url:
            raise Exception("no assignment url found to submit to.")

        # ensure it's the editsubmission page
        if "action=editsubmission" not in assignment_url:
            if "?" in assignment_url:
                assignment_url += "&action=editsubmission"
            else:
                assignment_url += "?action=editsubmission"

        print(f"navigating to submission: {assignment_url}")
        await self.page.goto(assignment_url)
        await self.page.wait_for_load_state("networkidle")

        # 1. click the 'Add file' icon (plus sign)
        await self.page.click(".fp-btn-add a")
        
        # 2. handle the file picker dialog
        # wait for the 'Upload a file' tab (usually active by default, but let's be safe)
        upload_tab = self.page.locator("span.fp-repo-name:has-text('Upload a file')")
        if await upload_tab.count() > 0:
            await upload_tab.click()

        # 3. set the file in the hidden input
        file_input = self.page.locator("input[type='file']")
        await file_input.set_input_files(pdf_path)

        # 4. click 'Upload this file'
        await self.page.click("button.fp-upload-btn")
        
        # 5. wait for upload to draft area to finish (dialog disappears)
        await self.page.wait_for_selector(".fp-upload-form", state="hidden")

        # 6. click 'Save changes'
        await self.page.click("#id_submitbutton")
        await self.page.wait_for_load_state("networkidle")
        
        print("submission completed successfully.")
