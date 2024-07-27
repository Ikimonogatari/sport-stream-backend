from flask_sqlalchemy import SQLAlchemy
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from models import StreamSources, Matches
from datetime import datetime, timedelta
import chromedriver_autoinstaller
import sys
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

db: SQLAlchemy = None
app: Flask = None


def get_live_links(driver, match_url):
    links = []
    driver.get(match_url)
    try:
        contentDiv = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'content-event')))
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
            contentDiv = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'box-responsive')))
            
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
    print("CRAWLER 3 HERE", file=sys.stderr)
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
            live_matches = db.session.query(Matches).filter(Matches.isLive == True).all()
            print("sources live matches", live_matches, file=sys.stderr)

            for match in live_matches:
                stream_links = get_live_links(driver, match.link)  # Ensure match has a 'url' attribute
                stream_sources = get_stream_sources(driver, stream_links)  # Get stream sources from links
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
    print(f"Running stream source crawler 3 at {datetime.now()}", file=sys.stderr)
    scheduler.add_job(main, 'interval', minutes=1, args=[db, app])
    scheduler.start()
