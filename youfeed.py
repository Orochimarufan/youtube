#!/usr/bin/python3
#-------------------------------------------------------------------------------
#- Copyright (C) 2010-2013  Orochimarufan
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

from __future__ import unicode_literals, print_function, absolute_import

#------------------------------------------------------------
# Settings
#------------------------------------------------------------
# database:
#   file that stores persistent settings and video/playlist infos
database = "youfeed.db"
# bytecount
#   number of bytes to recv at a time
#   can be overriden in database config
bytecount = 64*4096
# xspf_relpath
#   whether relative paths in XSPF playlists are enabled by default
#   can be overridden in database config
xspf_relpath = True


#------------------------------------------------------------
# Defaults
#------------------------------------------------------------
# these will be loaded from the db after being initialized
videos_folder = "videos"
playlists_folder = "playlists"
# these are fallback values that are used when neither the
#   job nor the config specifies
default_profile = "mixed-avc"
default_quality = 1080


#------------------------------------------------------------
# Filenames
#   How to handle filenames
#------------------------------------------------------------
allow_spaces    = False
allow_invalid   = False
valid_filename  = "-_.{ascii_letters}{digits}"
invalid_replace = ""
space_replace   = "_"


#------------------------------------------------------------
# Version
#   the version number
#------------------------------------------------------------
version         = "3.0"
version_info    = (3,0,0)
need_libyo      = (0,9,13)
date            = (2013,1,20)


#------------------------------------------------------------
# Imports
#------------------------------------------------------------
# stdlib
import sys
import logging
import os
import json
import string
import platform
import re
import datetime
import decimal
import uuid

# libyo
import libyo
from libyo.youtube.resolve import resolve3
from libyo.youtube.url import getIdFromUrl
from libyo.extern import argparse
from libyo.youtube.resolve.profiles import descriptions as fmtdesc, file_extensions as fmtext, profiles
from libyo.youtube.exception import YouTubeResolveError
from libyo.interface.progress.simple import SimpleProgress2
from libyo.interface.progress.file import SimpleFileProgress
from libyo.urllib.download import download as downloadFile
from libyo.configparser import RawPcsxConfigParser, PcsxConfigParser
from libyo.util import choice

# etree, urllib
from libyo.compat import etree
from libyo.urllib import request, parse
from libyo.youtube.auth import urlopen

# yfdb
import yfdb


#------------------------------------------------------------
# Platform and Filename helper code
#------------------------------------------------------------
if platform.system()=="cli": #IronPython OS Detection
    WINSX = platform.win32_ver()[0]!=""
else:
    WINSX = platform.system()=="Windows"

valid_filename = valid_filename.format(**string.__dict__)
_tfn_spaces = (lambda s: s) if allow_spaces \
else (lambda s: s.replace(" ","_"))
_tfn_validc = (lambda c: c) if allow_invalid \
else (lambda c: c if c in valid_filename else invalid_replace)
tofilename = lambda s: "".join([_tfn_validc(c) for c in _tfn_spaces(s)])


#------------------------------------------------------------
# Main Code
#   see the docstrings for more info
#------------------------------------------------------------
def welcome():
    """ Prints the Welcome Message and checks versions """
    print("YouFeed {1} (libyo {0})".format(libyo.version,version))
    print("(c) 2011-2012 Orochimarufan")
    if need_libyo > libyo.version_info:
        raise SystemError("libyo > {0} required.".format(".".join(map(str,need_libyo))))
    if (2,6) > sys.version_info:
        raise SystemError("python > 2.6 required.")


