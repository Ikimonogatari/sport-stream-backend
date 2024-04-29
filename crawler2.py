from flask_sqlalchemy import SQLAlchemy
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from models import StreamSources, Matches
from datetime import datetime, timedelta
import time
import chromedriver_autoinstaller
from webdriver_manager.chrome import ChromeDriverManager
import sys
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
print("Selenium version:", webdriver.__version__)
scheduler = BackgroundScheduler()

# chrome_driver_path = "/root/.wdm/drivers/chromedriver/linux64/114.0.5735.90/chromedriver"  # Update this with the correct path to your chromedriver
# print(chrome_driver_path, file=sys.stderr)

db: SQLAlchemy = None
app: Flask = None

# Install and update chromedriver to match the installed Chrome version
# chromedriver_autoinstaller.install()

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
    
    print(start_time, end_time, file=sys.stderr)

    return db.session.query(Matches).filter(
        Matches.datetime >= start_time,
        Matches.datetime <= end_time
    ).all()

def main():
    with app.app_context():
        chrome_driver_path = chromedriver_autoinstaller.install()
        # chrome_driver_path = ChromeDriverManager().install()
        print(chrome_driver_path)
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
                        stream_source = StreamSources(match_id=match.id, link=link)
                        db.session.add(stream_source)

        db.session.commit()
        db.session.close()

def main_loop(appArg: Flask, dbArg: SQLAlchemy):
    global db, app
    app = appArg
    db = dbArg
    print("main loop")
    print(f"Running stream source crawler at {datetime.now()}", file=sys.stderr)
    print("RUNNING LOOP CRAWLER")
    # scheduler.add_job(main, 'interval', seconds=10)
    # scheduler.start()
    main()
