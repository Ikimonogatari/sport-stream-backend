from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import Leagues, Matches, StreamSources
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
from apscheduler.executors.pool import ThreadPoolExecutor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

executors = {
    'default': ThreadPoolExecutor(3)
}
mongolia_tz = pytz.timezone('Asia/Ulaanbaatar')
scheduler = BackgroundScheduler(timezone=mongolia_tz, executors=executors)

db: SQLAlchemy = None
app: Flask = None

def insert_default_leagues():
    default_leagues = [
        {"name": "Basketball", "url": "https://basketball28.sportshub.stream/"},
        {"name": "Soccer", "url": "https://reddit15.sportshub.stream"},
        {"name": "Volleyball", "url": "https://volleyball3.sportshub.stream/"},
        {"name": "American Football", "url": "https://football2.sportshub.stream/"},
        {"name": "Tennis", "url": "https://tennis7.sportshub.stream/"},
        {"name": "Boxing", "url": "https://volleyball3.sportshub.stream/"},
        {"name": "Fight", "url": "https://mma3.sportshub.stream/"},
        {"name": "Motorsport", "url": "https://motorsport4.sportshub.stream/"},
        {"name": "Horse Racing", "url": "https://www.sportshub.stream/horse-racing-streams/"},
        {"name": "Rugby", "url": "https://rugby2.sportshub.stream/"},
        {"name": "Cycling", "url": "https://cycling2.sportshub.stream/"},
        {"name": "Golf", "url": "https://golf2.sportshub.stream/"},
        {"name": "Snooker", "url": "https://snooker2.sportshub.stream/"},
        {"name": "Water Sports", "url": "https://www.sportshub.stream/water-sports-streams/"},
        {"name": "Summer Sports", "url": "https://www.sportshub.stream/summer-sports-streams/"},
        {"name": "Beach Soccer", "url": "https://www.sportshub.stream/beach-soccer-streams/"},
        {"name": "Handball", "url": "https://handball3.sportshub.stream/"},
        {"name": "Athletics", "url": "https://www.sportshub.stream/athletics-streams/"},
        {"name": "Beach Volleyball", "url": "https://www.sportshub.stream/beach-volley-streams/"},
        {"name": "Badminton", "url": "https://badminton2.sportshub.stream/"},
        {"name": "Tabletennis", "url": "https://www.sportshub.stream/table-tennis-streams/"},
        {"name": "Rowing", "url": "https://www.sportshub.stream/rowing-streams/"},
        {"name": "Futsal", "url": "https://www.sportshub.stream/futsal-streams/"},
        {"name": "Winter Sports", "url": "https://www.sportshub.stream/winter-sports-streams/"},
        {"name": "Curling", "url": "https://www.sportshub.stream/curling-streams/"},
        {"name": "Hockey", "url": "https://hockey3.sportshub.stream/"},
        {"name": "NBA", "url": "https://nba37.sportshub.stream/"},
        # {"name": "NHL", "url": "https://nhl5.sportshub.stream/"},
        # {"name": "NFL", "url": "https://nfl2.sportshub.stream/"},
        # {"name": "MLB", "url": "https://mlb2.sportshub.stream/"},
        # {"name": "MLS", "url": "https://mls2.sportshub.stream/"},
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

def schedule_next_live_update(db: SQLAlchemy, app: Flask):
    print("Scheduling update match to live")
    with app.app_context():
        current_time_mongolia = datetime.now(mongolia_tz)
        current_time_mongolia = current_time_mongolia.replace(microsecond=0).replace(tzinfo=None)
        upcoming_match = Matches.query.filter(Matches.isLive == False).order_by(Matches.datetime).first()
        
        print(upcoming_match, "UPCOMING MATCH")
        if upcoming_match:
            next_match_time = upcoming_match.datetime
            print(next_match_time, "NEXT MATCH TIME")
            print(current_time_mongolia, "CURRENT MGL TIME")
            # Schedule a one-time job for when the match should go live
            scheduler.add_job(update_live_status, run_date=next_match_time, args=[db, app])
            logger.info(f"set sched 6969 {upcoming_match.id} at {next_match_time}")
            print("Jobs:", scheduler.get_jobs())
        else:
            logger.info("No upcoming matches to schedule.")

def update_live_status(db: SQLAlchemy, app: Flask):
    print("Updating live status")

    with app.app_context():
        # Set current time and update live matches
        current_time_mongolia = datetime.now(mongolia_tz)
        current_time_mongolia = current_time_mongolia.replace(microsecond=0).replace(tzinfo=None)
        matches_to_update = Matches.query.filter(Matches.datetime <= current_time_mongolia, Matches.isLive == False).all()
        
        for match in matches_to_update:
            match.isLive = True
            match.last_crawl_time = datetime.now()
        
        db.session.commit()

        # Schedule the next live update based on the next match
        schedule_next_live_update(db, app)        

def scheduleCrawler(driver, league):
    logger.info(f"Starting crawler for {league.name}")

    driver.get(league.url)
    wait = WebDriverWait(driver, 10)

    try:
        contentDiv = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'list-events')))
        logger.info("Content div found")

        fixturesLis = contentDiv.find_elements(By.CLASS_NAME, 'wrap-events-item')
        logger.info(f"Found {len(fixturesLis)} fixtures")

        for li in fixturesLis:
            team1Name = li.find_element(By.CLASS_NAME, 'mr-5').text
            matchURL = li.find_element(By.TAG_NAME, "a").get_attribute("href")
            matchDesc = li.find_element(By.CLASS_NAME, 'event-desc').text
            
            description, matchDateConverted = extract_desc_and_date(matchDesc)

            isLive = bool(li.find_elements(By.CLASS_NAME, 'live-label'))

            existing_match = Matches.query.filter_by(
                team1name=team1Name,
                link=matchURL,
                datetime=matchDateConverted,
                league_id=league.id,
                description=description
            ).first()

            if not existing_match:
                new_match = Matches(
                    team1name=team1Name,
                    team2name="",
                    link=matchURL,
                    time="",
                    date="",
                    datetime=matchDateConverted,
                    league_id=league.id,
                    isLive=isLive,
                    description=description,
                    last_crawl_time=None,
                )
                db.session.add(new_match)
                logger.info("Added new match")

        db.session.commit()

    except Exception as e:
        logger.error(f"An error occurred during web scraping for {league.name}: {str(e)}")
        db.session.rollback()
    finally:
        driver.quit()

