#!/usr/bin/python3
#-------------------------------------------------------------------------------
#- YouFeed
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
bytecount = 64 * 4096


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
version_info    = (3, 0, 0)
need_libyo      = (0, 10, 0)
date            = (2013, 1, 23)


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
import datetime
import uuid
import shutil

# libyo
import libyo
try:
    from libyo.youtube.resolve import resolve3
    from libyo.extern import argparse
    from libyo.youtube.resolve.profiles import descriptions as fmtdesc, file_extensions as fmtext, profiles
    from libyo.youtube.exception import YouTubeResolveError
    from libyo.interface.progress.file import SimpleFileProgress
    from libyo.urllib.download import download as downloadFile
    from libyo.util import choice

# etree, urllib
    from libyo.compat import etree
    from libyo.urllib import request, parse
    from libyo.youtube.auth import urlopen
except ImportError:
    if libyo.version_info < need_libyo:
        raise ImportError("Insufficent libyo version: %s found, %s required")
    raise

# yfdb
import yfdb


#------------------------------------------------------------
# Platform and Filename helper code
#------------------------------------------------------------
if platform.system() == "cli": #IronPython OS Detection
    WINSX = platform.win32_ver()[0] != ""
else:
    WINSX = platform.system() == "Windows"

valid_filename = valid_filename.format(**string.__dict__)
_tfn_spaces = (lambda s: s) if allow_spaces \
else (lambda s: s.replace(" ", "_"))
_tfn_validc = (lambda c: c) if allow_invalid \
else (lambda c: c if c in valid_filename else invalid_replace)
tofilename = lambda s: "".join([_tfn_validc(c) for c in _tfn_spaces(s)])

# put together a video filename
gen_videofn = lambda v, f: "-".join((tofilename(v.id), uuid.uuid4().hex, str(f)))


#------------------------------------------------------------
# Main Code
#   see the docstrings for more info
#------------------------------------------------------------
def welcome():
    """ Prints the Welcome Message and checks versions """
    print("YouFeed %s" % version)
    print("(c) 2011-2013 Orochimarufan")
    if need_libyo > libyo.version_info:
        raise SystemError("libyo > {0} required.".format(".".join(map(str, need_libyo))))
    if (2, 6) > sys.version_info:
        raise SystemError("python > 2.6 required.")
    
    logging.basicConfig(format="[%(levelname)5s] %(name)s: %(message)s", level=logging.INFO)


