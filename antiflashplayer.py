#!/usr/bin/env python
'''
/*****************************************************************************
 * antiflashplayer.py : AntiFlashPlayer program
 ****************************************************************************
 * Copyright (C) 2012 Orochimarufan
 *
 * Authors:  Orochimarufan <orochimarufan.x3@gmail.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston MA 02110-1301, USA.
 *****************************************************************************/
'''

from __future__ import absolute_import,print_function,unicode_literals

version = "2.0.4"
need_libyo = (0,9,13)

import sys
import logging
import libyo

if __name__ != "__main__":
    # welcome() will check it in __main__ launches
    if (2,6) > sys.version_info:
        raise ImportError("python > 2.6 required")
    if need_libyo > libyo.version_info:
        raise ImportError("libyo > {0} required".\
                format(".".join(map(str,need_libyo))))

from libyo import compat
from libyo.compat import uni
from libyo.youtube.resolve import profiles, resolve3
from libyo.youtube.url import getIdFromUrl
from libyo.youtube.exception import YouTubeException, YouTubeResolveError
from libyo.youtube.subtitles import getTracks as getSubTracks
from libyo.util.choice import cichoice, qchoice, switchchoice
from libyo.util.util import listreplace_s as lreplace
from libyo.util.pretty import fillA, fillP
from libyo.argparse import ArgumentParser, RawTextHelpFormatter, LibyoArgumentParser
from libyo.compat.bltin import input

import tempfile
import shlex
import os
import io
import subprocess
import copy
import platform
import string

try:
    import readline
except ImportError:
    HAS_READLINE=False
else:
    HAS_READLINE=True

# Filename Rules
allow_spaces    = False
allow_invalid   = False
valid_filename  = "-_.{ascii_letters}{digits}".format(**string.__dict__)
invalid_replace = ""
space_replace   = "_"

# Filename Generation
_tfn_spaces = (lambda s: s) if allow_spaces \
else (lambda s: s.replace(" ","_"))
_tfn_validc = (lambda c: c) if allow_invalid \
else (lambda c: c if c in valid_filename else invalid_replace)
tofilename = lambda s: "".join([_tfn_validc(c) for c in _tfn_spaces(s)])

firstkey = lambda i: next(iter(i))

# Platform Code
if platform.system()=="cli": #IronPython OS Detection
    WINSX = platform.win32_ver()[0]!=""
else:
    WINSX = platform.system()=="Windows"

# Tempfile code
class TempFile(io.TextIOWrapper):
    def __init__(self,prefix,suffix):
        cargs = { "prefix":prefix, "suffix":suffix, "mode":"w+b" }
        if WINSX:
            cargs["delete"]=False
        self.tempfile = tempfile.NamedTemporaryFile(**cargs)
        if (3,) > sys.version_info:
            self.tempfile.readable=self.tempfile.writable=self.tempfile.seekable=lambda: True
        super(TempFile,self).__init__(self.tempfile)
    def unlock(self):
        self.flush()
        if WINSX:
            self.close()
            self.tempfile.close()
    def dispose(self):
        if not WINSX:
            self.close()
            self.tempfile.close()
        self.tempfile.unlink() #get rid of it, close() should do the work on *NIX systems, but bsts.

def welcome():
    print("AntiFlashPlayer for YouTube {0} (libyo {1})".format(version, libyo.version))
    print("(c) 2011-2012 by Orochimarufan")
    if need_libyo > libyo.version_info:
        raise SystemError("AntiFlashPlayer requires at least libyo {0}".format(".".join(map(str,libyo_needed))))
    if (2,6) > sys.version_info:
        raise SystemError("AntiFlashPlayer requires at least Python 2.6")
    if (3,) < sys.version_info < (3,2):
        print("INFO: Python 3.x < 3.2 is not tested")
    print()

def main_argv(argv):
    return main(len(argv),argv)

