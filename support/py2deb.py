#!/usr/bin/env python
# -*- coding: utf-8 -*-
##
##    Copyright (C) 2009 manatlan manatlan[at]gmail(dot)com
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published
## by the Free Software Foundation; version 2 only.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
"""
Known limitations :
- don't sign package (-us -uc)
- no distinctions between author and maintainer(packager)

depends on :
- dpkg-dev (dpkg-buildpackage)
- alien
- python
- fakeroot

changelog
 - ??? ?/??/20?? (By epage)
    - PEP8
    - added recommends
    - fixed bug where it couldn't handle the contents of the pre/post scripts being specified
    - Added customization based on the targeted policy for sections (Maemo support)
    - Added maemo specific tarball, dsc, changes file generation support (including icon support)
    - Added armel architecture
    - Reduced the size of params being passed around by reducing the calls to locals()
    - Added respository, distribution, priority
    - Made setting control file a bit more flexible
 - 0.5 05/09/2009
    - pre/post install/remove scripts enabled
    - deb package install py2deb in dist-packages for py2.6
 - 0.4 14/10/2008
    - use os.environ USERNAME or USER (debian way)
    - install on py 2.(4,5,6) (*FIX* do better here)

"""

import os
import hashlib
import sys
import shutil
import time
import string
import StringIO
import stat
import commands
import base64
import tarfile
from glob import glob
from datetime import datetime
import socket # gethostname()
from subprocess import Popen, PIPE

#~ __version__ = "0.4"
__version__ = "0.5"
__author__ = "manatlan"
__mail__ = "manatlan@gmail.com"


PERMS_URW_GRW_OR = stat.S_IRUSR | stat.S_IWUSR | \
                   stat.S_IRGRP | stat.S_IWGRP | \
                   stat.S_IROTH

UID_ROOT = 0
GID_ROOT = 0


def run(cmds):
    p = Popen(cmds, shell=False, stdout=PIPE, stderr=PIPE)
    time.sleep(0.01)    # to avoid "IOError: [Errno 4] Interrupted system call"
    out = string.join(p.stdout.readlines()).strip()
    outerr = string.join(p.stderr.readlines()).strip()
    return out


def deb2rpm(file):
    txt=run(['alien', '-r', file])
    return txt.split(" generated")[0]


def py2src(TEMP, name):
    l=glob("%(TEMP)s/%(name)s*.tar.gz" % locals())
    if len(l) != 1:
        raise Py2debException("don't find source package tar.gz")

    tar = os.path.basename(l[0])
    shutil.move(l[0], tar)

    return tar


def md5sum(filename):
    f = open(filename, "r")
    try:
        return hashlib.md5(f.read()).hexdigest()
    finally:
        f.close()


class Py2changes(object):

    def __init__(self, ChangedBy, description, changes, files, category, repository, **kwargs):
      self.options = kwargs # TODO: Is order important?
      self.description = description
      self.changes=changes
      self.files=files
      self.category=category
      self.repository=repository
      self.ChangedBy=ChangedBy

    def getContent(self):
        content = ["%s: %s" % (k, v)
                   for k,v in self.options.iteritems()]

        if self.description:
            description=self.description.replace("\n","\n ")
            content.append('Description: ')
            content.append(' %s' % description)
        if self.changes:
            changes=self.changes.replace("\n","\n ")
            content.append('Changes: ')
            content.append(' %s' % changes)
        if self.ChangedBy:
            content.append("Changed-By: %s" % self.ChangedBy)

        content.append('Files:')

        for onefile in self.files:
            md5 = md5sum(onefile)
            size = os.stat(onefile).st_size.__str__()
            content.append(' ' + md5 + ' ' + size + ' ' + self.category +' '+self.repository+' '+os.path.basename(onefile))

        return "\n".join(content) + "\n\n"


