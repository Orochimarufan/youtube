#!/usr/bin/python3
#-------------------------------------------------------------------------------
#- YouFeed DataBase
#- Copyright (C) 2013  Orochimarufan
#-                 Authors: Orochimarufan <orochimarufan.x3@gmail.com>
#-
#- This program is free software: you can redistribute it and/or modify
#- it under the terms of the GNU General Public License as published by
#- the Free Software Foundation, either version 3 of the License, or
#- (at your option) any later version.
#-
#- This program is distributed in the hope that it will be useful,
#- but WITHOUT ANY WARRANTY; without even the implied warranty of
#- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#- GNU General Public License for more details.
#-
#- You should have received a copy of the GNU General Public License
#- along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

import os
import logging
from functools import wraps

import sqlalchemy.dialects.sqlite
from sqlalchemy import (create_engine, Table, Column, ForeignKey,
    String, Integer, DateTime, Text, Enum)
from sqlalchemy.schema import PrimaryKeyConstraint, Index
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()
logger = logging.getLogger("yfdb")

# yfdb schema version
DB_VERSION = 1


# Tables
class Video(Base):
    """ Stores information about a YouTube video """
    __tablename__ = 'videos'
    
    id      = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'))
    local   = relationship('LocalVideo', backref='video')
    
    title       = Column(String, index=True)
    description = Column(Text)
    categories  = Column(String, index=True)
    keywords    = Column(String, index=True)
    thumbnails  = Column(String)
    uploaded    = Column(String)
    duration    = Column(Integer)
    status      = Column(Integer, nullable=False, default='0')
    
    ST_PRIVATE  = 0x1
    ST_NOFORMAT = 0x2
    
    def __repr__(self):
        return "<YouTube Video: id='%s' title='%s'>" % (self.id, self.title)


class LocalVideo(Base):
    """ Stores information about a local video file """
    __tablename__ = 'local'
    
    id       = Column(Integer, primary_key=True)
    video_id = Column(String, ForeignKey('videos.id'))
    
    fmt      = Column(Integer)
    location = Column(String(4096), index=True)
    created  = Column(String)
    status   = Column(Integer, default=0)
    
    ST_V2IMPORT = 0x200
    
    def __repr__(self):
        return "<Local Video: video_id='%s' location='%s'>" % (self.video_id, self.location)


class PlaylistItem(Base):
    """ Association between a Playlist and it's Videos """
    __tablename__ = 'playlist_videos'
    
    playlist_id = Column(String, ForeignKey('playlists.id'), nullable=False)
    index       = Column(Integer, nullable=False)
    video_id    = Column(String, ForeignKey('videos.id'))
    
    __table_args__ = (PrimaryKeyConstraint('playlist_id', 'index'),)
    
    def __repr__(self):
        return "<Playlist Item: playlist_id='%s' index='%s' video_id='%s'>" % \
            (self.playlist_id, self.index, self.video_id)


class Playlist(Base):
    """ Stores a single Playlist """
    __tablename__ = 'playlists'
    
    id      = Column(String, primary_key=True)
    title   = Column(String, index=True)
    items   = relationship('PlaylistItem')
    
    user_id = Column(String, ForeignKey('users.id'))
    user_name = Column(String)
    url     = Column(String)
    summary = Column(Text)
    status  = Column(Integer, nullable=False, default='0')
    
    ST_NOSYNC = 0x2
    
    def __repr__(self):
        return "<YouTube Playlist: id='%s' name='%s'>" % (self.id, self.name)


class User(Base):
    """ Stores information about a youtube user """
    __tablename__ = 'users'
    
    id      = Column(String, primary_key=True)
    username= Column(String, index=True)
    name    = Column(String)
    status  = Column(Integer, nullable=False, default='0')
    
    ST_SUSPENDED = 0x1
    
    playlists = relationship('Playlist', backref='author')
    videos  = relationship('Video', backref='author')
    
    def __repr__(self):
        return "<YouTube User: name='%s' channel='%s' status='%s'>" % (self.name, self.channel, self.status)