def main(ARGC,ARGV):
    welcome()
    parser = ArgumentParser(prog=ARGV[0],formatter_class=RawTextHelpFormatter,
                            description="Playback YouTube Videos without flashplayer")
    parser.add_argument("id", metavar="VideoID", type=str, help="The YouTube Video ID")
    parser.add_argument("-u","--url", dest="extract_url", action="store_true", default=False, help="VideoID is a URL; Extract the ID from it.")
    parser.add_argument("-q","--quality", metavar="Q", dest="quality", action="store", choices=qchoice.new(1080,720,480,360,240), default="480", help="Quality (Will automatically lower Quality if not avaiable!) [Default: %(default)sp]")
    parser.add_argument("-a","--avc", metavar="PRF", dest="avc", action="store", choices=cichoice(profiles.profiles.keys()), default=firstkey(profiles.profiles), help="What Profile to use [Default: %(default)s]\nUse '%(prog)s -i profiles' to show avaliable choices")
    parser.add_argument("-f","--force",dest="force",action="store_true",default=False,help="Force Quality Level (don't jump down)")
    parser.add_argument("-y","--fmt",dest="fmt",metavar="FMT",action="store",type=int,choices=profiles.descriptions.keys(),help="Specify FMT Level. (For Advanced Users)\nUse '%(prog)s -i fmt' to show known Values")
    parser.add_argument("-c","--cmd", metavar="CMD", dest="command", default="vlc %u vlc://quit --sub-file=%s", action="store", help="Media PLayer Command. use \x25\x25u for url"); #use %% to get around the usage of % formatting in argparse
    parser.add_argument("-n","--not-quiet",dest="quiet",action="store_false",default=True,help="Show Media Player Output")
    parser.add_argument("-x","--xspf",dest="xspf",action="store_true",default=False,help="Don't Play the URL directly, but create a XSPF Playlist and play that. (With Title Information etc.)")
    parser.add_argument("-s","--sub",dest="sub",action="store_true",default=False,help="Enable Subtitles (use %%s in the cmd for subtitlefile)")
    parser.add_argument("-i","--internal",dest="int",action="store_true",default=False,help="Treat VideoID as AFP internal command\nUse '%(prog)s -i help' for more Informations.")
    parser.add_argument("-v","--verbose",dest="verbose",action="store_true",default=False,help="Output more Details")
    #parser.add_argument("-s","--shell",dest="shell",action="store_true",default=False,help="Run internal Shell")
    args    = parser.parse_args(ARGV[1:])
    args.id = args.id.lstrip("\\")
    args.prog = parser.prog

    if args.int:
        return internal_cmd(args)
    #elif args.shell:
    #    return afp_shell(args)
    else:
        return process(args)

def internal_cmd(args):
    if args.id.lower() in ("fmt","fmtcodes","fmtvalues"):
        print("Known FMT Values are:")
        for c,d in profiles.descriptions.items():
            print("FMT {}. Corresponds to: {}".format(fillP(c,3),d))
    elif args.id.lower() in ("help","h"):
        print(
                """Usage: {0} -i [command]
                \tAll non-Playing Commands are considered Internal
                Commands:
                \thelp     : show this help message"
                \tfmt      : show known fmt values"
                \tprofiles : show available Profiles
                \tshell    : open a shell that continuously accepts urls""".format(args.prog))
    elif args.id.lower() in ("profiles",):
        print("Available Profiles are:")
        i=max((len(i) for i in profiles.profiles.keys()))
        j=max((len(k) for z,k in profiles.profiles.values()))
        k=" (Default)"
        print("{0} : {1} [{2}]".format(fillA("<Name>",i),fillA("<Description>",j),"<Avaiable FMTs>"))
        for n,(f,d) in profiles.profiles.items():
            print("{0} : {1} [{2}]{3}".format(fillA(n,i),fillA(d,j),",".join([str(x) for x in f.keys()]),k))
            k=""
    elif args.id.lower() in ("shell",):
        return afp_shell(args)
    else:
        print("Unknown internal Command.\nUse '{0} -i help' for more Informations.".format(args.prog))
        return 1
    return 0