def main(argv):
    """
    The main entrypoint.
    
    This only manages commandline arguments and db intialization
    It will dispatch control to [subcommand]_command(args)
    """
    # print welcome message and check versions
    welcome()
    
    #---------------------------------------------
    # database initialization
    #---------------------------------------------
    if not os.path.exists(database):
        db = yfdb.DB.open(database)
        db.setOptionValue("playlists_folder", playlists_folder)
        db.setOptionValue("videos_folder", videos_folder)
    else:
        db = yfdb.DB.open(database)
    
    #---------------------------------------------
    # parse the commandline arguments
    #---------------------------------------------
    choice_profile = choices=choice.cichoice(profiles.keys())
    choice_quality = choice.qchoice.new(1080,720,480,360,240)
    
    parser = argparse.ArgumentParser(prog=argv[0])
    
    subparsers = parser.add_subparsers(dest="command",
        help="Use '%(prog)s (command) -h' to get further help. By Default, the 'run' command is run.",
        title="command", default="run")
    
    # config subcommand
    config_parser = subparsers.add_parser("config", description="Modify application options")
    config_parser.add_argument("mode", choices=("get", "set", "list"),
        help="What you want to do; available options are %(choices)s")
    config_parser.add_argument("key", help="The Key to modify/show (set, get)", nargs="?")
    config_parser.add_argument("value", help="The Value to set (set)", nargs="?")
    
    # job management
    job_parser = subparsers.add_parser("job", description="Manage youfeed jobs")
    job_subparsers = job_parser.add_subparsers(dest="mode",
        help="Job modification modes")
    
    job_add = job_subparsers.add_parser("add", description="Add new job")
    job_add.add_argument("name", help="An unique Identifier for this job")
    job_add.add_argument("type", help="The job type. choices: %(choices)s", choices=("playlist",))
    job_add.add_argument("resource", help="The job resource. [playlist -> playlist ID]")
    job_add.add_argument("-target", help="The name of the resulting playlist")
    job_add.add_argument("-profile", help="The job codec profile", choices=choice_profile)
    job_add.add_argument("-quality", help="The job maximum quality", choices=choice_quality)
    job_add.add_argument("-export", help="Export the playlist file")
    job_add.add_argument("-disable", action="store_true", help="Disable the new job")
    
    job_rm = job_subparsers.add_parser("rm", description="Remove a job")
    job_rm.add_argument("name", help="The job identifier")
    
    job_dis = job_subparsers.add_parser("disable", description="Enable/Disable Job")
    job_dis.add_argument("name", help="The job identifier")
    job_dis.add_argument("disabled", help="disabled flag value. choices: %(choices)s", choices=("yes", "no"))
    
    job_mod = job_subparsers.add_parser("change", description="Modify a job")
    job_mod.add_argument("name", help="The job identifier")
    job_mod.add_argument("-name", dest="newname", help="Change the identifier")
    job_mod.add_argument("-type", help="Change the job type", choices=("playlist",))
    job_mod.add_argument("-resource", help="Change the job resource")
    job_mod.add_argument("-target", help="Change the playlist name")
    job_mod.add_argument("-profile", help="Change the codec profile", choices=choice_profile)
    job_mod.add_argument("-quality", help="Change the maximum quality", choices=choice_quality)
    job_mod.add_argument("-export", help="Change the export location")
    
    job_list = job_subparsers.add_parser("list", description="List jobs")
    
    job_show = job_subparsers.add_parser("show", description="Display a job")
    job_show.add_argument("name", help="The job identifier")
    
    # run subcommand
    run_parser = subparsers.add_parser("run",
        description="run job(s). if no jobs are given, run all enabled jobs")
    run_parser.add_argument("names", help="The job identifier(s)", nargs="*")
    run_parser.add_argument("-p", help="Only recreate the playlist file(s)", action="store_true")
    run_parser.add_argument("-d", help="Only check for new videos, don't download anything", action="store_true")
    run_parser.add_argument("-forceall", help="run disabled jobs, too", action="store_true")
    
    # do the parsing
    args = parser.parse_args(argv[1:])
    
    # pass db around with args
    args.db     = db
    args.root   = os.path.dirname(os.path.abspath(database))
    
    #---------------------------------------------
    # Dispatcher
    #---------------------------------------------
    if args.command == "config":
        return config_command(args)
    elif args.command == "job":
        return job_command(args)
    elif args.command == "run":
        return run_command(args)


def config_command(args):
    """ The config subcommand implementation """
    if args.mode == "get":
        if not args.key:
            raise argparse.ArgumentError("key", "Key required for mode 'get'")
        print(args.db.getOptionValue(args.key))
    elif args.mode == "set":
        if not args.key:
            raise argparse.ArgumentError("key", "Key required for mode 'set'")
        if not args.value:
            raise argparse.ArgumentError("value", "Value required for mode 'set'")
        if args.key in ("db_version",):
            raise argparse.ArgumentError("key", "Key '%s' cannot be modified" % args.key)
        args.db.setOptionValue(args.key, args.value)
        print("'%s' is now '%s'" % (args.key, args.db.getOptionValue(args.key)))
    elif args.mode == "list":
        for opt in args.db.Session().query(yfdb.Option).all():
            print("'%s'='%s'" % (opt.key, opt.value))


