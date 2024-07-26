from flask import Flask, request, jsonify, make_response
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from os import environ
from functools import wraps
import logging
from models import Matches, Leagues, StreamSources  # Import the Match model from models.py
from database import db
from datetime import datetime

app = Flask(__name__)
app.logger.setLevel(logging.INFO)
app.config['SQLALCHEMY_DATABASE_URI'] = environ.get('DB_URL')
db.init_app(app)

logging.basicConfig(level=logging.DEBUG)

# Authorization decorator to protect endpoints
# def authorization_required(fn):
#     @wraps(fn)
#     def wrapper(*args, **kwargs):
#         if 'Authorization' not in request.headers:
#             return make_response(jsonify({'message': 'Authorization header is missing'}), 401)
        
#         try:
#             auth_header = request.headers['Authorization']
#             token_parts = auth_header.split()
#             if len(token_parts) != 2 or token_parts[0].lower() != 'bearer':
#                 raise Exception("Invalid token")
                
#             bearer_token = token_parts[1]
#             hardcoded_token = 'eyJhbGciOiJIUzI1NiJ9.eyJSb2xlIjoiQWRtaW4iLCJJc3N1ZXIiOiJUdXZzaGluamFyZ2FsIiwiVXNlcm5hbWUiOiJJa2ltb25vIiwiZXhwIjoxNzE2MjEwMjA0LCJpYXQiOjE3MTYyMTAyMDR9.bPq8cTPObKakFg54JGia8-hpcBK0fwMQu8HLffELs1M'  # Replace with your hardcoded token
            
#             if bearer_token != hardcoded_token:
#                 raise Exception("Invalid token")
                
#         except Exception as e:
#             return make_response(jsonify({'message': 'Invalid token'}), 401)
        
#         return fn(*args, **kwargs)
    
#     return wrapper

# # CRUD operations for matches
@app.route('/matches', methods=['POST'])
# @authorization_required
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
# @authorization_required
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
        now = datetime.now()
        all_matches = Matches.query.all()
        return make_response(jsonify([match.json() for match in all_matches]), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'Error getting matches', 'error': str(e)}), 500)

@app.route('/stream_sources', methods=['GET'])
# @authorization_required
def get_streamsources():
    try:
        stream_sources = StreamSources.query.all()
        return make_response(jsonify([stream_source.json() for stream_source in stream_sources]), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'Error getting leagues', 'error': str(e)}), 500)

@app.route('/live-matches', methods=['GET'])
# @authorization_required
def get_live_matches():
    try:
        live_matches = Matches.query.filter_by(isLive=True).all()
        return make_response(jsonify([match.json() for match in live_matches]), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'Error getting live matches', 'error': str(e)}), 500)


@app.route('/leagues', methods=['GET'])
# @authorization_required
def get_leagues():
    try:
        leagues = Leagues.query.all()
        return make_response(jsonify([league.json() for league in leagues]), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'Error getting leagues', 'error': str(e)}), 500)

@app.route('/matches/<int:id>', methods=['GET'])
# @authorization_required
def get_match(id):
    try:
        match = Matches.query.get(id)
        if match:
            return make_response(jsonify({'match': match.json()}), 200)
        return make_response(jsonify({'message': 'Match not found'}), 404)
    except Exception as e:
        return make_response(jsonify({'message': 'Error getting match', 'error': str(e)}), 500)

    
@app.route('/matches/<int:id>', methods=['PUT'])
# @authorization_required
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
# @authorization_required
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


import crawler
import crawler2
import crawler3
app.logger.info("main")
with app.app_context():
    db.create_all()
    crawler.main(app, db)
    crawler2.main_loop(app, db)
    # crawler3.main_loop(app, db)
    
    app.run(debug=True)
