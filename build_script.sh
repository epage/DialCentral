#!/bin/sh

PLATFORM="$1"
if [ "$PLATFORM" != "desktop" -a "$PLATFORM" != "os2007" -a "$PLATFORM" != "os2008" ]; then
	echo "Invalid platform parameter, defaulting to OS 2008"
	PLATFORM="os2008"
else
	echo "Building for $PLATFORM"
fi

LEGACY_GLADE="0"
if [ "$PLATFORM" = "os2007" ]; then
	LEGACY_GLADE="1"
fi
BUILD_BASE=./build-$PLATFORM



# Create PyPackager directory structure from the original files
# Please make sure the following files are in this directory before
# running this script

# gc_dialer_256.png
# gc_dialer_64.png
# gc_dialer_26.png
# gc_dialer.py
# gc_dialer.xml
# gc_dialer.desktop
# gcbackend.py
# browser_emu.py


mkdir -p $BUILD_BASE/usr/share/icons/hicolor/{scalable,26x26,64,64}/hildon
mkdir -p $BUILD_BASE/usr/share/applications/hildon
mkdir -p $BUILD_BASE/usr/local/{bin,lib}

cp gc_dialer/gc_dialer_256.png $BUILD_BASE/usr/share/icons/hicolor/scalable/hildon/gc_dialer.png
cp gc_dialer/gc_dialer_64.png $BUILD_BASE/usr/share/icons/hicolor/64x64/hildon/gc_dialer.png
cp gc_dialer/gc_dialer_26.png $BUILD_BASE/usr/share/icons/hicolor/26x26/hildon/gc_dialer.png

cp gc_dialer/gc_dialer.desktop $BUILD_BASE/usr/share/applications/hildon

cp gc_dialer/gc_dialer.glade $BUILD_BASE/usr/local/lib


#Construct the program by cat-ing all the python files together
echo "#!/usr/bin/python2.5" > $BUILD_BASE/usr/local/bin/gc_dialer.py
#echo "from __future__ import with_statement" >> $BUILD_BASE/usr/local/bin/gc_dialer.py
cat gc_dialer/gc_dialer.py gc_dialer/gcbackend.py gc_dialer/browser_emu.py | grep -e '^import ' | sort -u >> $BUILD_BASE/usr/local/bin/gc_dialer.py
cat gc_dialer/browser_emu.py gc_dialer/gcbackend.py gc_dialer/gc_dialer.py | grep -v 'browser_emu' | grep -v 'gcbackend' | grep -v "#!" >> $BUILD_BASE/usr/local/bin/gc_dialer.py
chmod 755 $BUILD_BASE/usr/local/bin/gc_dialer.py



#Perform platform specific work
if [ "$PLATFORM" != "desktop" ]; then
	echo "	Generic Maemo Support"
	# Compress whitespace for 30% savings, make sure we are a HildonWindow
	sed -i 's/^[ \t]*//;s/[ \t]*$//;s/GtkWindow/HildonWindow/' $BUILD_BASE/usr/local/lib/gc_dialer.glade
fi
