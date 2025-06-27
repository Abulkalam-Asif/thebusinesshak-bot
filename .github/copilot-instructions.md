# The client's requirements:

This Bot is meant to:

- Open Chrome, Firefox, Edge browsers in random order
- Clear all cache/cookies/data from browser
- Select a random FRENCH proxy from Oxylabs (should be revolving proxies) - new IP every time.
- Then Either visit our provided URLS (7) directly or Search for our keyword on Google, from provided list and then click through to 1 of the 7 URLS
- When on the site, Mimic advanced and complex human interactions like random clicks on the page, mouse movements, clicks on links and advanced human scrolling ect
- It should stay on the page for random times everytime between 25 - 90 seconds.
- It should make clicks random in session from 0-4 clicks - random in every session.
- Then it should close the browser and delete all data.
- Following every 50 Completed sessions it should generate an advanced report in PDF format that is exported to a folder on our desktop. The report should have detailed reporting about each session in bullet point format.
- The bot should be set up to randomly run between - 550 - 700 sessions per day. And should randomly change the amount per day.
- The bot by default should run between French hours of 8am - 22:00. But upon launching the bot, we should be asked if we wish to run outside of French hours, with a Y/N , if we say Y the bot should override the french hours and run.
- Use Advanced - Anti Detection Measures and Avoid digital Fingerprints
- Look like real human behaviour
- Run all in Headless Mode
-
- When the bot is running it should show the following information for each session:
-
- Session Number 001/700 (this will change with each session and depending on total sessions for the day)
- Browser : Google, Firefox etc
- IP address: Shown chosen IP Address
- IP Location: Paris, France - Show location
- Web Route: Google or Direct
- URL or Keywords: use form provided depending on what is chosen
- Other URLs visited : if a click though is done then record the url t takes you to
- Time on target URL : report the time spent on the URL for this session
- Clicks: record the number of click executed in this session
- Session , Success / No Success
- If no Success Reason for failing


# Visit Modes

- Direct: Visit 1 of 7 target URLs
- Search: Google search for keywords → Click through to target URLs
- Target URLs:
1. https://www.thebusinesshack.com/hire-a-pro-france  
2. https://www.mindyourbiz.online/find-a-pro_france  
3. https://www.arcsaver.com/find-a-pro  
4. https://www.le-trades.com/find-trades  
5. https://www.batiexperts.com/trouver-des-artisans  
6. https://www.trouveun.pro/  
7. https://www.cherche-artisan.com

- Google Searches: any web pages from the above - BUt, Must go to target website - via gooogle

# Additional Notes:
- Python
- Playwright