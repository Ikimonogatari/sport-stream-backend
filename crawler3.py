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

# Ensure the logger is configured
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

db: SQLAlchemy = None
app: Flask = None


def get_live_links(driver, match_url):
    links = []
    driver.get(match_url)
    try:
        WebDriverWait(driver,10).until(EC.presence_of_element_located((By.ID, 'streams')))
        streamTable = driver.find_element(By.CSS_SELECTOR, '.table.streams-table-new')
        tableBody = streamTable.find_element(By.TAG_NAME, 'tbody')
        tr_list = tableBody.find_elements(By.TAG_NAME, 'tr')

        for tr in tr_list:
            links.append(tr.get_attribute('data-stream-link'))

    except Exception as e:
        print("An error occurred:", e, file=sys.stderr)
    return links

def find_matches_about_to_start(db, time_buffer=100):
    now = datetime.now()
    start_time = now + timedelta(minutes=time_buffer)
    end_time = start_time + timedelta(minutes=100)

    # Print the datetime of the first match, assuming it exists

    return db.session.query(Matches).filter(
        Matches.datetime >= start_time,
        Matches.datetime <= end_time
    ).all()

def remove_expired_stream_sources(db):
    with app.app_context():
        try:
            # Calculate the expiration time for matches (e.g., matches older than 6 hours)
            expiration_time = datetime.utcnow() - timedelta(hours=6)

            # Query the database for matches that have exceeded the expiration time
            expired_matches = db.session.query(Matches).filter(Matches.datetime < expiration_time).all()

            if expired_matches:
                # Iterate over the expired matches
                for match in expired_matches:
                    # Query and delete the stream sources associated with the expired match
                    db.session.query(StreamSources).filter(StreamSources.match_id == match.id).delete()

                # Commit the changes to the database
                db.session.commit()
                logger.info(f"Removed stream sources associated with {len(expired_matches)} expired matches.")
            else:
                logger.info("No expired matches found.")

        except Exception as e:
            # Rollback in case of any error
            db.session.rollback()
            logger.error(f"Error occurred while removing expired stream sources: {str(e)}")

def main(db: SQLAlchemy, app: Flask):
    now = datetime.now()

    with app.app_context():
        chrome_driver_path = chromedriver_autoinstaller.install()
        chrome_options = Options()
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--proxy-bypass-list=*")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-browser-side-navigation")
        upcoming_matches = find_matches_about_to_start(db)

        service = Service(executable_path=chrome_driver_path)

        with webdriver.Chrome(service=service, options=chrome_options) as driver:

            for match in upcoming_matches:

                stream_links = get_live_links(driver, match.link)  # Ensure match has a 'url' attribute
                for link in stream_links:
                    # Check if the stream source already exists
                    existing_source = db.session.query(StreamSources).filter_by(match_id=match.id, link=link).first()
                    if not existing_source:
                        # If no existing source, create a new one
                        stream_source = StreamSources(match_id=match.id, link=link, datetime=datetime.now())
                        db.session.add(stream_source)
                       
        db.session.commit()
        db.session.close()

def main_loop(appArg: Flask, dbArg: SQLAlchemy):
    
    global db, app
    app = appArg
    db = dbArg
    print(f"Running stream source crawler at {datetime.now()}", file=sys.stderr)
    scheduler.add_job(main, 'interval', seconds=300, args=[db, app])
    scheduler.add_job(remove_expired_stream_sources, 'interval', hours=6, args=[db]) 
    scheduler.start()
 