def main(argv):
    """
    The main entrypoint.
    
    This only manages commandline arguments and db intialization
    It will dispatch control to [subcommand]_command(args)
    """
    # print welcome message and check versions
    welcome()
    
    #---------------------------------------------
    # parse the commandline arguments
    #---------------------------------------------
    choice_profile = choice.cichoice(profiles.keys())
    choice_quality = choice.qchoice.new(1080, 720, 480, 360, 240)
    
    parser = argparse.ArgumentParser(prog=argv[0])
    parser.add_argument("-db", dest="database", help="The Database to use", default=database)
    parser.add_argument("-V", dest="command_", action="store_const", const="version",
        help="Display version and quit")
    
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
    job_add.add_argument("type", help="The job type. choices: %(choices)s", choices=("playlist", "favorites"))
    job_add.add_argument("resource", help="The job resource. [playlist -> playlist ID]")
    job_add.add_argument("-target", help="The name of the resulting playlist")
    job_add.add_argument("-profile", help="The job codec profile", choices=choice_profile)
    job_add.add_argument("-quality", help="The job maximum quality", choices=choice_quality)
    job_add.add_argument("-export", help="Export the playlist file")
    job_add.add_argument("-disable", action="store_true", help="Disable the new job")
    job_add.add_argument("-noidcheck", action="store_true", help="Disable Playlist ID check")
    
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
    job_mod.add_argument("-noidcheck", action="store_true", help="Disable Playlist ID check")
    
    job_list = job_subparsers.add_parser("list", description="List jobs")
    job_list.add_argument("-showall", help="Don't hide system jobs", action="store_true")
    
    job_show = job_subparsers.add_parser("show", description="Display a job")
    job_show.add_argument("name", help="The job identifier")
    
    # run subcommand
    run_parser = subparsers.add_parser("run",
        description="run job(s). if no jobs are given, run all enabled jobs")
    run_parser.add_argument("names", help="The job identifier(s)", nargs="*")
    run_parser.add_argument("-p", help="Only recreate the playlist file(s)", action="store_true")
    run_parser.add_argument("-d", help="Only check for new videos, don't download anything", action="store_true")
    run_parser.add_argument("-forceall", help="run disabled jobs, too", action="store_true")
    
    # db subcommand
    db_parser = subparsers.add_parser("db", description="Manage the YouFeed Database")
    
    db_parsers = db_parser.add_subparsers(dest="mode")
    
    db_import2 = db_parsers.add_parser("v2import", description="Import v2 videos")
    db_import2.add_argument("pldir", help="youfeed v2 pl/ directory")
    db_import2.add_argument("-move", help="move contained videos to new schema", action="store_true")
    #db_import2.add_argument
    
    # do the parsing
    args = parser.parse_args(argv[1:])
    
    #---------------------------------------------
    # database initialization
    #---------------------------------------------
    if not os.path.exists(args.database):
        db = yfdb.DB.open(args.database)
        db.setOptionValue("playlists_folder", playlists_folder)
        db.setOptionValue("videos_folder", videos_folder)
    else:
        db = yfdb.DB.open(args.database)
        
    # pass db around with args
    args.db     = db
    args.root   = os.path.dirname(os.path.abspath(args.database))
    
    #---------------------------------------------
    # Dispatcher
    #---------------------------------------------
    if args.command_:
        if args.command_ == "version":
            print("YouFeed version: %s" % version)
            print("libyo version:   %s" % libyo.version)
            print("DB version:      %i" % yfdb.DB_VERSION)
            return 0
    elif args.command == "config":
        return config_command(args)
    elif args.command == "job":
        return job_command(args)
    elif args.command == "run":
        return run_command(args)
    elif args.command == "db":
        return db_command(args)


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
            # db_version might be used in non-sqlite environments
            raise argparse.ArgumentError("key", "Key '%s' is reserved" % args.key)
        args.db.setOptionValue(args.key, args.value)
        print("'%s' is now '%s'" % (args.key, args.db.getOptionValue(args.key)))
    elif args.mode == "list":
        for opt in args.db.Session().query(yfdb.Option).\
                filter(~yfdb.Option.key.in_('db_version',)).all():
            print("'%s'='%s'" % (opt.key, opt.value))


def db_command(args):
    """ the db subcommand """
    if args.mode == "v2import":
        v2import_command(args)


def job_command(args):
    """ the job command allows users to create and modify jobs """
    session = args.db.Session()
    
    # fav job
    def make_fav_pi():
        user = session.query(yfdb.User).filter(yfdb.User.username == args.resource.lower()).first()
        
        if not user:
            userdoc = gdata("users/%s" % args.resource)
            userid = userdoc.find(tag("yt", "userId")).text
            user = session.query(yfdb.User).get(userid)
            if not user:
                username = userdoc.find(tag("yt", "username"))
                username1 = username.text
                username2 = username.attrib['display']
                user = yfdb.User(id=userid, username=username1, name=username2)
                session.add(user)
        
        return "FL%s" % user.id
    
    def make_job_tr():
        if args.type == "favorites":
            return "playlist", make_fav_pi()
        else:
            if not args.noidcheck and args.resource[:2] not in ("PL", "FL"):
                print("[ERROR] playlist id not prefixed with either [PL] or [FL], please double-check your playlist ID and make sure you used the whole id (&list=<id>&) Normal playlists have the [PL] prefix. will stop now. use -noidcheck to ignore")
                return None, None
            return args.type, args.resource
    
    # add unique stuff
    if args.mode == "add":
        tp, pl = make_job_tr()
        job = yfdb.Job(name=args.name, type=tp, playlist_id=pl)
        
        if args.disable:
            job.status = job.ST_DISABLED
        
        session.add(job)
        print("Job '%s' was created%s" % (job.name, " (disabled)" if args.disable else ""))
    
    # list
    elif args.mode == "list":
        q = session.query(yfdb.Job)
        if not args.showall:
            q = q.filter(~yfdb.Job.name.startswith("v2import_"))
        
        jobs = q.all()
        if jobs:
            for job in jobs:
                print("Job '%s'%s" % (job.name,
                    #job.type, job.playlist_id,
                    " (disabled)" if job.status & job.ST_DISABLED else ""))
        else:
            print("No jobs.")
    
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
            
            # stringify the flags
            flags = list()
            if job.status & job.ST_DISABLED:
                flags.append("disabled")
            if job.status & job.ST_NODL:
                flags.append("nodl")
            if job.status & job.ST_NOSYNC:
                flags.append("nosync")
            if job.status & job.ST_RUNONCE:
                flags.append("once")
            if job.status & job.ST_V2IMPORT:
                flags.append("v2")
            
            print("Flags: {0:b}{1:s}".format(job.status, " (" + ", ".join(flags) + ")" if flags else ""))
        
        # change unique stuff
        elif args.mode == "change":
            if args.newname:
                job.name = args.newname
            if args.type:
                if not args.resource:
                    raise argparse.ArgumentError("resource", "resource required if type is changed")
                job.type, job.playlist_id = make_job_tr()
            elif args.resource:
                job.playlist_id = args.resource
            print("Job '%s' was modified. % job.name")
    
    #common modify/add operations
    if args.mode in ("add", "change"):
        if args.target:
            job.target = args.target
        if args.profile:
            job.profile = args.profile
        if args.quality:
            job.quality = choice.qchoice.unify(args.quality)
        if args.export:
            job.export = args.export
    
    session.commit()