def job_command(args):
    """ the job command allows users to create and modify jobs """
    session = args.db.Session()
    
    if args.mode == "add":
        job = yfdb.Job(name=args.name, type=args.type)
        pl = get_playlist_id(args.type, args.resource)
        args.db.addPlaylistEx(pl, session=session)
        job.playlist_id = pl
        job.status = 0
        if args.disable:
            job.status = job.ST_DISABLED
        session.add(job)
        print("Job '%s' was created%s" % (job.name, " (disabled)" if args.disable else ""))
    
    elif args.mode == "list":
        for job in session.query(yfdb.Job).all():
            print("Job '%s': %s('%s')%s" % (
                job.name, job.type, job.playlist_id,
                " (disabled)" if job.status & job.ST_DISABLED else ""))
    
    else:
        # all other operation modify an existing Job
        job = session.query(yfdb.Job).get(args.name)
        if job is None:
            raise argparse.ArgumentError("name", "Job '%s' does not exist." % args.name)
        
        if args.mode == "rm":
            # remove it
            session.delete(job)
            print("Job '%s' was deleted." % args.name)
        
        elif args.mode == "disable":
            # disable it (or not)
            if args.disabled == "yes":
                job.status |= job.ST_DISABLED
                print("Job '%s' was disabled" % job.name)
            else:
                job.status &= ~job.ST_DISABLED
                print("Job '%s' was enabled" % job.name)
        
        elif args.mode == "show":
            # print it
            print("Job: %s" % job.name)
            print("%s('%s')" % (job.type, job.playlist_id))
            if job.target is not None:
                print("Target: %s" % job.target)
            if job.profile is not None:
                print("Profile: %s" % job.profile)
            if job.quality is not None:
                print("Quality: %i" % job.quality)
            if job.export is not None:
                print("Export to: '%s'" % job.export)
            
            flags = list()
            if job.status & job.ST_DISABLED:
                flags.append("disabled")
            print("Flags: {0:b}{1:s}".format(job.status, "(" + ", ".join(flags) + ")" if flags else ""))
        
        elif args.mode == "change":
            if args.newname:
                job.name = args.newname
            if args.type:
                job.type = args.type
            if args.resource:
                pl = get_playlist_id(job.type, args.resource)
                args.db.addPlaylistEx(pl, session=session)
                job.playlist_id = pl
            print("Job '%s' was modified. % job.name")
    
    #common modify/add operations
    if args.mode in ("add", "change"):
        if args.target:
            job.target = args.target
        if args.profile:
            job.profile = args.profile
        if args.quality:
            job.quality = 360#TODO get quality integer
        if args.export:
            job.export = args.export
    
    session.commit()


def run_command(args):
    """
    the run subcommand
    
    collects jobs and calls run_job for each of them
    """
    session = args.db.Session()
    
    if not os.path.exists(args.db.getOptionValue("videos_folder")):
        os.makedirs(args.db.getOptionValue("videos_folder"))
    if not os.path.exists(args.db.getOptionValue("playlists_folder")):
        os.makedirs(args.db.getOptionValue("playlists_folder"))
    
    if args.names:
        joblist = list()
        for name in args.names:
            joblist.append(session.query(yfdb.Job).get(name))
    
    else:
        if not args.forceall:
            joblist = session.query(yfdb.Job).filter(
                yfdb.Job.status.op("&")(yfdb.Job.ST_DISABLED) == 0
                ).all()
        else:
            joblist = session.query(yfdb.Job).all()
    
    for job in joblist:
        run_job(args, session, job)
    
    session.commit()
    return 0


