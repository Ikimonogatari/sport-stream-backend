from flask import Flask, request, jsonify, make_response
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from os import environ
from functools import wraps
import logging
from models import Matches, Leagues, StreamSources  # Import the Match model from models.py
from database import db

app = Flask(__name__)
app.logger.setLevel(logging.INFO)
app.config['SQLALCHEMY_DATABASE_URI'] = environ.get('DB_URL')
app.config['JWT_SECRET_KEY'] = 'xkYRtIG8FiHStcS5iS2aqsBeSFZcaj43cPDcX1Yph60GrQUbXC8YJP6MfOXV1DIv'
db.init_app(app)
jwt = JWTManager(app)

logging.basicConfig(level=logging.DEBUG)

# Authorization decorator to protect endpoints
def authorization_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'Authorization' not in request.headers:
            return make_response(jsonify({'message': 'Authorization header is missing'}), 401)
        
        try:
            access_token = request.headers['Authorization'].split(' ')[1]
            get_jwt_identity(access_token)
        except Exception as e:
            return make_response(jsonify({'message': 'Invalid token'}), 401)
        
        return fn(*args, **kwargs)
    
    return wrapper

# Test route
@app.route('/test', methods=['GET'])
def test():
    return make_response(jsonify({'message': 'Test route'}), 200)

# CRUD operations for matches
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
        matches = Matches.query.all()
        return make_response(jsonify([match.json() for match in matches]), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'Error getting matches', 'error': str(e)}), 500)


@app.route('/stream_sources', methods=['GET'])
def get_streamsources():
    try:
        stream_sources = StreamSources.query.all()
        return make_response(jsonify([stream_source.json() for stream_source in stream_sources]), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'Error getting leagues', 'error': str(e)}), 500)

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


import crawler
import crawler2
app.logger.info("main")
with app.app_context():
    db.create_all()
    print('CRAWLERS WORKING NOW!')
    crawler.main(app, db)
    crawler2.main_loop(app, db)
    app.run(debug=True)