def run_command(args):
    """
    the run subcommand
    
    collects jobs and calls run_job for each of them
    """
    session = args.db.Session()
    
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
    process a job
    """
    print("[ RUN ] Job: %s" % job.name)
    
    if job.status & yfdb.Job.ST_NOSYNC == 0:
        playlist = run_sync(args, session, job)
    else:
        playlist = session.query(yfdb.Playlist).get(job.playlist_id)
        if not playlist:
            print("[ERROR]: playlist not initialized, but sync turned off")
            return 1
    
    # do the job (haha)
    vids = run_playlist(args, session, job, playlist)
    run_mkplaylist(args, session, job, playlist, vids)
    
    # runonce
    if job.status & yfdb.Job.ST_RUNONCE != 0:
        job.status |= yfdb.Job.ST_DISABLED
    
    return 0


def run_sync(args, session, job):
    """
    Gets the remote playlist
    """
    if job.type == "playlist":
        # get the remote playlist
        doc = gdata("playlists/" + job.playlist_id, {"max-results": "50"}).getroot()
        
    # playlist metadata
    author = doc.find(tag("atom", "author"))
    title  = doc.find(tag("atom", "title")).text
    
    playlist        = session.query(yfdb.Playlist).get(job.playlist_id)
    if playlist is None:
        playlist    = yfdb.Playlist(id=job.playlist_id)
        session.add(playlist)
    
    playlist.title  = title
    playlist.user_name = author.find(tag("atom", "name")).text
    if author.find(tag("yt", "userId")) is not None:
        playlist.author = get_make_user(author.find(tag("yt", "userId")).text, session)
    #playlist.url    = doc.find("%s[rel='alternate']" % tag("atom", "link")).text
    
    print("[ RUN ] Playlist: '%s' by %s" % (playlist.title, playlist.user_name))
    
    # fetch the videos
    while True:
        for entry in doc.iterfind(tag("atom", "entry")):
            data     = entry.find(tag("media", "group"))
            
            video_id = data.find(tag("yt", "videoid")).text
            video    = session.query(yfdb.Video).get(video_id)
            
            if video is None:
                # create the video
                video = yfdb.Video(id=video_id)
                session.add(video)
                
                # link the user
                user_id = data.find(tag("yt", "uploaderId")).text[2:]
                author = get_make_user(user_id, session)
                if author.status & yfdb.User.ST_SUSPENDED != 0:
                    author_ = data.find("%s[@role='uploader']" % tag("media", "credit"))
                    author.name = author_.attrib[tag("yt", "display")]
                    author.username = author_.text
                video.author = author
            
            #print(str(etree.tostring(data, pretty_print=True),"utf8"))
            
            # update the metadata
            video.title       = data.find(tag("media", "title")).text
            try:
                video.description = data.find(tag("media", "description")).text
            except AttributeError: pass
            try:
                video.keywords    = data.find(tag("media", "keywords")).text
            except AttributeError: pass
            try:
                video.categories  = ",".join([i.attrib["label"]
                    for i in data.iterfind(tag("media", "category"))])
            except (AttributeError, KeyError): pass
            try:
                video.thumbnails  = json.dumps([
                    (i.attrib["width"], i.attrib["height"],
                     i.attrib.get("time", "0"), i.attrib["url"])
                    for i in data.iterfind(tag("media", "thumbnail"))])
            except AttributeError: pass
            try:
                video.uploaded    = data.find(tag("yt", "uploaded")).text
            except AttributeError: pass
            try:
                video.duration    = int(data.find(tag("yt", "duration")).attrib["seconds"])
            except AttributeError: pass
            
            # create the playlist item
            try:
                session.query(yfdb.PlaylistItem).\
                    filter(yfdb.PlaylistItem.playlist_id == job.playlist_id).\
                    filter(yfdb.PlaylistItem.video_id == video_id).one()
            except yfdb.NoResultFound:
                ix = entry.find(tag("yt", "position"))
                index = int(ix.text) if ix is not None else None
                args.db.addPlaylistVideo(job.playlist_id, video.id, index, session=session)
        
        # get next set of videos ( if any )
        nextpage = doc.find("%s[@rel='next']" % tag("atom", "link"))
        if nextpage is not None:
            doc = gdata_link(nextpage.attrib["href"]).getroot()
        else:
            break
    
    # commit database
    session.commit()
    
    return playlist


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
    
    # ST_NODL prevents downloads
    if job.status & yfdb.Job.ST_NODL != 0: return
    
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
    make_dirs_to(args, "videos_folder")
    
    folder      = args.db.getOptionValue("videos_folder")
    basename    = gen_videofn(video, fmt)
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
                                 created=datetime.datetime.utcnow().isoformat())
    session.add(localvideo)
    session.commit()
    
    return localvideo


def run_mkplaylist(args, session, job, playlist_, vids):
    """ creates the local playlist """
    make_dirs_to(args, "playlists_folder")
    
    # sort out missing videos
    vids = [vid for vid in vids if vid is not None]
    
    print("[ RUN ] Creating Playlists...")
    
    if job.target:
        target = job.target
    else:
        target = playlist_.title
    
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
        TextElement(track, "identifier", "http://youtube.com/watch?v=%s" % video.video_id)
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
    if quality not in profile[0]:
        print("[ WARN] The Exact Quality (%i) is not avaiable in this Profile: \"%s\"" % (quality, profile_name))
    return [v for k, v in profile[0].items() if k <= quality]


def recursive_resolve(video_id, lookup_table):
    umap = resolve3(video_id).urlmap
    for i in lookup_table:
        if i in umap:
            return umap[i], i
    else:
        return None, None


#------------------------------------------------------------
# Helpers
#------------------------------------------------------------
# YouTube GData v2 helpers
xmlns = {
    "atom": "http://www.w3.org/2005/Atom",
    "openSearch": "http://a9.com/-/spec/opensearch/1.1/",
    "yt": "http://gdata.youtube.com/schemas/2007",
    "gd": "http://schemas.google.com/g/2005",
    "media": "http://search.yahoo.com/mrss/",
    "xspf": "http://xspf.org/ns/0/",
    "xml": "http://www.w3.org/XML/1998/namespace",
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
        try:
            with urlopen(req) as fp:
                return etree.parse(fp)
        except request.HTTPError as e:
            tree = etree.parse(e.fp)
            el = etree.SubElement(tree.getroot(), "httpcode")
            el.text = str(e.getcode())
            e.fp.close()
            return tree
    else:
        return urlopen(req)


def tag(xmlns_, tagname):
    return "".join(('{', xmlns[xmlns_], '}', tagname))


def get_make_user(user_id, session):
    """ get or create an user """
    user = session.query(yfdb.User).get(user_id)
    if user is None:
        userdoc = gdata("users/%s" % user_id)
        #print(str(etree.tostring(userdoc, pretty_print=True), "utf8"))
        if userdoc.getroot().tag == tag("gd", "errors"):
            user = yfdb.User(id=user_id, name="SUSPENDED USER", status=yfdb.User.ST_SUSPENDED)
            session.add(user)
        else:
            username = userdoc.find(tag("yt", "username"))
            username1 = username.text
            username2 = username.attrib["display"]
            user = yfdb.User(id=user_id, username=username1, name=username2, status=0)
            session.add(user)
    return user


# some path stuff
def make_absolute(path, root=None):
    if not os.path.isabs(path):
        if root is None:
            root = os.getcwd()
        path = os.path.join(root, path)
    return os.path.normpath(path)


def make_dirs_to(args, key):
    path = make_absolute(args.db.getOptionValue(key), args.root)
    if not os.path.exists(path):
        os.makedirs(path)


#------------------------------------------------------------
# v2 compatibility stuff
#------------------------------------------------------------
def v2import_command(args):
    """ import v2 pl/ dir """
    session = args.db.Session()
    folder = os.path.abspath(args.pldir)
    parent = folder.rsplit(os.path.sep, 1)[0]
    
    print("[  DB ]Starting Import in: %s" % parent)
    os.chdir(parent)
    
    nPl = 0
    nVi = 0
    
    for f in os.listdir(folder):
        if f.endswith(".plm"):
            nPl += 1
            with open(os.path.join(folder, f)) as fp:
                meta = json.load(fp)
            
            #import pprint
            #pprint.pprint(meta["meta"])
            
            try:
                playlist_id = meta["meta"]["playlist_id"]
            except KeyError:
                playlist_id = f[:-4]
            
            # Standard playlists are prefixed [PL]
            if not playlist_id.startswith("PL"):
                playlist_id = "PL" + playlist_id
            
            author_name = meta["meta"]["author"]
            playlist_ti = meta["meta"]["name"]
            playlist_su = meta["meta"]["description"]
            
            print("Playlist: %s (%s)" % (playlist_ti, playlist_id))
            
            playlist = yfdb.Playlist(id=playlist_id, user_name=author_name,
                title=playlist_ti, summary=playlist_su)
            
            session.add(playlist)
            
            for item in meta["local"]:
                vid2 = session.query(yfdb.Video).get(item["id"])
                if vid2:
                    print("[ WARN] Dup Video (%s): '%s' and '%s', skipping 2nd" %
                        (item["id"], vid2.title, item["title"]))
                    continue
                
                nVi += 1
                
                vid = yfdb.Video(id=item["id"], title=item["title"],
                   categories=item["category"], description=item["description"],
                   keywords=",".join(item.get("tags", list())), uploaded=item["uploaded"],
                   thumbnails=json.dumps((
                       (0, 0, "", item["thumbnail"]["sqDefault"]),
                       (0, 0, "", item["thumbnail"]["hqDefault"]))),
                    duration=item["duration"])
                
                usr = item["uploader"]
                
                user = session.query(yfdb.User).\
                    filter(yfdb.User.username == usr.lower()).first()
        
                if not user:
                    userdoc = gdata("users/%s" % usr)
                    if userdoc.getroot().tag == tag("gd", "errors"):
                        user = None
                    else:
                        userid = userdoc.find(tag("yt", "userId")).text
                        user = session.query(yfdb.User).get(userid)
                        if not user:
                            username = userdoc.find(tag("yt", "username"))
                            username1 = username.text
                            username2 = username.attrib['display']
                            user = yfdb.User(id=userid, username=username1,
                                name=username2)
                            session.add(user)
                
                vid.author = user
            
            for video_id, dl in meta["downloads"].items():
                path = os.path.abspath(dl["path"])
                
                if not os.path.exists(path):
                    print("[ERROR] '%s' does not exist" % path)
                    continue
                
                if args.move:
                    video = session.query(yfdb.User).get(video_id)
                    newfile = gen_videofn(video, dl["fmt"])
                    newfile2 = newfile + "." + dl["type"]
                    newpath = make_absolute(args.db.getOptionValue("videos_dir"),
                        args.root)
                    newfull = os.path.join(newpath, newfile2)
                    
                    shutil.move(path, newfull)
                    
                    path = newfull
                
                path = os.path.relpath(path, args.root)
                
                loc = yfdb.LocalVideo(video_id=video_id, location=path,
                    created=datetime.datetime.utcnow().isoformat(),
                    fmt=dl["fmt"], status=yfdb.LocalVideo.ST_V2IMPORT)
                
                session.add(loc)
            
            safe = tofilename(playlist_ti)
            
            job = yfdb.Job(type="playlist", playlist_id=playlist_id,
                name="v2import_%s_%s" % (safe, playlist_id),
                target="%s_(v2import)" % safe,
                status=yfdb.Job.ST_NODL | yfdb.Job.ST_RUNONCE | yfdb.Job.ST_V2IMPORT)
            
            session.add(job)
    
    print("[  DB ] Import Done: Imported %i Playlists, %i Videos" % (nPl, nVi))
    session.commit()


#------------------------------------------------------------
# Python entrypoint
#------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main(sys.argv))
