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
        contentDiv = WebDriverWait(driver, 0).until(EC.presence_of_element_located((By.ID, 'content-event')))
        l_list = contentDiv.find_elements(By.TAG_NAME, 'a')
        for l in l_list:
            links.append(l.get_attribute('href'))
        if not links:  # No links found
            return None
    except Exception as e:
        print("An error occurred:", e, file=sys.stderr)
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
    thirty_minutes_ago = current_time_mongolia - timedelta(minutes=60)
    ninety_minutes_ago = current_time_mongolia - timedelta(minutes=90)

    chrome_driver_path = chromedriver_autoinstaller.install()
    chrome_options = Options()
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--proxy-bypass-list=*")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-browser-side-navigation")

    service = Service(executable_path=chrome_driver_path)

    with app.app_context():
        driver = None
        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
            live_matches_to_update = db.session.query(Matches).filter(
                Matches.isLive == True,
                Matches.last_crawl_time >= thirty_minutes_ago
            ).all()
            print("Live matches to update", live_matches_to_update, file=sys.stderr)
            for match in live_matches_to_update:
                stream_links = get_live_links(driver, match.link)
                if stream_links:
                    stream_sources = get_stream_sources(driver, stream_links)
                    print(f"Match {match.id} stream sources: {stream_sources}", file=sys.stderr)
                    if stream_sources:
                        for source in stream_sources:
                            existing_source = db.session.query(StreamSources).filter_by(match_id=match.id, link=source).first()
                            if not existing_source:
                                stream_source = StreamSources(match_id=match.id, link=source)
                                db.session.add(stream_source)
                    else:
                        existing_sources = db.session.query(StreamSources).filter_by(match_id=match.id).all()
                        if existing_sources:
                            for source in existing_sources:
                                db.session.delete(source)
                                print(f"Deleted stream source: {source.link} for match {match.id}", file=sys.stderr)
                            logger.info(f"Removed existing stream sources for match {match.id} due to no live sources found.")

            # Remove stream sources for matches with no live sources found for 90 minutes
            live_matches_to_remove_sources = db.session.query(Matches).filter(
                Matches.isLive == True,
                Matches.last_crawl_time < ninety_minutes_ago
            ).all()
            print("Live matches to remove sources", live_matches_to_remove_sources, file=sys.stderr)
            for match in live_matches_to_remove_sources:
                stream_links = get_live_links(driver, match.link)
                if stream_links:
                    stream_sources = get_stream_sources(driver, stream_links)
                    print(f"Match {match.id} stream sources: {stream_sources}", file=sys.stderr)
                    if not stream_sources:
                        stream_sources_to_delete = db.session.query(StreamSources).filter_by(match_id=match.id).all()
                        print(f"Stream sources to delete for match {match.id}: {stream_sources_to_delete}", file=sys.stderr)
                        if stream_sources_to_delete:
                            for source in stream_sources_to_delete:
                                db.session.delete(source)
                                print(f"Deleted stream source: {source.link} for match {match.id}", file=sys.stderr)
                            logger.info(f"Removed stream sources for match {match.id} due to no live sources found for 90 minutes.")
                        else:
                            print(f"No stream sources found for match {match.id} to delete", file=sys.stderr)

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error occurred during the main function: {str(e)}")
        finally:
            if driver:
                driver.quit()  # Ensure the browser is properly closed after the job
            db.session.close()  # Ensure session is properly removed after the job

def main_loop(appArg: Flask, dbArg: SQLAlchemy):
    global db, app
    app = appArg
    db = dbArg
    print(f"Running stream source crawler at {datetime.now(mongolia_tz)}", file=sys.stderr)
    scheduler.add_job(main, 'interval', minutes=10, args=[db, app])
    scheduler.start()
