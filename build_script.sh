#!/bin/sh

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

# The script creates the directories and concatenates the .py into a
# single python script

mkdir -p build/usr/share/icons/hicolor/scalable/hildon
mkdir -p build/usr/share/icons/hicolor/26x26/hildon
mkdir -p build/usr/share/icons/hicolor/64x64/hildon
mkdir -p build/usr/share/applications/hildon
mkdir -p build/usr/local/bin
mkdir -p build/usr/local/lib

cp gc_dialer/gc_dialer_256.png build/usr/share/icons/hicolor/scalable/hildon/gc_dialer.png
cp gc_dialer/gc_dialer_64.png  build/usr/share/icons/hicolor/64x64/hildon/gc_dialer.png
cp gc_dialer/gc_dialer_26.png  build/usr/share/icons/hicolor/26x26/hildon/gc_dialer.png

cp gc_dialer/gc_dialer.desktop build/usr/share/applications/hildon

cp gc_dialer/gc_dialer.xml     build/usr/local/lib

# Compress whitespace for 30% savings, make sure we are a HildonWindow
sed -i 's/^[ \t]*//;s/[ \t]*$//;s/GtkWindow/HildonWindow/' build/usr/local/lib/gc_dialer.xml

echo "#!/usr/bin/python" > build/usr/local/bin/gc_dialer.py
#echo "from __future__ import with_statement" >> build/usr/local/bin/gc_dialer.py
cat gc_dialer/gc_dialer.py gc_dialer/gcbackend.py gc_dialer/browser_emu.py | grep -e '^import ' | sort -u >> build/usr/local/bin/gc_dialer.py
echo "import hildon" >> build/usr/local/bin/gc_dialer.py
cat gc_dialer/browser_emu.py gc_dialer/gcbackend.py gc_dialer/gc_dialer.py | grep -v 'import ' | grep -v "#!" >> build/usr/local/bin/gc_dialer.py
chmod 755 build/usr/local/bin/gc_dialer.py