def process(args):
    if args.extract_url:
        args.url=args.id
        try:
            args.id=getIdFromUrl(args.url)
        except AttributeError:
            print("ERROR: invalid URL")
            return
    fmt_map = profiles.profiles[cichoice.unify(args.avc)][0]
    if args.fmt is None and not args.force:
        fmt_request   = [fmt_map[i] for i in (1080,720,480,360,240) if i in fmt_map and i<=qchoice.unify(args.quality)]
    elif args.fmt is not None:
        fmt_request   = [args.fmt]
    elif args.force:
        fmt_request   = [fmt_map[qchoice.unify(args.quality)]]

    print("Receiving Video with ID '{0}'".format(args.id))
    video_info = resolve3(args.id)
    if not video_info:
        print("ERROR: Could not find Video (Maybe your Internet connection is down?)")
        return 1

    print("Found Video: \"{0}\"".format(video_info.title))
    print("Searching for a video url: {0}p ({1})".format(qchoice.unify(args.quality),args.avc))
    if (args.verbose):
        print("Requested FMT: [{0}]".format(",".join(str(k) for k in fmt_request)))
        print("Available FMT: [{0}]".format(",".join(str(k) for k in video_info.urlmap.keys())))
    for fmt in fmt_request:
        if fmt in video_info.urlmap:
            url = video_info.fmt_url(fmt)
            break
    else:
        print("ERROR: Could not find a video url matching your request. maybe try another profile?")
        return 1
    if args.verbose:
        print("Found FMT: {0} ({1})".format(fmt,profiles.descriptions[fmt]))
    else:
        print("Found a Video URL: {0}".format(profiles.descriptions[fmt]))

    #Subtitles
    subtitle_file=""
    if args.sub:
        print("Looking for Subtitles",end="\r")
        tracks = getSubTracks(args.id)
        if len(tracks)<1:
            print("No Subtitles Found!  ")
        else:
            track = tracks[0]
            print("Enabling Subtitles: "+track.lang_original)
            srtfile = TempFile("afpSubtitle_",".srt")
            srtfile.write(track.getSRT())
            srtfile.unlock()
            subtitle_file = srtfile.name

    #XSPF File
    if args.xspf:
        from libyo.xspf.simple import Playlist,Track
        xspf = Playlist(video_info.title)
        xspf.append(Track(video_info.title,video_info.uploader,uri=url))
        xspf[0].annotation = video_info.description
        xspf[0].image = "http://s.ytimg.com/vi/{0}/default.jpg".format(video_info.video_id)
        xspf[0].info = "http://www.youtube.com/watch?v={0}".format(video_info.video_id)
        temp = TempFile("afp_",".xspf")
        xspf.write(temp)
        fn=temp.name
        if args.verbose:
            print("XSPF Filename: "+fn)
        temp.unlock()
    else:
        fn=url
    argv = map(uni.u,shlex.split(uni.nativestring(args.command)))
    for pair in [("\0",""),
                ("%u",fn),
                ("%s",subtitle_file),
                ("%n",video_info.title),
                #("%a",video_info.uploader),
                ("%e",profiles.file_extensions[fmt]),
                ("%f","{0}.{1}".format(tofilename(video_info.title),profiles.file_extensions[fmt]))]:
        argv = lreplace(argv,*pair)
    if args.quiet:
        out_fp=open(os.devnull,"w")
    else:
        print("calling '{0}'".format(" ".join(argv)))
        out_fp=None
        print()
    subprocess.call(argv,stdout=out_fp,stderr=out_fp)
    if args.xspf:
        temp.dispose()
    return 0

def afp_shell(args):
    my_args = copy.copy(args)
    running = True
    parser = LibyoArgumentParser(prog="AFP Shell",may_exit=False,autoprint_usage=False,error_handle=sys.stdout)
    parser.add_argument("id",help="VideoID / URL / literals '+exit', '+pass', '+print'", metavar="OPERATION")
    parser.add_argument("-s","--switches",dest="switches",help="Set enabled switches (u,x,f,n,v,s)",choices=switchchoice(["u","x","f","n","v","s"]),metavar="SW")
    parser.add_argument("-a","--avc",dest="avc",help="Set Profile",choices=cichoice(profiles.profiles.keys()),metavar="PROFILE")
    parser.add_argument("-q","--quality",dest="quality",help="Set Quality Level",choices=qchoice.new(1080,720,480,360,240))
    parser.add_argument("-c","--cmd",dest="command",help="set command")
    if HAS_READLINE:
        readline.parse_and_bind("\eA: previous-history")
        readline.parse_and_bind("\eB: next-history")
    else:
        print("WARNING: No Readline extension found. Readline functionality will NOT be available. If you're on Windows you might want to consider PyReadline.")
    sw = my_args.switches = ("u" if args.extract_url else "")+("x" if args.xspf else "")+("f" if args.force else"")+("n" if not args.quiet else "")+("v" if args.verbose else "")+("s" if args.sub else "")
    while running:
        line = input("{0}> ".format(args.prog))
        try:
            parser.parse_args(shlex.split(line), my_args)
        except SystemExit:
            print("""Use "+pass --help" to show available options""")
            continue
        if sw != my_args.switches:
            my_args.extract_url = "u" in my_args.switches
            my_args.xspf = "x" in my_args.switches
            my_args.force = "f" in my_args.switches
            my_args.quiet = "n" not in my_args.switches
            my_args.verbose = "v" in my_args.switches
            my_args.sub = "s" in my_args.switches
            sw = my_args.switches
        if my_args.id =="+pass":
            continue
        elif my_args.id == "+print":
            print("Switches: [{0}]\nProfile: {1}p {2}\nCommand: {3}".format(my_args.switches,my_args.quality,my_args.avc,my_args.command))
            continue
        elif my_args.id == "+exit":
            running = False
            break
        else:
            try:
                process(my_args)
            except YouTubeException:
                print(sys.exc_info()[1])
    #end while
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main_argv(sys.argv))
