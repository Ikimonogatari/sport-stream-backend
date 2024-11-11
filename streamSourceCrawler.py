from flask_sqlalchemy import SQLAlchemy
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from models import StreamSources, Matches
from datetime import datetime, timedelta
import pytz
import chromedriver_autoinstaller
import sys
from apscheduler.schedulers.background import BackgroundScheduler
import random
import requests
SCRAPER_API_KEY = '6be10ab64669a2f166584ccf985109c6'
scraper_api_url = "http://api.scraperapi.com"   

from flask import Flask
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

mongolia_tz = pytz.timezone('Asia/Ulaanbaatar')

db: SQLAlchemy = None
app: Flask = None

def parse_datetime_string(datetime_str):
    # Parse the string into a datetime object, assuming it is in GMT
    return datetime.strptime(datetime_str, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=pytz.UTC)

def filter_valid_links(links):
    unwanted_substrings = ["adobe", "get.adobe.com"]
    valid_links = [link for link in links if not any(sub in link for sub in unwanted_substrings)]
    return valid_links

def get_live_links(driver, match_url):
    links = []
    driver.get(match_url)
    try:
        contentDiv = WebDriverWait(driver, 0).until(EC.presence_of_element_located((By.ID, 'links_block')))
        l_list = contentDiv.find_elements(By.TAG_NAME, 'a')
        for l in l_list:
            links.append(l.get_attribute('href'))
        links = list(set(links))  # Remove duplicates
        links = filter_valid_links(links)  # Filter out unwanted links
        if not links:
            print(f"No valid stream links found for {match_url}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"An error occurred while fetching links from {match_url}: {e}", file=sys.stderr)
        return None
    return links

def get_stream_sources(driver, links):
    sources = []
    for link in links:
        driver.get(link)
        try:
            contentDiv = WebDriverWait(driver, 0).until(EC.presence_of_element_located((By.CLASS_NAME, 'box-responsive')))
            
            video_src = None
            iframe_src = None
            
            video_elements = contentDiv.find_elements(By.TAG_NAME, 'video')
            if video_elements:
                video_src = video_elements[0].get_attribute('src')
            
            if not video_src:
                iframe_elements = contentDiv.find_elements(By.TAG_NAME, 'iframe')
                if iframe_elements:
                    iframe_src = iframe_elements[0].get_attribute('src')
            
            if video_src:
                sources.append(video_src)
            elif iframe_src:
                sources.append(iframe_src)

        except Exception as e:
            print("An error occurred:", e, file=sys.stderr)
    return sources

def main(db: SQLAlchemy, app: Flask):

    chrome_driver_path = chromedriver_autoinstaller.install()
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--proxy-bypass-list=*")
    chrome_options.add_argument("--disable-browser-side-navigation")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument('--no-zygote')
    chrome_options.add_argument("--disable-gpu") 
    target_url = 'https://sportshub.stream'
    proxy = f"{scraper_api_url}?api_key={SCRAPER_API_KEY}&url={target_url}"
    chrome_options.add_argument(f'--proxy-server={proxy}')
    
    service = Service(executable_path=chrome_driver_path)

    with app.app_context():
        driver = None
        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
            live_matches_to_update = db.session.query(Matches).filter(
                Matches.isLive == True,
            ).all()
            print("Live matches to update", live_matches_to_update, file=sys.stderr)
            for match in live_matches_to_update:
                try:
                    current_time_mongolia = datetime.now(mongolia_tz).replace(microsecond=0, tzinfo=None)
                    match_age = current_time_mongolia - match.datetime

                    if match_age > timedelta(hours=3):
                        db.session.query(StreamSources).filter_by(match_id=match.id).delete()  # Bulk delete
                        print(f"Deleted stream source for match {match.id}", file=sys.stderr)
                        db.session.delete(match)
                        print(f"Deleted match {match.id} {match.team1name} due to being older than 2 hours and having no stream links.", file=sys.stderr)

                    elif timedelta(minutes=40) < match_age < timedelta(hours=2):
                        stream_links = get_live_links(driver, match.link)

                        if stream_links is None:
                            existing_sources = db.session.query(StreamSources).filter_by(match_id=match.id).all()
                            for source in existing_sources:
                                db.session.delete(source)
                                print(f"Deleted stream source: {source.link} for match {match.team1name}", file=sys.stderr)
                            db.session.delete(match)
                            print(f"Deleted match {match.id} {match.team1name}", file=sys.stderr)

                    elif match_age > timedelta(hours=2):
                        stream_links = get_live_links(driver, match.link)
                        
                        if stream_links is not None and len(stream_links) <= 1:
                            existing_sources = db.session.query(StreamSources).filter_by(match_id=match.id).all()
                            for source in existing_sources:
                                db.session.delete(source)
                                print(f"Deleted stream source: {source.link} for match {match.team1name}", file=sys.stderr)
                            db.session.delete(match)
                            print(f"Deleted match {match.id} {match.team1name}", file=sys.stderr)
                except Exception as e:
                    db.session.rollback()  # Rollback only for current iteration if needed
                    logger.error(f"Error processing match {match.id} ({match.team1name}): {str(e)}")
                else:
                    db.session.commit()

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error occurred during the main function: {str(e)}")
        finally:
            if driver:
                driver.quit()  
            db.session.close()  

def main_loop(appArg: Flask, dbArg: SQLAlchemy):
    global db, app
    app = appArg
    db = dbArg
    # main(db, app)
    # scheduler.add_job(main, 'interval', minutes=5, args=[db, app])
    # scheduler.start()
