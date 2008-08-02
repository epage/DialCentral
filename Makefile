PROJECT_NAME=gc_dialer
PROJECT_VERSION=0.8.0
SOURCE_PATH=src
SOURCE=$(SOURCE_PATH)/gc_dialer.py $(SOURCE_PATH)/gcbackend.py $(SOURCE_PATH)/browser_emu.py
OBJ=$(SOURCE:.py=.pyc)
LINT_STATS_PATH=~/.pylint.d
LINT_STATS=$(foreach file, $(addsuffix 1.stats,$(subst /,.,$(basename $(SOURCE)))), $(LINT_STATS_PATH)/$(file) )
TEST_PATH=./tests
TAG_FILE=~/.ctags/$(PROJECT_NAME).tags
PYPACKAGE_FILE=./support/GrandcentralDialer.pypackager
DEB_METADATA=./support/DEBIAN
SDK_DISPLAY=:2

PLATFORM=desktop
ifeq ($(PLATFORM),os2007)
	LEGACY_GLADE=1
else
	LEGACY_GLADE=0
endif
PRE_PACKAGE_PATH=./pkg-$(PLATFORM)
PACKAGE_PATH=./deb-$(PLATFORM)
BUILD_PATH=./build-$(PLATFORM)
BUILD_BIN=$(BUILD_PATH)/gc_dialer.py
DEB_PACKAGE=$(PACKAGE_PATH)/$(PROJECT_NAME)-$(PROJECT_VERSION)_$(PLATFORM).deb

DEBUGGER=winpdb
UNIT_TEST=nosetests -w $(TEST_PATH)
STYLE_TEST=../../Python/tools/pep8.py --ignore=W191
LINT=pylint --rcfile=./support/pylint.rc
COVERAGE_TEST=figleaf
PROFILER=pyprofiler
CTAGS=ctags-exuberant

.PHONY: all run debug test lint tags build package clean

all: test tags package

run: $(SOURCE)
	cd $(SOURCE_PATH) ; ./gc_dialer.py

debug: $(SOURCE)
	cd $(SOURCE_PATH) ; $(DEBUGGER) ./gc_dialer.py

test: $(SOURCE)
	cd $(SOURCE_PATH) ; ./gc_dialer.py -t

xephyr:
	 Xephyr $(SDK_DISPLAY) -host-cursor -screen 800x480x16 -dpi 96 -ac

sdk_start:
	export DISPLAY=$(SDK_DISPLAY)
	af-sb-ini.sh start

sdk_stop:
	af-sb-ini.sh stop

lint: $(LINT_STATS)

tags: $(TAG_FILE) 

build: $(BUILD_PATH)

package: $(DEB_PACKAGE)

$(BUILD_PATH): $(BUILD_BIN)
	mkdir -p $(BUILD_PATH)

	cp $(SOURCE_PATH)/gc_dialer_256.png $(BUILD_PATH)
	cp $(SOURCE_PATH)/gc_dialer_64.png $(BUILD_PATH)
	cp $(SOURCE_PATH)/gc_dialer_26.png $(BUILD_PATH)

	cp $(SOURCE_PATH)/gc_contact.png $(BUILD_PATH)

	cp $(SOURCE_PATH)/gc_dialer.desktop $(BUILD_PATH)

	cp $(SOURCE_PATH)/gc_dialer.glade $(BUILD_PATH)

