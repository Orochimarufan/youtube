#!/usr/bin/python32
#freeze.py
#cx_Freeze setup.py

print("IMPORTING..")
from cx_Freeze import setup, Executable
import sys, os.path, re
from subprocess import Popen, PIPE

release_tarball = ("install" in sys.argv)

print("ANALYZING SYSTEM..")
if sys.platform=="win32":
    base='Win32GUI'
    ext=".exe"
    file_deps=[("share","share")]
    # installers dont support this
    release_tarball=True
else:
    base=None
    ext=""
    file_deps=[]

pipe = Popen(["git","rev-list","--all"],stdout=PIPE)
pipe.wait()
rev = len(pipe.stdout.read().decode("utf8").strip().split("\n"))

from libyo.version import Version #@UnresolvedImport
version = Version.LibyoVersion.format("{0}.{1}.{2}{patch_i:02}.{{0}}").format(rev)

print("Version = %s"%version)
with open("VERSION","w") as v:
    v.write(version)

print("SETTING UP..")
vlyc = Executable(
    script = "vlyc2.py",
    initScript = None,
    base = base,
    targetName = "vlyc"+ext,
    #icon = os.path.join("res", "konachan.ico")
    )
youfeed = Executable(
    script = "youfeed.py",
    initScript = None,
    base = None,
    targetName = "youfeed"+ext,
    #icon = os.path.join("res", "konachan.ico")
    )
afp = Executable(
	script = "antiflashplayer.py",
	initScript = None,
	base = None,
	targetName = "afp"+ext,
	#icon = os.path.join("res", "konachan.ico")
	)

print("SETUP()...")
options = {"build_exe": {
            "includes": ['re', 'io', "libyo.compat.features.htmlparser_fallback","lxml.html"],
            "excludes": ["libyo.compat.python2"],
            "packages": ["libyo.compat.python3","lxml.html"],
            "path": [],
            "optimize":2,
            #"bin_includes":["libvlc.so.5","libvlccore.so.5"],
            #"bin_path_includes":["/usr/lib"],
            "append_script_to_exe":True,
            "include_files": ["VERSION",
                              ("/usr/lib/libvlc.so.5","libvlc.so.5"),
                              ("/usr/lib/libvlccore.so.5","libvlccore.so.5")],
            }
        }

if not release_tarball:
    options["install"]={"install_exe":""}

setup(
    version = version,
    description = "Youtube Toolchain",
    author = "Orochimarufan",
    name = "YoutubeTools",
    options = options,
    executables = [afp,youfeed,vlyc],
    )

