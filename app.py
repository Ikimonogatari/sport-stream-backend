from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from os import environ
import logging
from models import Matches, Leagues, StreamSources
from database import db
from datetime import datetime
from streamSourceCrawler import get_live_links, get_stream_sources
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
SCRAPER_API_KEY = '6be10ab64669a2f166584ccf985109c6'
scraper_api_url = "http://api.scraperapi.com"   

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = environ.get('DB_URL')
db.init_app(app)

CORS(app, supports_credentials=True)

@app.route('/matches', methods=['POST'])
def create_match():
    try:
        data = request.get_json()
        required_fields = ['team1name', 'team2name', 'link', 'time', 'date', 'league_id', 'datetime']
        if not all(field in data for field in required_fields):
            return make_response(jsonify({'message': 'Missing required fields'}), 400)
        
        new_match = Matches(**data)
        db.session.add(new_match)
        db.session.commit()
        return make_response(jsonify({'message': 'Match created'}), 201)
    except Exception as e:
        return make_response(jsonify({'message': 'Error creating match', 'error': str(e)}), 500)


@app.route('/matches', methods=['GET'])
def get_matches():
    try:
        now = datetime.now()
        future_matches = Matches.query.filter(Matches.datetime > now).all()
        return make_response(jsonify([match.json() for match in future_matches]), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'Error getting matches', 'error': str(e)}), 500)

@app.route('/all-matches', methods=['GET'])
def get_allmatches():
    try:
        all_matches = Matches.query.all()
        return make_response(jsonify([match.json() for match in all_matches]), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'Error getting matches', 'error': str(e)}), 500)

@app.route('/stream_sources', methods=['GET'])
def get_streamsources():
    try:
        stream_sources = StreamSources.query.all()
        return make_response(jsonify([stream_source.json() for stream_source in stream_sources]), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'Error getting stream sources', 'error': str(e)}), 500)

@app.route('/live-matches', methods=['GET'])
def get_live_matches():
    try:
        live_matches = Matches.query.filter_by(isLive=True).all()
        return make_response(jsonify([match.json() for match in live_matches]), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'Error getting live matches', 'error': str(e)}), 500)

@app.route('/leagues', methods=['GET'])
def get_leagues():
    try:
        leagues = Leagues.query.all()
        return make_response(jsonify([league.json() for league in leagues]), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'Error getting leagues', 'error': str(e)}), 500)

@app.route('/matches/<int:id>', methods=['GET'])
def get_match(id):
    try:
        match = Matches.query.get(id)
        if match:
            return make_response(jsonify({'match': match.json()}), 200)
        return make_response(jsonify({'message': 'Match not found'}), 404)
    except Exception as e:
        return make_response(jsonify({'message': 'Error getting match', 'error': str(e)}), 500)

@app.route('/matches/<int:id>', methods=['PUT'])
def update_match(id):
    try:
        match = Matches.query.get(id)
        if match:
            data = request.get_json()
            for key, value in data.items():
                setattr(match, key, value)
            db.session.commit()
            return make_response(jsonify({'message': 'Match updated'}), 200)
        return make_response(jsonify({'message': 'Match not found'}), 404)
    except Exception as e:
        return make_response(jsonify({'message': 'Error updating match', 'error': str(e)}), 500)

@app.route('/matches/<int:id>', methods=['DELETE'])
def delete_match(id):
    try:
        match = Matches.query.get(id)
        if match:
            db.session.delete(match)
            db.session.commit()
            return make_response(jsonify({'message': 'Match deleted'}), 200)
        return make_response(jsonify({'message': 'Match not found'}), 404)
    except Exception as e:
        return make_response(jsonify({'message': 'Error deleting match', 'error': str(e)}), 500)