$(PRE_PACKAGE_PATH): $(BUILD_PATH)
	mkdir -p $(PRE_PACKAGE_PATH)/build/usr/share/icons/hicolor/scalable/hildon
	mkdir -p $(PRE_PACKAGE_PATH)/build/usr/share/icons/hicolor/26x26/hildon
	mkdir -p $(PRE_PACKAGE_PATH)/build/usr/share/icons/hicolor/64x64/hildon
	mkdir -p $(PRE_PACKAGE_PATH)/build/usr/share/applications/hildon
	mkdir -p $(PRE_PACKAGE_PATH)/build/usr/local/lib
	mkdir -p $(PRE_PACKAGE_PATH)/build/usr/local/bin

	cp $(BUILD_PATH)/gc_dialer_256.png $(PRE_PACKAGE_PATH)/build/usr/share/icons/hicolor/scalable/hildon/gc_dialer.png
	cp $(BUILD_PATH)/gc_dialer_64.png $(PRE_PACKAGE_PATH)/build/usr/share/icons/hicolor/64x64/hildon/gc_dialer.png
	cp $(BUILD_PATH)/gc_dialer_26.png $(PRE_PACKAGE_PATH)/build/usr/share/icons/hicolor/26x26/hildon/gc_dialer.png

	cp $(BUILD_PATH)/gc_contact.png $(PRE_PACKAGE_PATH)/build/usr/share/icons/hicolor/scalable/hildon/gc_contact.png

	cp $(BUILD_PATH)/gc_dialer.desktop $(PRE_PACKAGE_PATH)/build/usr/share/applications/hildon

	cp $(BUILD_PATH)/gc_dialer.glade $(PRE_PACKAGE_PATH)/build/usr/local/lib
ifneq ($(PLATFORM),desktop)
	sed -i 's/^[ \t]*//;s/GtkWindow/HildonWindow/' $(PRE_PACKAGE_PATH)/build/usr/local/lib/gc_dialer.glade
endif

	cp $(BUILD_BIN) $(PRE_PACKAGE_PATH)/build/usr/local/bin

	cp $(PYPACKAGE_FILE) $(PRE_PACKAGE_PATH)
	cp -R $(DEB_METADATA) $(PRE_PACKAGE_PATH)/build/
ifeq ($(PLATFORM),desktop)
	sed -i 's/, python2.5-hildon//' $(PRE_PACKAGE_PATH)/build/DEBIAN/control
endif

$(DEB_PACKAGE): $(PRE_PACKAGE_PATH)
	mkdir -p $(PACKAGE_PATH)
	dpkg-deb -b $(PRE_PACKAGE_PATH)/build/ $(DEB_PACKAGE)

clean:
	rm -Rf $(PRE_PACKAGE_PATH) $(PACKAGE_PATH) $(BUILD_PATH)
	rm -Rf $(DEB_PACKAGE)
	rm -Rf $(OBJ)
	rm -Rf $(LINT_STATS_PATH)/*

$(BUILD_BIN): $(SOURCE)
	mkdir -p $(dir $(BUILD_BIN))

	#Construct the program by cat-ing all the python files together
	echo "#!/usr/bin/python2.5" > $(BUILD_BIN)
	#echo "from __future__ import with_statement" >> $(PRE_PACKAGE_PATH)/usr/local/bin/gc_dialer.py
	cat $(SOURCE_PATH)/gc_dialer.py $(SOURCE_PATH)/gcbackend.py $(SOURCE_PATH)/browser_emu.py | grep -e '^import ' | sort -u >> $(BUILD_BIN)
	cat $(SOURCE_PATH)/browser_emu.py $(SOURCE_PATH)/gcbackend.py $(SOURCE_PATH)/gc_dialer.py | grep -v 'browser_emu' | grep -v 'gcbackend' | grep -v "#!" >> $(BUILD_BIN)
	chmod 755 $(BUILD_BIN)

$(TAG_FILE): $(SOURCE)
	mkdir -p $(dir $(TAG_FILE))
	$(CTAGS) -o $(TAG_FILE) $(SOURCE)

%1.stats: $(SOURCE)
	@ #DESIRED DEPENDENCY: $(subst .,/,$(notdir $*)).py
	@ #DESIRED COMMAND: $(LINT) $<
	@ $(LINT) $(subst .,/,$(notdir $*)).py
	@# echo $*
	@# echo $?

#Makefile Debugging
#Target to print any variable, can be added to the dependencies of any other target
#Userfule flags for make, -d, -p, -n
print-%: ; @$(error $* is $($*) ($(value $*)) (from $(origin $*)))