def py2changes(params):
    changescontent = Py2changes(
        "%(author)s <%(mail)s>" % params,
        "%(description)s" % params,
        "%(changelog)s" % params,
        (
            "%(TEMP)s/%(name)s_%(version)s.tar.gz" % params,
            "%(TEMP)s/%(name)s_%(version)s.dsc" % params,
        ),
        "%(section)s" % params,
        "%(repository)s" % params,
        Format='1.7',
        Date=time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime()),
        Source="%(name)s" % params,
        Architecture="%(arch)s" % params,
        Version="%(version)s" % params,
        Distribution="%(distribution)s" % params,
        Urgency="%(urgency)s" % params,
        Maintainer="%(author)s <%(mail)s>" % params
    )
    f = open("%(TEMP)s/%(name)s_%(version)s.changes" % params,"wb")
    f.write(changescontent.getContent())
    f.close()

    fileHandle = open('/tmp/py2deb2.tmp', 'w')
    fileHandle.write('#!/bin/sh\n')
    fileHandle.write("cd " +os.getcwd()+ "\n")
    # TODO Renable signing
    # fileHandle.write("gpg --local-user %(mail)s --clearsign %(TEMP)s/%(name)s_%(version)s.changes\n" % params)
    fileHandle.write("mv %(TEMP)s/%(name)s_%(version)s.changes.asc %(TEMP)s/%(name)s_%(version)s.changes\n" % params)
    fileHandle.write('\nexit')
    fileHandle.close()
    commands.getoutput("chmod 777 /tmp/py2deb2.tmp")
    commands.getoutput("/tmp/py2deb2.tmp")

    ret = []

    l=glob("%(TEMP)s/%(name)s*.tar.gz" % params)
    if len(l)!=1:
        raise Py2debException("don't find source package tar.gz")
    tar = os.path.basename(l[0])
    shutil.move(l[0],tar)
    ret.append(tar)

    l=glob("%(TEMP)s/%(name)s*.dsc" % params)
    if len(l)!=1:
        raise Py2debException("don't find source package dsc")
    tar = os.path.basename(l[0])
    shutil.move(l[0],tar)
    ret.append(tar)

    l=glob("%(TEMP)s/%(name)s*_*_*.changes" % params)
    if len(l)!=1:
        raise Py2debException("don't find source package changes")
    tar = os.path.basename(l[0])
    shutil.move(l[0],tar)
    ret.append(tar)

    return ret


class Py2dsc(object):

    def __init__(self, StandardsVersion, BuildDepends, files, **kwargs):
      self.options = kwargs # TODO: Is order important?
      self.StandardsVersion = StandardsVersion
      self.BuildDepends=BuildDepends
      self.files=files

    @property
    def content(self):
        content = ["%s: %s" % (k, v)
                   for k,v in self.options.iteritems()]

        if self.BuildDepends:
            content.append("Build-Depends: %s" % self.BuildDepends)
        if self.StandardsVersion:
            content.append("Standards-Version: %s" % self.StandardsVersion)

        content.append('Files:')

        for onefile in self.files:
            print onefile
            md5 = md5sum(onefile)
            size = os.stat(onefile).st_size.__str__()
            content.append(' '+md5 + ' ' + size +' '+os.path.basename(onefile))

        return "\n".join(content)+"\n\n"


def py2dsc(TEMP, name, version, depends, author, mail, arch):
    dsccontent = Py2dsc(
        "%(version)s" % locals(),
        "%(depends)s" % locals(),
        ("%(TEMP)s/%(name)s_%(version)s.tar.gz" % locals(),),
        Format='1.0',
        Source="%(name)s" % locals(),
        Version="%(version)s" % locals(),
        Maintainer="%(author)s <%(mail)s>" % locals(),
        Architecture="%(arch)s" % locals(),
    )

    filename = "%(TEMP)s/%(name)s_%(version)s.dsc" % locals()

    f = open(filename, "wb")
    try:
        f.write(dsccontent.content)
    finally:
        f.close()

    fileHandle = open('/tmp/py2deb.tmp', 'w')
    try:
        fileHandle.write('#!/bin/sh\n')
        fileHandle.write("cd " + os.getcwd() + "\n")
        # TODO Renable signing
        # fileHandle.write("gpg --local-user %(mail)s --clearsign %(TEMP)s/%(name)s_%(version)s.dsc\n" % locals())
        fileHandle.write("mv %(TEMP)s/%(name)s_%(version)s.dsc.asc %(filename)s\n" % locals())
        fileHandle.write('\nexit')
        fileHandle.close()
    finally:
        f.close()

    commands.getoutput("chmod 777 /tmp/py2deb.tmp")
    commands.getoutput("/tmp/py2deb.tmp")

    return filename