class Option(Base):
    """ Stores application settings """
    __tablename__ = 'options'
    
    key     = Column(String(32), primary_key=True)
    value   = Column(Text)
    
    def __repr__(self):
        return "<Option: '%s'='%s'>" % (self.key, self.value)


class Job(Base):
    """ Stores a YouFeed job """
    __tablename__ = 'jobs'
    
    name    = Column(String(32), primary_key=True)
    type    = Column(String(32))
    playlist_id = Column(String, ForeignKey(Playlist.id))
    target  = Column(String(32))
    profile = Column(String(32))
    quality = Column(Integer)
    export  = Column(String(4096))
    range   = Column(String(10))
    status  = Column(Integer, nullable=False, default='0')
    
    ST_DISABLED = 0x1
    ST_NODL     = 0x2
    ST_NOSYNC   = 0x4
    
    ST_RUNONCE  = 0x100
    ST_V2IMPORT = 0x200


# DB migration helper
def db_version_migrate(engine, ver=None):
    """
    Function to recover from DB_VERSION mismatches.
    
    tries to patch the db schemas to the yfdl version
    """
    if ver is None:
        ver = get_version(engine)
    
    # simple comparisons
    if ver == DB_VERSION:
        logger.error("DB is already the latest version.")
        return
    if ver > DB_VERSION:
        #logger.error("DB has an unknown version: %i. are you sure you are using the latest yfdb?" % ver)
        raise ValueError("Database Version Unknown: %i" % ver)
    
    # minimalistic fallthrough-case implementation
    class case:
        fall=False
        def __call__(self, v):
            if self.fall or v == ver:
                self.fall = True
                return True
            return False
    case = case()
    
    # Migration code. Template:
    #if case(_version_):
    #   engine.execute(_modify_schema_to_match_next_version_)
    
    set_version(engine, DB_VERSION)


# sqlite specific stuff
def is_sqlite(engine):
    return isinstance(engine.dialect, sqlalchemy.dialects.sqlite.dialect)

def get_version(engine):
    if is_sqlite(engine):
        return engine.execute("PRAGMA user_version").fetchone()[0]
    else:
        if "options" in engine.dialect.table_names():
            return int(engine.execute("SELECT value FROM options WHERE key='db_version'").fetchone()[0])
        else:
            return 0

def set_version(engine, version):
    if is_sqlite(engine):
        engine.execute("PRAGMA user_version = %i" % version)
    else:
        if engine.execute("SELECT value FROM options WHERE key = 'db_version'").\
                count() == 0:
            engine.execute("INSERT INTO options (key, value) VALUES ('db_version', ?)", str(version))
        else:
            engine.execute("UPDATE options SET value = ? WHERE key = 'db_version'", str(version))

# DB sql worker decorator
def sqlworker(f):
    """ Auto-session-management decorator """
    @wraps(f)
    def proxy(self, *a, **b):
        if "session" not in b:
            session = self.Session()
            res = f(self, *a, session=session, **b)
            session.commit()
            if res is not None:
                return session, res
        else:
            return f(self, *a, **b)
    return proxy


