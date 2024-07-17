import re
import time
from dotenv import load_dotenv
import asyncio
import os, argparse
import pandas as pd
from playwright_stealth import stealth_async
from playwright.async_api import Playwright, async_playwright, Page, BrowserContext


class LINKEDIN_GROUP_POST:
    def __init__(self) -> None:
        self.base_url = "https://www.linkedin.com"
        self.url = "https://www.linkedin.com/login?fromSignIn=true"
        self.current_path = os.path.dirname(os.path.realpath(__file__))
        self.urls_df = pd.read_excel(os.path.join(self.current_path,"LINKEDIN_GROUP_URL.xlsx"))
        self.urls_df = self.urls_df.fillna("")
        self.urls_df = self.urls_df[self.urls_df["GROUP URL"] != ""]
        self.urls_df = self.urls_df[self.urls_df["INCLUDE"] == "YES"]
        load_dotenv(dotenv_path=f"{self.current_path}/CREDENTIALS/.env")
        self.page:Page = None
        self.playwright:Playwright = None
        self.context: BrowserContext = None
        self.email = os.environ["EMAIL"]
        self.password = os.environ["PASSWORD"]
        self.group_url = ""
        self.group_url_id = ""
        self.keywords = []
        
        self.filter_list = {"SECOND":1,"MINUTE":2,"HOUR":3,"DAY":4,"WEEK":5,"MONTH":6,"YEAR":7}
        self.filter_to = 0
        self.filter_from = 0
        self.post_count_to_scrape = None
        self.filter_by = None
        self.current_last_post_date = ""
        self.current_post_date = ""
        self.headless = False
        self.previous_post_date = ""

    async def generate_post_link(self,post_id):
        if post_id == "" or post_id == None:
            return None
        return f"https://www.linkedin.com/feed/update/{post_id}/"
    
    async def linkedin_login(self):
        success = False
        while not success:
            try:
                await self.page.goto(self.url)
                await self.page.wait_for_load_state("domcontentloaded",timeout=100000)
                Email = await self.page.locator('[id="username"]').all()
                if len(Email)>0:
                    await self.page.locator('[id="username"]').evaluate('(element) => element.value = ""')
                    await self.page.locator('[id="username"]').fill(self.email)
                Password = await self.page.locator('[id="password"]').all()
                if len(Password)>0:
                    await self.page.locator('[id="password"]').evaluate('(element) => element.value = ""')
                    await self.page.locator('[id="password"]').fill(self.password)
                await self.page.locator('button[aria-label="Sign in"]').click()
                await self.page.wait_for_load_state("domcontentloaded",timeout=100000)
                await self.page.wait_for_timeout(7000)
                title = await self.page.title()
                while "Security Verification" in title.strip():
                    await self.page.wait_for_timeout(2000)
                    title = await self.page.title()
                    print("Title",title)
                if "Feed" in title.strip() or "LinkedIn" == title.strip() or "feed" in self.page.url:
                    success = True
                    break
            except Exception as e:
                print(e)
                time.sleep(5)
                continue
        return True
                
    
    async def _scroll_to_last_post(self,all_posts):
        no_post_counter = 0
        completed = False
        previous_posts_view = []
        total_post_view = []
        
        while not completed:
            try:
                previous_posts_view = total_post_view.copy()
                await self.page.wait_for_selector('//div[@class="scaffold-finite-scroll__content"]/div/div',timeout=100000)
                new_posts = await self.page.locator('//div[@class="scaffold-finite-scroll__content"]/div/div').all()
                total_post_view = await self.page.locator('[class="scaffold-finite-scroll__content"] [class*="feed-shared-update-v2 feed-shared-update-v2"]').all()
                new_posts_view = total_post_view[len(previous_posts_view):]
                for post_view in new_posts_view:
                    await self.page.mouse.wheel(0, 400)
                    await self.page.mouse.wheel(0, 400)
                    post_id = await post_view.get_attribute("data-urn")
                    post_id = re.findall(r'\d+',post_id)[0]
                    if all_posts.get(post_id) is None:
                        
                        pinned = await post_view.locator('[type="pin-fill"]').all()
                        if pinned:
                            all_posts[post_id] = post_view
                            print("PINNED POST",post_id)
                        else:
                            try:
                                #//span[contains(text() ,"ago")]
                                last_post_date = await post_view.locator('//span[contains(text() ,"ago")]').all()
                                if last_post_date:
                                    last_post_date = await post_view.locator('//span[contains(text() ,"ago")]').first.inner_text()
                                    last_post_date = last_post_date.strip()
                                    date = re.findall(r'\d+',last_post_date)
                                    filter_by = last_post_date.split(" ")[1].upper()
                                    if filter_by.endswith("S"):
                                        filter_by = filter_by[:-1]
                                    if self.filter_list.get(filter_by) > self.filter_list.get(self.filter_by):
                                        completed = True
                                        break
                                    elif self.filter_list.get(filter_by) == self.filter_list.get(self.filter_by):
                                        if len(date) != 0:
                                            if self.filter_to not in [0,None,""] and self.filter_from not in [None,""]:  
                                                if int(date[0])  > self.filter_to:
                                                    completed = True
                                                    break
                                                elif int(date[0]) < self.filter_from:
                                                    continue
                                                else:
                                                    if self.post_count_to_scrape not in [0,None,""]:
                                                        if len(all_posts.keys()) > self.post_count_to_scrape:
                                                            print("Post Count Reached")
                                                            completed = True
                                                            break
                                                    if self.keywords != []:
                                                        post_content = await post_view.locator('[id="fie-impression-container"] [class="update-components-text relative update-components-update-v2__commentary "] > [class*="break-words"] > span[dir="ltr"]').all_inner_texts()
                                                        found = False
                                                        post_content = " ".join(post_content)
                                                        for keyword in self.keywords:
                                                            if keyword.lower() in post_content.lower():
                                                                found = True
                                                                break
                                                        if not found:
                                                            continue
                                                    all_posts[post_id] = post_view
                                                    no_post_counter = 0
                                                    print("POSTED DATE",last_post_date,post_id,int(date[0])  <= self.filter_to)
                                            elif self.post_count_to_scrape not in [0,None,""]:
                                                if self.keywords != []:
                                                    post_content = await post_view.locator('[id="fie-impression-container"] [class="update-components-text relative update-components-update-v2__commentary "] > [class*="break-words"] > span[dir="ltr"]').all_inner_texts()
                                                    found = False
                                                    post_content = " ".join(post_content)
                                                    for keyword in self.keywords:
                                                        if keyword.lower() in post_content.lower():
                                                            found = True
                                                            break
                                                    if not found:
                                                        continue
                                                all_posts[post_id] = post_view
                                                no_post_counter = 0
                                                print("POSTED DATE",last_post_date,post_id)
                                                if len(all_posts.keys()) > self.post_count_to_scrape:
                                                    print("Post Count Reached")
                                                    completed = True
                                                    break
                                            elif self.keywords != []:
                                                found = False
                                                post_content = await post_view.locator('[id="fie-impression-container"] [class="update-components-text relative update-components-update-v2__commentary "] > [class*="break-words"] > span[dir="ltr"]').all_inner_texts()
                                                post_content = " ".join(post_content)
                                                for keyword in self.keywords:
                                                    if keyword.lower() in post_content.lower():
                                                        found = True
                                                        break
                                                if not found:
                                                    print("Keyword Not Found",self.keywords,"POSTED DATE",last_post_date,post_id)
                                                    continue
                                                all_posts[post_id] = post_view
                                                no_post_counter = 0
                                                print("POSTED DATE",last_post_date,post_id)
                                            else:
                                                print("Invalid Filter From and Filter To")
                                    else:
                                        if self.post_count_to_scrape not in [0,None,""]:
                                            if len(all_posts.keys()) > self.post_count_to_scrape:
                                                print("Post Count Reached")
                                                completed = True
                                                break
                                        if self.keywords != []:
                                            post_content = await post_view.locator('[id="fie-impression-container"] [class="update-components-text relative update-components-update-v2__commentary "] > [class*="break-words"] > span[dir="ltr"]').all_inner_texts()
                                            post_content = " ".join(post_content)
                                            found = False
                                            for keyword in self.keywords:
                                                if keyword.lower() in post_content.lower():
                                                    found = True
                                                    break
                                            if not found:
                                                print("Keyword Not Found",self.keywords,"POSTED DATE",last_post_date,post_id)
                                                continue
                                        all_posts[post_id] = post_view
                                        no_post_counter = 0
                                        print("POSTED DATE",last_post_date,post_id)
                            except Exception as e:
                                print("Exception",e)
                                pass
                        
                await self.page.mouse.wheel(0, 400)
                await self.page.mouse.wheel(0, 400)
                show_more = await self.page.get_by_role("button",name="Show more results").all()
                if show_more:
                    await show_more[0].click()
                    await self.page.wait_for_load_state("domcontentloaded",timeout=100000)
                if len(new_posts) == 0:
                    no_post_counter += 1
                    time.sleep(2)
                    #Show more results
                    show_more = await self.page.get_by_role("button",name="Show more results").all()
                    if show_more:
                        print("Show More Results",no_post_counter)
                        await show_more[0].click()
                        await self.page.wait_for_load_state("domcontentloaded",timeout=100000)
                        await self.page.wait_for_timeout(5000)
                else:
                    no_post_counter = 0
                if no_post_counter >= 5:
                    completed = True
                    break
            except Exception as e:
                try:
                    show_more = await self.page.get_by_role("button",name="Show more results").all()
                    if show_more:
                        await show_more[0].click()
                        await self.page.wait_for_load_state("domcontentloaded",timeout=100000)
                        await self.page.wait_for_timeout(2000)
                    else:
                        await self.page.goto(self.page.url)
                        await self.page.wait_for_load_state("domcontentloaded",timeout=100000)
                        await self.page.wait_for_timeout(2000)
                    continue
                except Exception as e:
                    print(e)
                continue
        return all_posts
                   
    async def scrape_linkedin_group_post(self):
        for index,group in self.urls_df.iterrows():
            all_posts = {}
            group_url = group["GROUP URL"]
            group_url_id = re.findall(r'\d+',group_url)[0]
            completed = False
            while not completed:
                try:
                    if "/login" in self.page.url:
                        await self.linkedin_login()
                    else:
                        pass
                    await self.page.goto(group_url)
                    await self.page.wait_for_load_state("domcontentloaded",timeout=100000)
                    current_url = self.page.url
                    if current_url == group_url:
                        current_url = self.page.url
                        completed = True
                        break
                    else:
                        time.sleep(0.8)
                except Exception as e:
                    try:
                        time.sleep(5)
                        await self.page.evaluate('window.scrollTo(0, 0)')
                        await self.page.wait_for_load_state("domcontentloaded",timeout=100000)
                        await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                        await self.page.wait_for_load_state("domcontentloaded",timeout=100000)
                        continue
                    except Exception as e:
                        pass
                    
            if self.filter_list.get(group["FILTER_BY"]):
                self.filter_by = group["FILTER_BY"]
                if group["TO"] not in [0,None,""]:
                    self.filter_to = int(group["TO"])
                if group["FROM"] not in [None,""]:
                    self.filter_from = int(group["FROM"])
            if group["MAX POST COUNT"] not in [0,None,""]:
                self.post_count_to_scrape = int(group["MAX POST COUNT"])
            if group['KEYWORDS'] not in [None,""]:
                self.keywords = group['KEYWORDS']
                self.keywords = self.keywords.split(",")
                
            print("Scraping LinkedIn Group Post", self.page.url, "Filter By",self.filter_by,"Filter From",self.filter_from,"Filter To",self.filter_to,"Post Count To Scrape",self.post_count_to_scrape,"Keywords",self.keywords)
            completed = False
            while not completed:
                try:
                    all_posts = await self._scroll_to_last_post(all_posts)
                    completed = True
                    break
                except Exception as e:
                    print(e)
                
            completed = False
            while not completed:
                try:
                    if len(all_posts) == 0:
                        print("No Post Found")
                    else:
                        await self.scrape_posts_data(all_posts, group_url_id,group_url)
                    completed = True
                    break
                except Exception as e:
                    time.sleep(5)
                    continue
    
    async def scrape_posts_data(self,all_posts, group_url_id,group_url):
        success = False
        while not success:
            try:
                os.makedirs(os.path.join(self.current_path,"RESULT",str(group_url_id),"LINKEDIN_IMAGES"),exist_ok=True)
                df = pd.DataFrame(columns=["POST NUMBER","POST LINK","POST DATE","GROUP POSTER NAME","GROUP POSTER LINK","POST IMAGE","POST CONTENT","ORIGINAL POSTER","ORIGINAL POSTER LINK"])
                post_count = 0
                all_posts = dict(reversed(list(all_posts.items())))
                for key,post in all_posts.items():
                    completed = False
                    while not completed:
                        try:
                            post_id = await post.get_attribute("data-urn")
                            Feed_post_number = await post.locator('//div[@id="fie-impression-container"]/preceding-sibling::h2').inner_text()
                            post_link = await self.generate_post_link(post_id=post_id)
                            posted_Date = await post.locator('//span[contains(text() ,"ago")]').first.inner_text()
                            group_poster_name = await post.locator('[id="fie-impression-container"] [class="relative"] div[class*="update-components-actor__container"]>  a').get_attribute("aria-label")
                            group_poster_link = await post.locator('[id="fie-impression-container"] [class="relative"] div[class*="update-components-actor__container"]>  a').get_attribute("href")
                            group_poster_image = await post.locator('[class="relative"] button[class="update-components-image__image-link"]').all()
                            post_content = await post.locator('[id="fie-impression-container"] [class="update-components-text relative update-components-update-v2__commentary "] > [class*="break-words"] > span[dir="ltr"]').all_inner_texts()
                            post_content = [re.sub(r'<.*?>', '', i) for i in post_content]
                            post_content = " ".join(post_content)
                            post_content = re.sub(r'hashtag', '', post_content)
                            post_content = re.sub(r'&.*?;', '', post_content) # remove all html symbols except #
                            post_content = re.sub(r'\s+', ' ', post_content) # remove all extra spaces with single space
                            post_content = post_content.strip()
                            original_poster = await post.locator('[class*="content-wrapper artdeco-card"] [class*="update-components-actor__name"] [aria-hidden="true"]').all_inner_texts()
                            if original_poster:
                                original_poster = original_poster[0]
                            else:
                                original_poster = group_poster_name
                            original_poster_link = await post.locator('[class*="content-wrapper artdeco-card"] a[class*="actor__image relative"]').all()
                            if original_poster_link:
                                original_poster_link = await original_poster_link[0].get_attribute("href")
                            else:
                                original_poster_link = group_poster_link
                            
                            if group_poster_image:
                                while True:
                                    try:
                                        index_counter = 0
                                        for image in group_poster_image:
                                            #await image.scroll_into_view_if_needed()
                                            if len(group_poster_image) > 1:
                                                image_handler = f"_{str(index_counter)}"
                                                index_counter += 1
                                            else:
                                                image_handler = ""
                                            await image.screenshot(path=f"{self.current_path}/RESULT/{str(group_url_id)}/LINKEDIN_IMAGES/"+str(Feed_post_number)+f"{image_handler}.png")
                                            group_poster_image = f"{self.current_path}/RESULT/{str(group_url_id)}/LINKEDIN_IMAGES/"+str(Feed_post_number)+f"{image_handler}.png"
                                            
                                        break
                                    except Exception as e:
                                        await self.page.screenshot(path=f"{self.current_path}/RESULT/{str(group_url_id)}/LINKEDIN_IMAGES/"+str(Feed_post_number)+"error.png")
                            else:
                                group_poster_image = ""    
                            print(f"POSTED BY :{original_poster} POSTED AT: {posted_Date}")
                            
                            if len(post_link) > 2079:
                                post_link = post_link[:2076] + '...'
                            if len(original_poster_link) > 2079:
                                original_poster_link = original_poster_link[:2076] + '...'
                            if len(group_poster_link) > 2079:
                                group_poster_link = group_poster_link[:2076] + '...'
                            post_id = re.findall(r'\d+',post_id)[0]
                            df = pd.concat([df,pd.DataFrame([[Feed_post_number,post_link,posted_Date,group_poster_name,group_poster_link,group_poster_image,post_content,original_poster,original_poster_link,post_id,group_url_id,group_url]],columns=["POST NUMBER","POST LINK","POST DATE","GROUP POSTER NAME","GROUP POSTER LINK","POST IMAGE","POST CONTENT","ORIGINAL POSTER","ORIGINAL POSTER LINK","POST ID","GROUP URL ID","GROUP URL"])],ignore_index=True)
                            post_count += 1
                            break
                        except Exception as e:
                            print("outer",e)
                
                df = df.iloc[::-1]
                df.to_excel(f"RESULT/{str(group_url_id)}/linkedin_group_post.xlsx",index=False)
                if df.shape[0] == 1:
                    os.remove(f"RESULT/{str(group_url_id)}/linkedin_group_post.xlsx")
                    print("No Post Found")
                else:
                    print("Post Count",post_count)
                success = True
                break
            except Exception as e:
                print(e)
                time.sleep(5)
                continue
        
    async def main(self):
        
        async with async_playwright() as self.playwright:
            if not os.path.exists(os.path.join(self.current_path,"CREDENTIALS","linkedin.json")):
                self.context = await self.playwright.chromium.launch_persistent_context(java_script_enabled=True,user_data_dir="USER_DATA_DIR",headless=self.headless)
                await self.context.storage_state(path=os.path.join(self.current_path,"CREDENTIALS","linkedin.json"))
                while True:
                    try:
                        if self.context.pages:
                            self.page = self.context.pages[0]
                        else:
                            self.page = await self.context.new_page()
                        await stealth_async(self.page)
                        await self.page.goto(self.base_url,timeout=100000,wait_until="domcontentloaded")
                        await self.page.wait_for_load_state("load",timeout=100000)
                        await self.page.wait_for_load_state("domcontentloaded",timeout=100000)
                        await self.page.wait_for_timeout(5000)
                        break
                    except Exception as e:
                        print(e)
                        continue
                title = await self.page.title()
                if "LinkedIn" in title.strip() or "feed" in self.page.url:
                    pass
                else:
                    await self.linkedin_login()
                await self.context.storage_state(path=os.path.join(self.current_path,"CREDENTIALS","linkedin.json"))
                await self.scrape_linkedin_group_post()
                
            else:
                self.context = await self.playwright.chromium.launch_persistent_context(java_script_enabled=True,user_data_dir="USER_DATA_DIR",headless=self.headless)
                if self.context.pages:
                    self.page = self.context.pages[0]  
                else:
                    self.page = await self.context.new_page()
            # await self.page.on("dialog", lambda dialog: asyncio.ensure_future(dialog.dismiss()))
            await stealth_async(self.page)
            await self.scrape_linkedin_group_post()
            await self.context.storage_state(path=os.path.join(self.current_path,"CREDENTIALS","linkedin.json"))
            await self.context.close()
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Linkedin Group Post Scraper')
    parser.add_argument('--headless', type=bool, help='Launch Browser in Headless Mode',default=False)
    args = parser.parse_args()
    linkedin = LINKEDIN_GROUP_POST()
    if args.headless:
        linkedin.headless = args.headless
   
    asyncio.run(linkedin.main())
    
# python LinkedIn_main.py --headless True
# python LinkedIn_main.py --headless False