class Py2tar(object):

    def __init__(self, dataDirectoryPath):
        self._dataDirectoryPath = dataDirectoryPath

    def packed(self):
        return self._getSourcesFiles()

    def _getSourcesFiles(self):
        directoryPath = self._dataDirectoryPath

        outputFileObj = StringIO.StringIO() # TODO: Do more transparently?

        tarOutput = tarfile.TarFile.open('sources',
                                 mode = "w:gz",
                                 fileobj = outputFileObj)

        # Note: We can't use this because we need to fiddle permissions:
        #       tarOutput.add(directoryPath, arcname = "")

        for root, dirs, files in os.walk(directoryPath):
            archiveRoot = root[len(directoryPath):]

            tarinfo = tarOutput.gettarinfo(root, archiveRoot)
            # TODO: Make configurable?
            tarinfo.uid = UID_ROOT
            tarinfo.gid = GID_ROOT
            tarinfo.uname = ""
            tarinfo.gname = ""
            tarOutput.addfile(tarinfo)

            for f in  files:
                tarinfo = tarOutput.gettarinfo(os.path.join(root, f),
                                               os.path.join(archiveRoot, f))
                tarinfo.uid = UID_ROOT
                tarinfo.gid = GID_ROOT
                tarinfo.uname = ""
                tarinfo.gname = ""
                tarOutput.addfile(tarinfo, file(os.path.join(root, f)))

        tarOutput.close()

        data_tar_gz = outputFileObj.getvalue()

        return data_tar_gz


def py2tar(DEST, TEMP, name, version):
    tarcontent = Py2tar("%(DEST)s" % locals())
    filename = "%(TEMP)s/%(name)s_%(version)s.tar.gz" % locals()
    f = open(filename, "wb")
    try:
        f.write(tarcontent.packed())
    finally:
        f.close()
    return filename


class Py2debException(Exception):
    pass


SECTIONS_BY_POLICY = {
    # http://www.debian.org/doc/debian-policy/ch-archive.html#s-subsections
    "debian": "admin, base, comm, contrib, devel, doc, editors, electronics, embedded, games, gnome, graphics, hamradio, interpreters, kde, libs, libdevel, mail, math, misc, net, news, non-free, oldlibs, otherosfs, perl, python, science, shells, sound, tex, text, utils, web, x11",
    # http://maemo.org/forrest-images/pdf/maemo-policy.pdf
    "chinook": "accessories, communication, games, multimedia, office, other, programming, support, themes, tools",
    # http://wiki.maemo.org/Task:Package_categories
    "diablo": "user/desktop, user/development, user/education, user/games, user/graphics, user/multimedia, user/navigation, user/network, user/office, user/science, user/system, user/utilities",
    # http://wiki.maemo.org/Task:Fremantle_application_categories
    "mer": "user/desktop, user/development, user/education, user/games, user/graphics, user/multimedia, user/navigation, user/network, user/office, user/science, user/system, user/utilities",
    # http://wiki.maemo.org/Task:Fremantle_application_categories
    "fremantle": "user/desktop, user/development, user/education, user/games, user/graphics, user/multimedia, user/navigation, user/network, user/office, user/science, user/system, user/utilities",
}


LICENSE_AGREEMENT = {
        "gpl": """
    This package is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This package is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this package; if not, write to the Free Software
    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

On Debian systems, the complete text of the GNU General
Public License can be found in `/usr/share/common-licenses/GPL'.
""",
        "lgpl":"""
    This package is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2 of the License, or (at your option) any later version.

    This package is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this package; if not, write to the Free Software
    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

On Debian systems, the complete text of the GNU Lesser General
Public License can be found in `/usr/share/common-licenses/LGPL'.
""",
        "bsd": """
    Redistribution and use in source and binary forms, with or without
    modification, are permitted under the terms of the BSD License.

    THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
    ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
    IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
    ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
    FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
    DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
    OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
    HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
    LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
    OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
    SUCH DAMAGE.

On Debian systems, the complete text of the BSD License can be
found in `/usr/share/common-licenses/BSD'.
""",
        "artistic": """
    This program is free software; you can redistribute it and/or modify it
    under the terms of the "Artistic License" which comes with Debian.

    THIS PACKAGE IS PROVIDED "AS IS" AND WITHOUT ANY EXPRESS OR IMPLIED
    WARRANTIES, INCLUDING, WITHOUT LIMITATION, THE IMPLIED WARRANTIES
    OF MERCHANTIBILITY AND FITNESS FOR A PARTICULAR PURPOSE.

On Debian systems, the complete text of the Artistic License
can be found in `/usr/share/common-licenses/Artistic'.
"""
}