def extract_desc_and_date(desc_str):
    # Split the description and date
    description_part, date_time_text = desc_str.split("/", 1)
    description_part = description_part.strip()
    date_time_text = date_time_text.strip()

    date_part, time_part = date_time_text.split(" at ")
    date_part = date_part.strip()
    time_part = time_part.strip()

    # Define the current year and build the full date string
    current_year = datetime.now().year
    full_date_str = f"{time_part} {date_part} {current_year}"
    date_format = "%H:%M %d %B %Y"

    # Parse the date string to a naive datetime object
    naive_datetime = datetime.strptime(full_date_str, date_format)

    # Define the timezone for England (London) and Mongolia
    england_tz = pytz.timezone('Europe/London')
    mongolia_tz = pytz.timezone('Asia/Ulaanbaatar')

    # Localize the naive datetime to England timezone and then convert to Mongolia timezone
    aware_datetime_england = england_tz.localize(naive_datetime)
    aware_datetime_mongolia = aware_datetime_england.astimezone(mongolia_tz)

    # Convert to PostgreSQL compatible string format
    psql_compatible_string = aware_datetime_mongolia.strftime('%Y-%m-%dT%H:%M:%S%z')

    return description_part, psql_compatible_string

def main(db: SQLAlchemy, app: Flask):

    with app.app_context():
        insert_default_leagues()

        try:
            leagues = Leagues.query.all()

            for league in leagues:
                driver = setup_driver()
                scheduleCrawler(driver, league)
                update_live_status(db, app)
                logger.info(f"{league.name} matches added")
        except Exception as e:
            logger.error(f"Failed to connect to database or run crawler: {str(e)}")
        finally:
            db.session.close()

def main_loop(appArg: Flask, dbArg: SQLAlchemy):
    global db, app
    app = appArg
    db = dbArg
    # main(db, app)
    update_live_status(db, app)
    scheduler.add_job(main, 'interval', hours=8, args=[db, app])
    scheduler.start()