# DB Object
class DB(object):
    """
    Stores information about a YF instance
    """
    
    @classmethod
    def open(cls, filename, echo=False):
        """ Open a YFDB sqlite file """
        engine = create_engine('sqlite:///' + filename, echo=echo)
        db = cls(engine)
        db.sqlite_file = os.path.abspath(filename)
        return db
    
    def __init__(self, engine):
        """ Initialize a YouFeed Database """
        # version
        ver = get_version(engine)
        if ver == 0:
            logger.info("Creating Schema on %s" % engine)
            Base.metadata.create_all(engine)
            set_version(engine, DB_VERSION)
        elif ver != DB_VERSION:
            logger.warn("Database Version Mismatch: db=%i this=%i. trying to migrate." %
                    (ver, DB_VERSION))
            db_version_migrate(engine, ver)
        
        # setup instance
        logger.debug("New YFDB from %s" % engine)
        self.engine  = engine
        self.Session = sessionmaker(bind=engine)
    
    #------------------------------
    # Users
    @sqlworker
    def newUser(self, id, username=None, session=None):
        u = User(name=username, id=id)
        session.add(u)
        return u
    
    @sqlworker
    def getUserByName(self, username, session):
        return session.query(User).filter(User.name == username).first()
    
    @sqlworker
    def getUserById(self, user_id, session):
        return session.query(User).get(user_id)
    
    @sqlworker
    def addUserEx(self, id, username=None, session=None):
        u = self.getUserById(id, session=session)
        if not u:
            u = self.newUser(id, username, session=session)
        return u
    
    #------------------------------
    # Videos
    @sqlworker
    def newVideo(self, video_id, title, user, session):
        v = Video(id=video_id, title=title, user_id=user.id)
        session.add(v)
        return v
    
    @sqlworker
    def getVideo(self, video_id, session):
        return session.query(Video).get(video_id)
    
    @sqlworker
    def addVideoEx(self, video_id, title, username, session):
        v = self.getVideo(video_id)
        if not v:
            v = self.newVideo(video_id, title,
                self.addUserEx(username, session=session), session=session)
        return v
    
    #------------------------------
    # Playlists
    @sqlworker
    def newPlaylist(self, playlist_id, user_id=None, session=None):
        p = Playlist(id=playlist_id)
        session.add(p)
        return p
    
    @sqlworker
    def getPlaylist(self, playlist_id, session):
        return session.query(Playlist).get(playlist_id)
    
    @sqlworker
    def addPlaylistEx(self, playlist_id, user_id=None, session=None):
        p = self.getPlaylist(playlist_id, session=session)
        if not p:
            p = self.newPlaylist(playlist_id, user_id, session=session)
        return p
    
    @sqlworker
    def addPlaylistVideo(self, playlist_id, video_id, index=None, session=None):
        if index is None:
            item = session.query(PlaylistItem).filter(PlaylistItem.playlist_id
                == playlist_id).order_by(PlaylistItem.index.asc()).first()
            if item is None:
                index = 0
            else:
                index = item.index + 1
        else:
            if session.query(PlaylistItem).filter(PlaylistItem.playlist_id
                == playlist_id).filter(PlaylistItem.index == index).count() != 0:
                for record in session.query(PlaylistItem).filter(
                    PlaylistItem.playlist_id == playlist_id).filter(
                    PlaylistItem.index >= index).order_by(
                    PlaylistItem.index.desc()).all():
                    record.index += 1
        pi = PlaylistItem(playlist_id=playlist_id, index=index, video_id=video_id)
        session.add(pi)
        return pi
    
    #------------------------------
    # Local Videos
    @sqlworker
    def newLocalVideo(self, video_id, fmt, location, session):
        v = LocalVideo(fmt=fmt, location=location, video_id=video_id)
        session.add(v)
        return v
    
    @sqlworker
    def getLocalVideos(self, video_id, session):
        return session.query(LocalVideo).filter(LocalVideo.video_id == video_id).all()
    
    #------------------------------
    # Options
    @sqlworker
    def getOption(self, key, session):
        return session.query(Option).get(key)
    
    def getOptionValue(self, key):
        opt = self.getOption(key)
        if opt is not None:
            return opt[1].value
    
    @sqlworker
    def setOptionValue(self, key, value, session):
        opt = self.getOption(key, session=session)
        if opt is None:
            opt = Option(key=key, value=value)
            session.add(opt)
        else:
            opt.value = value

__all__=["DB", "Video", "Playlist", "PlaylistItem", "User", "LocalVideo", "Job", "Option"]