def run_job(args, session, job):
    """
    Gets the remote playlist and run_video()s each video
    The run_playlist()s the Playlist
    """
    type, res = job.type, get_resource(job.type, job.playlist_id)
    
    print("[ RUN ] Job: %s" % job.name)
    
    if type == "playlist":
        # get the remote playlist
        doc = gdata("playlists/" + res, {"max-results":"50"}).getroot()
        
    # playlist metadata
    author = doc.find(tag("atom", "author"))
    title  = doc.find(tag("atom", "title")).text
    
    playlist        = args.db.getPlaylist(job.playlist_id, session=session)
    playlist.title  = title
    playlist.user_name = author.find(tag("atom", "name")).text
    if author.find(tag("yt", "userId")) is not None:
        playlist.author = args.db.addUserEx(author.find(tag("yt", "userId")).text,
                                            author.find(tag("atom", "name")).text,
                                            session=session)
    #playlist.url    = doc.find("%s[rel='alternate']" % tag("atom", "link")).text
    
    print("[ RUN ] Playlist: '%s' by %s" % (playlist.title, playlist.user_name))
    
    # fetch the videos
    while True:
        for entry in doc.iterfind(tag("atom", "entry")):
            data     = entry.find(tag("media", "group"))
            
            video_id = data.find(tag("yt", "videoid")).text
            video    = args.db.getVideo(video_id)
            
            if video is None:
                # get the metadata
                title       = data.find(tag("media", "title")).text
                description = data.find(tag("media", "description")).text
                keywords    = data.find(tag("media", "keywords")).text
                categories  = ",".join([i.attrib["label"]
                        for i in data.iterfind(tag("media", "category"))])
                thumbnails  = json.dumps([
                        (i.attrib["width"], i.attrib["height"],
                         i.attrib.get("time", "0"), i.attrib["url"])
                        for i in data.iterfind(tag("media", "thumbnail"))])
                author_id   = data.find(tag("yt", "uploaderId")).text[2:]
                uploaded    = isodate_parse_datetime(data.find(tag("yt", "uploaded")).text)
                duration    = int(data.find(tag("yt", "duration")).attrib["seconds"])
                
                # create the video
                video = yfdb.Video(id=video_id, title=title, description=description,
                                   keywords=keywords, categories=categories,
                                   thumbnails=thumbnails, uploaded=uploaded,
                                   status=0, duration=duration)
                session.add(video)
                
                # do the user
                user = session.query(yfdb.User).get(author_id)
                if user is None:
                    userdoc = gdata("users/%s" % author_id)
                    username = userdoc.find(tag("atom", "title")).text
                    user = yfdb.User(id=author_id, name=username)
                    session.add(user)
                video.author = user
            
            try:
                session.query(yfdb.PlaylistItem).\
                    filter(yfdb.PlaylistItem.playlist_id == job.playlist_id).\
                    filter(yfdb.PlaylistItem.video_id == video_id).one()
            except yfdb.NoResultFound:
                ix = entry.find(tag("yt", "position"))
                index = int(ix.text) if ix is not None else None
                args.db.addPlaylistVideo(job.playlist_id, video.id, index, session=session)
        
        next = doc.find("%s[@rel='next']" % tag("atom", "link"))
        if next is not None:
            doc = gdata_link(next.attrib["href"]).getroot()
        else:
            break
    
    session.commit()
    
    # do the job (haha)
    vids = run_playlist(args, session, job, playlist)
    run_mkplaylist(args, session, job, playlist, vids)
    return 0


def run_playlist(args, session, job, playlist):
    """ process videos in a playlist """
    items = session.query(yfdb.PlaylistItem).\
            filter(yfdb.PlaylistItem.playlist_id == playlist.id).\
            order_by(yfdb.PlaylistItem.index.asc()).all()
    
    if job.range:
        start, stop = job.range.split(":", 1)
        
        class negInf:
            def __lt__(self, other):
                return True
            def __gt__(self, other):
                return False
        class posInf:
            def __gt__(self, other):
                return True
            def __lt__(self, other):
                return False
        
        start = int(start) if start else negInf()
        stop  = int(stop) if stop else posInf()
        
        items = (item for item in items if start <= item.index < stop)
    
    lookup_table = make_job_qa(args, job)
    
    localVids = list()
    
    for item in items:
        video = session.query(yfdb.Video).get(item.video_id)
        
        localVids.append(run_video(args, session, job, video, lookup_table))
    
    return localVids