class Py2deb(object):
    """
    heavily based on technic described here :
    http://wiki.showmedo.com/index.php?title=LinuxJensMakingDeb
    """
    ## STATICS
    clear = False  # clear build folder after py2debianization

    SECTIONS = SECTIONS_BY_POLICY["debian"]

    #http://www.debian.org/doc/debian-policy/footnotes.html#f69
    ARCHS = "all i386 ia64 alpha amd64 armeb arm hppa m32r m68k mips mipsel powerpc ppc64 s390 s390x sh3 sh3eb sh4 sh4eb sparc darwin-i386 darwin-ia64 darwin-alpha darwin-amd64 darwin-armeb darwin-arm darwin-hppa darwin-m32r darwin-m68k darwin-mips darwin-mipsel darwin-powerpc darwin-ppc64 darwin-s390 darwin-s390x darwin-sh3 darwin-sh3eb darwin-sh4 darwin-sh4eb darwin-sparc freebsd-i386 freebsd-ia64 freebsd-alpha freebsd-amd64 freebsd-armeb freebsd-arm freebsd-hppa freebsd-m32r freebsd-m68k freebsd-mips freebsd-mipsel freebsd-powerpc freebsd-ppc64 freebsd-s390 freebsd-s390x freebsd-sh3 freebsd-sh3eb freebsd-sh4 freebsd-sh4eb freebsd-sparc kfreebsd-i386 kfreebsd-ia64 kfreebsd-alpha kfreebsd-amd64 kfreebsd-armeb kfreebsd-arm kfreebsd-hppa kfreebsd-m32r kfreebsd-m68k kfreebsd-mips kfreebsd-mipsel kfreebsd-powerpc kfreebsd-ppc64 kfreebsd-s390 kfreebsd-s390x kfreebsd-sh3 kfreebsd-sh3eb kfreebsd-sh4 kfreebsd-sh4eb kfreebsd-sparc knetbsd-i386 knetbsd-ia64 knetbsd-alpha knetbsd-amd64 knetbsd-armeb knetbsd-arm knetbsd-hppa knetbsd-m32r knetbsd-m68k knetbsd-mips knetbsd-mipsel knetbsd-powerpc knetbsd-ppc64 knetbsd-s390 knetbsd-s390x knetbsd-sh3 knetbsd-sh3eb knetbsd-sh4 knetbsd-sh4eb knetbsd-sparc netbsd-i386 netbsd-ia64 netbsd-alpha netbsd-amd64 netbsd-armeb netbsd-arm netbsd-hppa netbsd-m32r netbsd-m68k netbsd-mips netbsd-mipsel netbsd-powerpc netbsd-ppc64 netbsd-s390 netbsd-s390x netbsd-sh3 netbsd-sh3eb netbsd-sh4 netbsd-sh4eb netbsd-sparc openbsd-i386 openbsd-ia64 openbsd-alpha openbsd-amd64 openbsd-armeb openbsd-arm openbsd-hppa openbsd-m32r openbsd-m68k openbsd-mips openbsd-mipsel openbsd-powerpc openbsd-ppc64 openbsd-s390 openbsd-s390x openbsd-sh3 openbsd-sh3eb openbsd-sh4 openbsd-sh4eb openbsd-sparc hurd-i386 hurd-ia64 hurd-alpha hurd-amd64 hurd-armeb hurd-arm hurd-hppa hurd-m32r hurd-m68k hurd-mips hurd-mipsel hurd-powerpc hurd-ppc64 hurd-s390 hurd-s390x hurd-sh3 hurd-sh3eb hurd-sh4 hurd-sh4eb hurd-sparc armel".split(" ")

    # license terms taken from dh_make
    LICENSES = list(LICENSE_AGREEMENT.iterkeys())

    def __setitem__(self, path, files):

        if not type(files)==list:
            raise Py2debException("value of key path '%s' is not a list"%path)
        if not files:
            raise Py2debException("value of key path '%s' should'nt be empty"%path)
        if not path.startswith("/"):
            raise Py2debException("key path '%s' malformed (don't start with '/')"%path)
        if path.endswith("/"):
            raise Py2debException("key path '%s' malformed (shouldn't ends with '/')"%path)

        nfiles=[]
        for file in files:

            if ".." in file:
                raise Py2debException("file '%s' contains '..', please avoid that!"%file)


            if "|" in file:
                if file.count("|")!=1:
                    raise Py2debException("file '%s' is incorrect (more than one pipe)"%file)

                file, nfile = file.split("|")
            else:
                nfile=file  # same localisation

            if os.path.isdir(file):
                raise Py2debException("file '%s' is a folder, and py2deb refuse folders !"%file)

            if not os.path.isfile(file):
                raise Py2debException("file '%s' doesn't exist"%file)

            if file.startswith("/"):    # if an absolute file is defined
                if file==nfile:         # and not renamed (pipe trick)
                    nfile=os.path.basename(file)   # it's simply copied to 'path'

            nfiles.append((file, nfile))

        nfiles.sort(lambda a, b: cmp(a[1], b[1]))    #sort according new name (nfile)

        self.__files[path]=nfiles

    def __delitem__(self, k):
        del self.__files[k]

    def __init__(self,
                    name,
                    description="no description",
                    license="gpl",
                    depends="",
                    section="utils",
                    arch="all",

                    url="",
                    author = None,
                    mail = None,

                    preinstall = None,
                    postinstall = None,
                    preremove = None,
                    postremove = None
                ):

        if author is None:
            author = ("USERNAME" in os.environ) and os.environ["USERNAME"] or None
            if author is None:
                author = ("USER" in os.environ) and os.environ["USER"] or "unknown"

        if mail is None:
            mail = author+"@"+socket.gethostname()

        self.name = name
        self.prettyName = ""
        self.description = description
        self.upgradeDescription = ""
        self.bugTracker = ""
        self.license = license
        self.depends = depends
        self.recommends = ""
        self.section = section
        self.arch = arch
        self.url = url
        self.author = author
        self.mail = mail
        self.icon = ""
        self.distribution = ""
        self.respository = ""
        self.urgency = "low"

        self.preinstall = preinstall
        self.postinstall = postinstall
        self.preremove = preremove
        self.postremove = postremove

        self.__files={}

    def __repr__(self):
        name = self.name
        license = self.license
        description = self.description
        depends = self.depends
        recommends = self.recommends
        section = self.section
        arch = self.arch
        url = self.url
        author = self.author
        mail = self.mail

        preinstall = self.preinstall
        postinstall = self.postinstall
        preremove = self.preremove
        postremove = self.postremove

        paths=self.__files.keys()
        paths.sort()
        files=[]
        for path in paths:
            for file, nfile in self.__files[path]:
                #~ rfile=os.path.normpath(os.path.join(path, nfile))
                rfile=os.path.join(path, nfile)
                if nfile==file:
                    files.append(rfile)
                else:
                    files.append(rfile + " (%s)"%file)

        files.sort()
        files = "\n".join(files)


        lscripts = [    preinstall and "preinst",
                        postinstall and "postinst",
                        preremove and "prerm",
                        postremove and "postrm",
                    ]
        scripts = lscripts and ", ".join([i for i in lscripts if i]) or "None"
        return """
----------------------------------------------------------------------
NAME        : %(name)s
----------------------------------------------------------------------
LICENSE     : %(license)s
URL         : %(url)s
AUTHOR      : %(author)s
MAIL        : %(mail)s
----------------------------------------------------------------------
DEPENDS     : %(depends)s
RECOMMENDS  : %(recommends)s
ARCH        : %(arch)s
SECTION     : %(section)s
----------------------------------------------------------------------
DESCRIPTION :
%(description)s
----------------------------------------------------------------------
SCRIPTS : %(scripts)s
----------------------------------------------------------------------
FILES :
%(files)s
""" % locals()

    def generate(self, version, changelog="", rpm=False, src=False, build=True, tar=False, changes=False, dsc=False):
        """ generate a deb of version 'version', with or without 'changelog', with or without a rpm
            (in the current folder)
            return a list of generated files
        """
        if not sum([len(i) for i in self.__files.values()])>0:
            raise Py2debException("no files are defined")

        if not changelog:
            changelog="* no changelog"

        name = self.name
        description = self.description
        license = self.license
        depends = self.depends
        recommends = self.recommends
        section = self.section
        arch = self.arch
        url = self.url
        distribution = self.distribution
        repository = self.repository
        urgency = self.urgency
        author = self.author
        mail = self.mail
        files = self.__files
        preinstall = self.preinstall
        postinstall = self.postinstall
        preremove = self.preremove
        postremove = self.postremove

        if section not in Py2deb.SECTIONS:
            raise Py2debException("section '%s' is unknown (%s)" % (section, str(Py2deb.SECTIONS)))

        if arch not in Py2deb.ARCHS:
            raise Py2debException("arch '%s' is unknown (%s)"% (arch, str(Py2deb.ARCHS)))

        if license not in Py2deb.LICENSES:
            raise Py2debException("License '%s' is unknown (%s)" % (license, str(Py2deb.LICENSES)))

        # create dates (buildDate, buildDateYear)
        d=datetime.now()
        buildDate=d.strftime("%a, %d %b %Y %H:%M:%S +0000")
        buildDateYear=str(d.year)

        #clean description (add a space before each next lines)
        description=description.replace("\r", "").strip()
        description = "\n ".join(description.split("\n"))

        #clean changelog (add 2 spaces before each next lines)
        changelog=changelog.replace("\r", "").strip()
        changelog = "\n  ".join(changelog.split("\n"))

        TEMP = ".py2deb_build_folder"
        DEST = os.path.join(TEMP, name)
        DEBIAN = os.path.join(DEST, "debian")

        packageContents = locals()

        # let's start the process
        try:
            shutil.rmtree(TEMP)
        except:
            pass

        os.makedirs(DEBIAN)
        try:
            rules=[]
            dirs=[]
            for path in files:
                for ofile, nfile in files[path]:
                    if os.path.isfile(ofile):
                        # it's a file

                        if ofile.startswith("/"): # if absolute path
                            # we need to change dest
                            dest=os.path.join(DEST, nfile)
                        else:
                            dest=os.path.join(DEST, ofile)

                        # copy file to be packaged
                        destDir = os.path.dirname(dest)
                        if not os.path.isdir(destDir):
                            os.makedirs(destDir)

                        shutil.copy2(ofile, dest)

                        ndir = os.path.join(path, os.path.dirname(nfile))
                        nname = os.path.basename(nfile)

                        # make a line RULES to be sure the destination folder is created
                        # and one for copying the file
                        fpath = "/".join(["$(CURDIR)", "debian", name+ndir])
                        rules.append('mkdir -p "%s"' % fpath)
                        rules.append('cp -a "%s" "%s"' % (ofile, os.path.join(fpath, nname)))

                        # append a dir
                        dirs.append(ndir)

                    else:
                        raise Py2debException("unknown file '' "%ofile) # shouldn't be raised (because controlled before)

            # make rules right
            rules= "\n\t".join(rules) + "\n"
            packageContents["rules"] = rules

            # make dirs right
            dirs= [i[1:] for i in set(dirs)]
            dirs.sort()

            #==========================================================================
            # CREATE debian/dirs
            #==========================================================================
            open(os.path.join(DEBIAN, "dirs"), "w").write("\n".join(dirs))

            #==========================================================================
            # CREATE debian/changelog
            #==========================================================================
            clog="""%(name)s (%(version)s) stable; urgency=low

  %(changelog)s

 -- %(author)s <%(mail)s>  %(buildDate)s
""" % packageContents

            open(os.path.join(DEBIAN, "changelog"), "w").write(clog)

            #==========================================================================
            #Create pre/post install/remove
            #==========================================================================
            def mkscript(name, dest):
                if name and name.strip()!="":
                    if os.path.isfile(name):    # it's a file
                        content = file(name).read()
                    else:   # it's a script
                        content = name
                    open(os.path.join(DEBIAN, dest), "w").write(content)

            mkscript(preinstall, "preinst")
            mkscript(postinstall, "postinst")
            mkscript(preremove, "prerm")
            mkscript(postremove, "postrm")


            #==========================================================================
            # CREATE debian/compat
            #==========================================================================
            open(os.path.join(DEBIAN, "compat"), "w").write("5\n")

            #==========================================================================
            # CREATE debian/control
            #==========================================================================
            generalParagraphFields = [
                "Source: %(name)s",
                "Maintainer: %(author)s <%(mail)s>",
                "Section: %(section)s",
                "Priority: extra",
                "Build-Depends: debhelper (>= 5)",
                "Standards-Version: 3.7.2",
            ]

            specificParagraphFields = [
                "Package: %(name)s",
                "Architecture: %(arch)s",
                "Depends: %(depends)s",
                "Recommends: %(recommends)s",
                "Description: %(description)s",
            ]

            if self.prettyName:
                prettyName = "XSBC-Maemo-Display-Name: %s" % self.prettyName.strip()
                specificParagraphFields.append("\n  ".join(prettyName.split("\n")))

            if self.bugTracker:
                bugTracker = "XSBC-Bugtracker: %s" % self.bugTracker.strip()
                specificParagraphFields.append("\n  ".join(bugTracker.split("\n")))

            if self.upgradeDescription:
                upgradeDescription = "XSBC-Maemo-Upgrade-Description: %s" % self.upgradeDescription.strip()
                specificParagraphFields.append("\n  ".join(upgradeDescription.split("\n")))

            if self.icon:
                f = open(self.icon, "rb")
                try:
                    rawIcon = f.read()
                finally:
                    f.close()
                uueIcon = base64.b64encode(rawIcon)
                uueIconLines = []
                for i, c in enumerate(uueIcon):
                    if i % 60 == 0:
                        uueIconLines.append("")
                    uueIconLines[-1] += c
                uueIconLines[0:0] = ("XSBC-Maemo-Icon-26:", )
                specificParagraphFields.append("\n  ".join(uueIconLines))

            generalParagraph = "\n".join(generalParagraphFields)
            specificParagraph = "\n".join(specificParagraphFields)
            controlContent = "\n\n".join((generalParagraph, specificParagraph)) % packageContents
            open(os.path.join(DEBIAN, "control"), "w").write(controlContent)

            #==========================================================================
            # CREATE debian/copyright
            #==========================================================================
            packageContents["txtLicense"] = LICENSE_AGREEMENT[license]
            packageContents["pv"] =__version__
            txt="""This package was py2debianized(%(pv)s) by %(author)s <%(mail)s> on
%(buildDate)s.

It was downloaded from %(url)s

Upstream Author: %(author)s <%(mail)s>

Copyright: %(buildDateYear)s by %(author)s

License:

%(txtLicense)s

The Debian packaging is (C) %(buildDateYear)s, %(author)s <%(mail)s> and
is licensed under the GPL, see above.


# Please also look if there are files or directories which have a
# different copyright/license attached and list them here.
""" % packageContents
            open(os.path.join(DEBIAN, "copyright"), "w").write(txt)

            #==========================================================================
            # CREATE debian/rules
            #==========================================================================
            txt="""#!/usr/bin/make -f
# -*- makefile -*-
# Sample debian/rules that uses debhelper.
# This file was originally written by Joey Hess and Craig Small.
# As a special exception, when this file is copied by dh-make into a
# dh-make output file, you may use that output file without restriction.
# This special exception was added by Craig Small in version 0.37 of dh-make.

# Uncomment this to turn on verbose mode.
#export DH_VERBOSE=1




CFLAGS = -Wall -g

ifneq (,$(findstring noopt,$(DEB_BUILD_OPTIONS)))
	CFLAGS += -O0
else
	CFLAGS += -O2
endif

configure: configure-stamp
configure-stamp:
	dh_testdir
	# Add here commands to configure the package.

	touch configure-stamp


build: build-stamp

build-stamp: configure-stamp
	dh_testdir
	touch build-stamp

clean:
	dh_testdir
	dh_testroot
	rm -f build-stamp configure-stamp
	dh_clean

install: build
	dh_testdir
	dh_testroot
	dh_clean -k
	dh_installdirs

	# ======================================================
	#$(MAKE) DESTDIR="$(CURDIR)/debian/%(name)s" install
	mkdir -p "$(CURDIR)/debian/%(name)s"

	%(rules)s
	# ======================================================

# Build architecture-independent files here.
binary-indep: build install
# We have nothing to do by default.

# Build architecture-dependent files here.
binary-arch: build install
	dh_testdir
	dh_testroot
	dh_installchangelogs debian/changelog
	dh_installdocs
	dh_installexamples
#	dh_install
#	dh_installmenu
#	dh_installdebconf
#	dh_installlogrotate
#	dh_installemacsen
#	dh_installpam
#	dh_installmime
#	dh_python
#	dh_installinit
#	dh_installcron
#	dh_installinfo
	dh_installman
	dh_link
	dh_strip
	dh_compress
	dh_fixperms
#	dh_perl
#	dh_makeshlibs
	dh_installdeb
	dh_shlibdeps
	dh_gencontrol
	dh_md5sums
	dh_builddeb

binary: binary-indep binary-arch
.PHONY: build clean binary-indep binary-arch binary install configure
""" % packageContents
            open(os.path.join(DEBIAN, "rules"), "w").write(txt)
            os.chmod(os.path.join(DEBIAN, "rules"), 0755)

            ###########################################################################
            ###########################################################################
            ###########################################################################

            generatedFiles = []

            if build:
                #http://www.debian.org/doc/manuals/maint-guide/ch-build.fr.html
                ret = os.system('cd "%(DEST)s"; dpkg-buildpackage -tc -rfakeroot -us -uc' % packageContents)
                if ret != 0:
                    raise Py2debException("buildpackage failed (see output)")

                l=glob("%(TEMP)s/%(name)s*.deb" % packageContents)
                if len(l) != 1:
                    raise Py2debException("didn't find builded deb")

                tdeb = l[0]
                deb = os.path.basename(tdeb)
                shutil.move(tdeb, deb)

                generatedFiles = [deb, ]

                if rpm:
                    rpmFilename = deb2rpm(deb)
                    generatedFiles.append(rpmFilename)

                if src:
                    tarFilename = py2src(TEMP, name)
                    generatedFiles.append(tarFilename)

            if tar:
                tarFilename = py2tar(DEST, TEMP, name, version)
                generatedFiles.append(tarFilename)

            if dsc:
                dscFilename = py2dsc(TEMP, name, version, depends, author, mail, arch)
                generatedFiles.append(dscFilename)

            if changes:
                changesFilenames = py2changes(packageContents)
                generatedFiles.extend(changesFilenames)

            return generatedFiles

        #~ except Exception,m:
            #~ raise Py2debException("build error :"+str(m))

        finally:
            if Py2deb.clear:
                shutil.rmtree(TEMP)


if __name__ == "__main__":
    try:
        os.chdir(os.path.dirname(sys.argv[0]))
    except:
        pass

    p=Py2deb("python-py2deb")
    p.description="Generate simple deb(/rpm/tgz) from python (2.4, 2.5 and 2.6)"
    p.url = "http://www.manatlan.com/page/py2deb"
    p.author=__author__
    p.mail=__mail__
    p.depends = "dpkg-dev, fakeroot, alien, python"
    p.section="python"
    p["/usr/lib/python2.6/dist-packages"] = ["py2deb.py", ]
    p["/usr/lib/python2.5/site-packages"] = ["py2deb.py", ]
    p["/usr/lib/python2.4/site-packages"] = ["py2deb.py", ]
    #~ p.postinstall = "s.py"
    #~ p.preinstall = "s.py"
    #~ p.postremove = "s.py"
    #~ p.preremove = "s.py"
    print p
    print p.generate(__version__, changelog = __doc__, src=True)
