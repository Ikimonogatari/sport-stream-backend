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
from flask import Flask
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

mongolia_tz = pytz.timezone('Asia/Ulaanbaatar')

db: SQLAlchemy = None
app: Flask = None


def get_live_links(driver, match_url):
    links = []
    driver.get(match_url)
    try:
        contentDiv = WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.ID, 'content-event')))
        l_list = contentDiv.find_elements(By.TAG_NAME, 'a')
        for l in l_list:
            links.append(l.get_attribute('href'))
    except Exception as e:
        print("An error occurred:", e, file=sys.stderr)
    return links

def get_stream_sources(driver, links):
    sources = []
    for link in links:
        driver.get(link)
        try:
            contentDiv = WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.CLASS_NAME, 'box-responsive')))
            
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

def update_live_status(db: SQLAlchemy):
    print("Starting to update live matches", file=sys.stderr)

    with app.app_context():
        try:
            current_time_mongolia = datetime.now(mongolia_tz)
            current_time_mongolia = current_time_mongolia.replace(microsecond=0).replace(tzinfo=None)
            matches_to_update = Matches.query.filter(
                Matches.datetime <= current_time_mongolia,
                Matches.isLive == False
            ).all()

            print("Matches to update", matches_to_update, file=sys.stderr)
            
            for match in matches_to_update:
                match.isLive = True
                match.last_crawl_time = current_time_mongolia
                db.session.commit()
                logger.info(f"Updated match {match.id} to live and set last crawl time.")
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error occurred while updating live status: {str(e)}")


def main(db: SQLAlchemy, app: Flask):
    update_live_status(db)

    print("Updated live matches", file=sys.stderr)

    current_time_mongolia = datetime.now(mongolia_tz)
    thirty_minutes_ago = current_time_mongolia - timedelta(minutes=15)

    with app.app_context():
        chrome_driver_path = chromedriver_autoinstaller.install()
        chrome_options = Options()
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--proxy-bypass-list=*")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-browser-side-navigation")

        service = Service(executable_path=chrome_driver_path)

        with webdriver.Chrome(service=service, options=chrome_options) as driver:
            live_matches = db.session.query(Matches).filter(
                Matches.isLive == True,
                Matches.last_crawl_time >= thirty_minutes_ago
            ).all()
            print("Live matches to query", live_matches, file=sys.stderr)
            for match in live_matches:
                stream_links = get_live_links(driver, match.link)
                stream_sources = get_stream_sources(driver, stream_links)
                for source in stream_sources:
                    existing_source = db.session.query(StreamSources).filter_by(match_id=match.id, link=source).first()
                    if not existing_source:
                        stream_source = StreamSources(match_id=match.id, link=source)
                        db.session.add(stream_source)

        db.session.commit()
        db.session.close()

def main_loop(appArg: Flask, dbArg: SQLAlchemy):
    global db, app
    app = appArg
    db = dbArg
    print(f"Running stream source crawler at {datetime.now(mongolia_tz)}", file=sys.stderr)
    scheduler.add_job(main, 'interval', minutes=5, args=[db, app])
    scheduler.start()