def run_video(args, session, job, video, lookup_table):
    """
    Check if we have a local video that works for the job
    and download one if we don't
    """
    # check if we have something fitting
    localvids = session.query(yfdb.LocalVideo).\
            filter(yfdb.LocalVideo.video_id == video.id).\
            filter(yfdb.LocalVideo.fmt.in_(lookup_table)).all()
    
    if localvids:
        localvids.sort(key=lambda v: lookup_table.index(v.fmt))
        return localvids[0]
    
    # -p only checks videos that we already have
    if args.p: return
    
    # get it from youtube
    print("[VIDEO] New video: '%s' by %s" % (video.title, video.author.name))
    
    # -d doesn't download new videos
    if args.d: return
    
    # check if we can access the video
    fp = gdata("videos/%s" % video.id, raw=True)
    
    with fp:
        if fp.read(512) == "Private Video":
            print("[VIDEO] Video '%s' is Private!" % video.title)
            video.status |= video.ST_PRIVATE
            return
    
    # get the url
    try:
        url, fmt = recursive_resolve(video.id, lookup_table)
    except YouTubeResolveError:
        print("[VIDEO] Could not resolve video.")
        return
    if url is fmt is None:
        print("[VIDEO] Video does not have a format that is allowed by your profile/quality settings")
        video.status |= video.ST_NOFORMAT
        return
    
    print("[VIDEO] Downloading Video as %s." % fmtdesc[fmt])
    
    # download it
    return run_download(args, session, video, url, fmt)


def run_download(args, session, video, url, fmt):
    """ actually download a video """
    folder      = args.db.getOptionValue("videos_folder")
    basename    = tofilename("-".join((video.id, uuid.uuid4().hex)))
    filename    = ".".join((basename, fmtext[fmt]))
    path        = os.path.join(folder, filename)
    fullpath    = make_absolute(path, args.root)
    
    progress    = SimpleFileProgress("{position}/{total} {bar} {percent} {speed} ETA: {eta}")
    retry       = 0
    while retry < 5:
        try:
            downloadFile(url, fullpath, progress, 2, bytecount)
        except Exception:
            import traceback
            print("[ERROR] " + "".join(traceback.format_exception_only(*sys.exc_info()[:2])))
            retry += 1
        else:
            break
    else:
        print("[ERROR] Cannot Download. Continuing")
        return
    
    # Save DB
    localvideo = yfdb.LocalVideo(video_id=video.id, fmt=fmt, location=path,
                                 created=datetime.datetime.utcnow())
    session.add(localvideo)
    session.commit()
    
    return localvideo


def run_mkplaylist(args, session, job, playlist_, vids):
    """ creates the local playlist """
    # sort out missing videos
    vids = [vid for vid in vids if vid is not None]
    
    print("[ RUN ] Creating Playlists...")
    
    if job.target:
        target = job.target
    else:
        target = playlist_.title
    
    rel = args.db.getOptionValue("xspf_relpath")
    if rel is None:
        rel = xspf_relpath
    else:
        rel = rel in ("true", "yes", "True")
    
    # get the playlist localtion
    folder      = args.db.getOptionValue("playlists_folder")
    filename    = tofilename(target) + ".xspf"
    path        = make_absolute(os.path.join(folder, filename), args.root)
    
    # create it in memory
    playlist = etree.Element("playlist", {"xmlns": "http://xspf.org/ns/0/", "version": "1"})
    #playlist.attrib[tag("xml", "base")] = "file://" + args.root
    playlist.append(etree.Comment("Created by YouFeed v3"))
    
    def TextElement(parent, tag, text):
        elem = etree.SubElement(parent, tag)
        elem.text = text
        return elem
    
    TextElement(playlist, "title", text=playlist_.title)
    TextElement(playlist, "creator", text=playlist_.user_name)
    #TextElement(playlist, "info", text=playlist_.url)
    
    trackList = etree.SubElement(playlist, "trackList")
    
    for video in vids:
        track = etree.SubElement(trackList, "track")
        
        TextElement(track, "location", "file://" + video.location)
        TextElement(track, "location", "file://" + make_absolute(video.location, args.root))
        TextElement(track, "title", video.video.title)
        TextElement(track, "creator", video.video.author.name)
        TextElement(track, "annotation", video.video.description)
        TextElement(track, "duration", str(video.video.duration))
        TextElement(track, "info", "http://youtube.com/watch?v=%s" % video.id)
        TextElement(track, "image", json.loads(video.video.thumbnails)[0][3])
    
    tree = etree.ElementTree(playlist)
    
    # write it down
    with open(path, "wb") as fp:
        tree.write(fp, xml_declaration=True, encoding="utf8")
    
    if job.export:
        with open(make_absolute(job.export, args.root)) as fp:
            tree.write(fp, xml_declaration=True, encoding="utf8")


