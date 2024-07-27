from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import Leagues, Matches
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pytz
from datetime import datetime, timedelta
import sys
import chromedriver_autoinstaller
from apscheduler.schedulers.background import BackgroundScheduler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

db: SQLAlchemy = None
app: Flask = None

def insert_default_leagues():
    default_leagues = [
        {"name": "Basketball", "url": "https://basketball28.sportshub.stream/"},
        {"name": "Soccer", "url": "https://reddit15.sportshub.stream"},
        {"name": "Volleyball", "url": "https://volleyball3.sportshub.stream/"},
    ]

    for league_info in default_leagues:
        existing_league = Leagues.query.filter_by(name=league_info['name']).first()
        if not existing_league:
            new_league = Leagues(name=league_info['name'], url=league_info['url'])
            db.session.add(new_league)
    db.session.commit()

def setup_driver():
    chrome_driver_path = chromedriver_autoinstaller.install()
    chrome_options = Options()
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--proxy-bypass-list=*")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-browser-side-navigation")

    service = Service(executable_path=chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def scheduleCrawler(driver, league):
    logger.info(f"Starting crawler for {league.name}")

    driver.get(league.url)
    wait = WebDriverWait(driver, 10)

    try:
        contentDiv = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'list-events')))
        logger.info("Content div found")

        day = contentDiv.find_element(By.TAG_NAME, 'h4').text

        fixturesLis = contentDiv.find_elements(By.CLASS_NAME, 'wrap-events-item')
        logger.info(f"Found {len(fixturesLis)} fixtures")

        for li in fixturesLis:
            team1Name = li.find_element(By.CLASS_NAME, 'mr-5').text
            matchURL = li.find_element(By.TAG_NAME, "a").get_attribute("href")
            matchDate = li.find_element(By.CLASS_NAME, 'event-desc').text
            matchDateConverted = convert_buff_to_utc_psql_format(matchDate)

            isLive = bool(li.find_elements(By.CLASS_NAME, 'live-label'))

            existing_match = Matches.query.filter_by(
                team1name=team1Name,
                link=matchURL,
                date=day,
                datetime=matchDateConverted,
                league_id=league.id
            ).first()

            if not existing_match:
                new_match = Matches(
                    team1name=team1Name,
                    team2name="",
                    time="",
                    link=matchURL,
                    date=day,
                    datetime=matchDateConverted,
                    league_id=league.id,
                    isLive=isLive
                )
                db.session.add(new_match)
                logger.info("Added new match")
            elif isLive and not existing_match.isLive:
                existing_match.isLive = True
                logger.info("Updated match to live")

        db.session.commit()
    except Exception as e:
        logger.error(f"An error occurred during web scraping for {league.name}: {str(e)}")
        db.session.rollback()
    finally:
        driver.quit()

def convert_buff_to_utc_psql_format(date_str):
    _, date_time_text = date_str.split("/", 1)
    date_time_text = date_time_text.strip()
    date_part, time_part = date_time_text.split(" at ")
    date_part = date_part.strip()
    time_part = time_part.strip()

    current_year = datetime.now().year
    full_date_str = f"{time_part} {date_part} {current_year}"
    date_format = "%H:%M %d %B %Y"
    naive_datetime = datetime.strptime(full_date_str, date_format)

    est = pytz.timezone('US/Eastern')
    aware_datetime = est.localize(naive_datetime)
    utc_datetime = aware_datetime.astimezone(pytz.utc)
    psql_compatible_string = utc_datetime.strftime('%Y-%m-%dT%H:%M:%S%z')

    return psql_compatible_string

def convert_to_utc_psql_format(date_str):
    date_format = "%H:%M %a %d %b %Y"
    naive_datetime = datetime.strptime(date_str, date_format)
    est = pytz.timezone('US/Eastern')
    aware_datetime = est.localize(naive_datetime)
    utc_datetime = aware_datetime.astimezone(pytz.utc)
    psql_compatible_string = utc_datetime.strftime('%Y-%m-%dT%H:%M:%S%z')

    return psql_compatible_string

def remove_expired_matches():
    with app.app_context():
        try:
            expiration_time = datetime.utcnow() - timedelta(hours=6)
            expired_matches = db.session.query(Matches).filter(Matches.datetime < expiration_time).all()

            if expired_matches:
                for match in expired_matches:
                    db.session.query(Matches).filter(Matches.match_id == match.id).delete()

                db.session.commit()
                logger.info(f"Removed stream sources associated with {len(expired_matches)} expired matches.")
            else:
                logger.info("No expired matches found.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error occurred while removing expired stream sources: {str(e)}")

def main(appArg: Flask, dbArg: SQLAlchemy):
    global db, app
    app = appArg
    db = dbArg

    with app.app_context():
        insert_default_leagues()

        try:
            leagues = Leagues.query.all()

            for league in leagues:
                driver = setup_driver()
                scheduleCrawler(driver, league)
                logger.info(f"{league.name} matches added")
        except Exception as e:
            logger.error(f"Failed to connect to database or run crawler: {str(e)}")
        finally:
            db.session.close()

if __name__ == '__main__':
    scheduler.add_job(main, 'interval', minutes=5, args=[db, app])
    scheduler.add_job(remove_expired_matches, 'interval', hours=1)
    scheduler.start()