@app.route('/matches/by-league', methods=['GET'])
def get_matches_by_league():
    try:
        app.logger.info("Received request for matches by league")
        
        league_name = request.args.get('league_name')
        app.logger.info(f"League name received: {league_name}")

        if not league_name:
            app.logger.warning("League name is missing")
            return make_response(jsonify({'message': 'League name is required'}), 400)

        league = Leagues.query.filter_by(name=league_name).first()
        if not league:
            app.logger.warning(f"League not found: {league_name}")
            return make_response(jsonify({'message': 'League not found'}), 404)

        # Get the current time and subtract 3 hours
        three_hours_ago = datetime.now() - timedelta(hours=3)

        # Query for matches in this league with datetime no older than 3 hours ago
        matches = Matches.query.filter(
            Matches.league_id == league.id,
            Matches.datetime >= three_hours_ago
        ).all()
        
        return make_response(jsonify([match.json() for match in matches]), 200)
    except Exception as e:
        app.logger.error(f"Error getting matches: {str(e)}")
        return make_response(jsonify({'message': 'Error getting matches', 'error': str(e)}), 500)


@app.route('/matches/<int:match_id>/stream_sources', methods=['GET'])
def get_stream_sources_for_match(match_id):
<<<<<<< HEAD
    chrome_options = Options()
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--proxy-bypass-list=*")
    chrome_options.add_argument("--disable-browser-side-navigation")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--remote-debugging-port=9222")
    
    target_url = 'https://sportshub.stream'
    proxy = f"{scraper_api_url}?api_key={SCRAPER_API_KEY}&url={target_url}"
    chrome_options.add_argument(f'--proxy-server={proxy}')

    driver = webdriver.Chrome(options=chrome_options)

=======
>>>>>>> staging
    try:
        match = Matches.query.get(match_id)
        if not match:
            return make_response(jsonify({'message': 'Match not found'}), 404)

        if not match.isLive:
            return make_response(jsonify({'message': 'Match is not live'}), 200)
        
        last_crawl_time = match.last_crawl_time or datetime.min

        # If the match is already being crawled or was recently crawled, return existing sources
        if  match.isCrawling or (datetime.now() - last_crawl_time).total_seconds() < 300:
            
            app.logger.info("Returning existing stream sources due to recent crawl")
            existing_sources = StreamSources.query.filter_by(match_id=match_id).all()
            return make_response(jsonify([source.json() for source in existing_sources]), 200)
        

        # Set isCrawling to True to indicate a new crawl is in progress
        match.isCrawling = True
        db.session.commit()
        # Start the crawler to get live links
        chrome_options = Options()
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--proxy-bypass-list=*")
        chrome_options.add_argument("--disable-browser-side-navigation")
        target_url = 'https://sportshub.stream'
        proxy = f"{scraper_api_url}?api_key={SCRAPER_API_KEY}&url={target_url}"
        chrome_options.add_argument(f'--proxy-server={proxy}')
        driver = webdriver.Chrome(options=chrome_options)
        stream_links = get_live_links(driver, match.link)
        new_sources = []

        if stream_links:
            for link in stream_links:
                # Check if the link already exists in the database
                existing_source = StreamSources.query.filter_by(match_id=match_id, link=link).first()
                if not existing_source:
                    app.logger.info("ADDED NEW SOURCE")
                    # Crawl and add new sources only if the link is new
                    new_source_links = get_stream_sources(driver, [link])
                    for source in new_source_links:
                        new_source = StreamSources(match_id=match_id, link=link, source=source)
                        db.session.add(new_source)
                        new_sources.append(new_source)

            # Update last crawl time and reset isCrawling status
            match.last_crawl_time = datetime.now()
            db.session.commit()

        match.isCrawling = False
        db.session.commit()
        # Get all sources (both new and existing) and return them
        all_sources = StreamSources.query.filter_by(match_id=match_id).all()
        return make_response(jsonify([source.json() for source in all_sources]), 200)

    except Exception as e:
        app.logger.error(f"Error getting stream sources for match: {str(e)}")
        return make_response(jsonify({'message': 'Error getting stream sources', 'error': str(e)}), 500)

import matchCrawler
import streamSourceCrawler
app.logger.info("main")
with app.app_context():
    db.create_all()
    matchCrawler.main_loop(app, db)
    streamSourceCrawler.main_loop(app, db)
    
    app.run(debug=False)