#------------------------------------------------------------
# Youtube Resolving stuff
#------------------------------------------------------------
def make_job_qa(args, job):
    """ generate a quality lookup table """
    
    # get the job profile
    if job.profile is not None:
        profile_name = job.profile
    else:
        profile_name = args.db.getOptionValue("default_profile")
        if profile_name is None:
            profile_name = default_profile
    
    profile = profiles[profile_name]
    
    # get the job quality
    if job.quality is not None:
        quality = job.quality
    else:
        quality = args.db.getOptionValue("default_quality")
        if quality is None:
            quality = default_quality
        else:
            quality = int(choice.qchoice.unify(quality))
    
    # generate the lookup table
    if quality not in profile:
       print("[ WARN] The Exact Quality (%i) is not avaiable in this Profile: \"%s\"" % (quality, profile_name))
    return [v for k, v in profile[0].items() if k <= quality]


def recursive_resolve(video_id, lookup_table):
    umap = resolve3(video_id).urlmap
    for i in lookup_table:
        if i in umap:
            return umap[i], i
    else:
        return None,None


#------------------------------------------------------------
# Helpers
#------------------------------------------------------------
# YouTube GData v2 helpers
xmlns = {
    "atom": "http://www.w3.org/2005/Atom",
    "openSearch": "http://a9.com/-/spec/opensearch/1.1/",
    "yt": "http://gdata.youtube.com/schemas/2007",
    "media": "http://search.yahoo.com/mrss/",
    "xspf": "http://xspf.org/ns/0/",
    "xml":  "http://www.w3.org/XML/1998/namespace",
    }

def gdata(module, params=dict(), ssl=True, raw=False):
    url = parse.urlunparse(("https" if ssl else "http",
                            "gdata.youtube.com",
                            "feeds/api/" + module,
                            "",
                            parse.urlencode(params),
                            ""))
    
    return gdata_link(url, raw)

def gdata_link(url, raw=False):
    req = request.Request(url)
    req.add_header("GData-Version", "2")
    
    if not raw:
        with urlopen(req) as fp:
            return etree.parse(fp)
    else:
        return urlopen(req)

def tag(xmlns_, tagname):
    return "".join(('{', xmlns[xmlns_], '}', tagname))


# playlist_id helpers
def get_playlist_id(type, resource):
    """ helper that returns the playlist_id to use in the DB """
    if type == "playlist":
        return resource
    elif type == "favorites":
        return "yf_favorites:%s" % resource

def get_resource(type, playlist_id):
    """ helper to get the resource from the playlist id """
    if type == "playlist":
        return playlist_id
    elif type == "favorites":
        return playlist_id[:13]


# some path stuff
def make_absolute(path, root=None):
    if not os.path.isabs(path):
        if root is None:
            root = os.getcwd()
        path = os.path.join(root, path)
    return os.path.normpath(path)

#------------------------------------------------------------
# ISO8601 DateTime parser
#------------------------------------------------------------
isodate_date = (r"(?:"
                r"(?:(?P<sign>[+-])(?P<year5>[0-9]{5,}[0-9]+)|(?P<year>[0-9]{4}))"
                r"(?:(?P<datesep>-?)(?:"
                 # y-m-d
                 r"(?P<month>[0-9]{2})"
                 r"(?:(?P=datesep)(?P<day>[0-9]{2}))?"
                r"|"
                 # y-w-d
                 r"W(?P<week>[0-9]{2})"
                 r"(?:(?P=datesep)(?P<weekday>[0-7]))?"
                r"|"
                 # y-d
                 r"(?P<ordinal>[0-9]{3})"
                r"))?|"
                # century
                r"(?:(?P<centsign>[+-])(?P<cent3>[0-9]{3,4})|(?P<century>[0-9]{2}))"
               r")")
isodate_time = (r"(?P<hour>[0-9]{2})"
                r"(?:(?P<timesep>:?)(?P<minute>[0-9]{2})"
                r"(?:(?P=timesep)(?P<second>[0-9]{2})))"
                r"(?:[,.](?P<fraction>[0-9]+))?")
isodate_tz   = r"(?P<tz>(?:Z|(?P<tzsign>[+-])(?P<tzhour>[0-9]{2})(?::?(?P<tzmin>[0-9]{2}))?)?)"
isodate_tre  = re.compile(isodate_time + isodate_tz)
isodate_dre  = re.compile(isodate_date)
isodate_re   = re.compile(isodate_date + "T" + isodate_time + isodate_tz)
isodate_zero = datetime.timedelta(0)

