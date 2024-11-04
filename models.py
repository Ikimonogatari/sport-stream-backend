from database import db

class Leagues(db.Model):
    __tablename__ = 'leagues'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    url = db.Column(db.String, nullable=False)
    
    matches = db.relationship("Matches", back_populates="league")

    def __init__(self, name, url):
        self.name = name
        self.url = url

    def __repr__(self):
        return f"<Leagues(name='{self.name}', url='{self.url}')>"

    def json(self):
        return {'id': self.id, 'name': self.name, 'url': self.url}

class StreamSources(db.Model):
    __tablename__ = 'stream_sources'
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'))
    link = db.Column(db.String)
    source = db.Column(db.String)

    match = db.relationship("Matches", back_populates="stream_sources")
    
    def __init__(self, match_id, link, source):
        self.match_id = match_id
        self.link = link
        self.source = source

    def json(self):
        return {'id': self.id, 'match_id': self.match_id, 'link': self.link, 'source': self.source}

class Matches(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    team1name = db.Column(db.String, nullable=True)
    team2name = db.Column(db.String, nullable=True)
    link = db.Column(db.String, nullable=True)
    time = db.Column(db.String, nullable=True)
    date = db.Column(db.String, nullable=True)
    league_id = db.Column(db.Integer, db.ForeignKey('leagues.id'))
    datetime = db.Column(db.DateTime, nullable=True)
    isLive = db.Column(db.Boolean, nullable=False, default=False)
    description = db.Column(db.String, nullable=True) 
    last_crawl_time = db.Column(db.DateTime, nullable=True, default=None) 
    isCrawling = db.Column(db.Boolean, nullable=False, default=False)
    
    league = db.relationship("Leagues", back_populates="matches")
    stream_sources = db.relationship("StreamSources", back_populates="match", cascade="all, delete-orphan")

    def __init__(self, team1name, team2name, link, time, date, league_id, datetime, isLive=False, description=None, last_crawl_time=None, isCrawling=False):
        self.team1name = team1name
        self.team2name = team2name
        self.link = link
        # match's current time
        self.time = time 
        # match created time
        self.date = date
        self.league_id = league_id
        # match start time
        self.datetime = datetime
        self.isLive = isLive
        self.description = description
        self.last_crawl_time = last_crawl_time
        self.isCrawling = isCrawling


    def json(self):
        return {
            'id': self.id,
            'team1name': self.team1name,
            'team2name': self.team2name,
            'link': self.link,
            'time': self.time,
            'date': self.date,
            'league_id': self.league_id,
            'datetime': self.datetime,
            'isLive': self.isLive,
            'description': self.description,
            'last_crawl_time': self.last_crawl_time,
            'isCrawling': self.isCrawling,
            
        }

    def __repr__(self):
        return f"<Matches(id={self.id}, team1name='{self.team1name}', team2name='{self.team2name}', isLive={self.isLive}, description='{self.description}', last_crawl_time='{self.last_crawl_time}', datetime='{self.datetime}')>"