class isodate_tzinfo(datetime.tzinfo):
    def __init__(self, offset_hours=0, offset_mins=0, name='UTC'):
        self.__offset = datetime.timedelta(hours=offset_hours, minutes=offset_mins)
        self.__name = name
    def utcoffset(self, dt):
        return self.__offset
    def tzname(self, dt):
        return self.__name
    def dst(self, dt):
        return isodate_zero
    def __repr__(self):
        return '<ISO8601 TZInfo %r>' % self.__name

isodate_utc = isodate_tzinfo()

def isodate_parse_datetime(s):
    """ parses a ISO8601 DateTime """
    match = isodate_re.match(s)
    if not match:
        raise ValueError("not a valid ISO8601 DateTime: '%s'" % s)
    groups = match.groupdict()
    
    return datetime.datetime.combine(isodate_pd(groups), isodate_pt(groups))

def isodate_parse_date(s):
    """ parses a ISO8601 Date """
    match = isodate_dre.match(s)
    if not match:
        raise ValueError("not a valid ISO8601 Date: '%s'" % s)
    
    return isodate_pd(match.groupdict())

def isodate_parse_time(s):
    """ parses a ISO8601 Time """
    match = isodate_tre.match(s)
    if not match:
        raise ValueError("not a valid ISO8601 Time: '%s'" % s)
    
    return isodate_pt(match.groupdict())

def isodate_pd(groups):
    """ Extracts the date from regexp results """
    # century date
    has = lambda k: k in groups and groups[k] is not None
    if has('cent3'):
        sign = -1 if groups['centsign'] == "-" else 1
        date = datetime.date(sign * (int(groups['century']) * 100 + 1), 1, 1)
    elif has('century'):
        date = datetime.date(int(groups['century']) * 100, 1, 1)
    
    else:
        # year
        if has('year5'):
            year = int(groups['year5']) * -1 if groups['sign'] == "-" else 1
        else:
            year = int(groups['year'])
        
        # y-m-*
        if has('month'):
            if has('day'):
                date = datetime.date(year, int(groups['month']), int(groups['day']))
            else:
                date = datetime.date(year, int(groups['month']), 1)
        
        else:
            date = datetime.date(year, 1, 1)
            
            # y-w-d
            if has('week'):
                iso = date.isocalendar()
                
                date += datetime.timedelta(
                    weeks=int(groups['week']) - (1 if iso[1] == 1 else 0),
                    days=-iso[2] + (int(groups['weekday']) if has('weekday') else 1))
            
            # y-d
            elif has('ordinal'):
                date += datetime.timedelta(days=int(groups['ordinal'])-1)
    
    return date

def isodate_pt(groups):
    """ Extracts the time from regexp results """
    has = lambda k: k in groups and groups[k] is not None
    get = lambda k, d: groups[k] if has(k) else d
    
    # TZInfo
    if not groups['tz']:
        tz = None
    elif groups['tz'] == 'Z':
        tz = isodate_utc
    else:
        sign = -1 if groups['tzsign'] == '-' else 1
        tz = isodate_tzinfo(sign * int(get('tzhour', 0)),
                            sign * int(get('tzmin', 0)),
                            groups['tz'])
    
    # Time
    if has('fraction'):
        fraction = decimal.Decimal('0.' + groups['fraction'])
    else:
        fraction = 0
    
    if has('second'):
        time = datetime.time(int(groups['hour']), int(groups['minute']), int(groups['second']),
            (fraction.quantize(decimal.Decimal('.000001')) * int(1e6)).to_integral(), tz)
    elif has('minute'):
        second = fraction * 60
        time = datetime.time(int(groups['hour']), int(groups['minute']), int(second),
            ((second - int(second)).quantize(decimal.Decimal('0.000001')) * int(1e6)).to_integral(), tz)
    else:
        minute = fraction * 60
        second = (minute - int(minute)) * 60
        time = datetime.time(int(groups['hour']), int(minute), int(second),
            ((second - int(second)).quantize(decimal.Decimal('0.000001')) * int(1e6)).to_integral(), tz)
    
    return time


#------------------------------------------------------------
# Python entrypoint
#------------------------------------------------------------
if __name__=="__main__":
    sys.exit(main(sys.argv))

