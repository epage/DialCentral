PROJECT_NAME=gc_dialer
SOURCE_PATH=./gc_dialer
SOURCE=$(SOURCE_PATH)/gc_dialer.py $(SOURCE_PATH)/gcbackend.py $(SOURCE_PATH)/browser_emu.py
OBJ=$(SOURCE:.py=.pyc)
TEST_PATH=./tests
TAG_FILE=~/.ctags/$(PROJECT_NAME).tags
PYPACKAGE_FILE=./support/GrandcentralDialer.pypackager

PLATFORM=desktop
ifeq ($(PLATFORM),os2007)
	LEGACY_GLADE=1
else
	LEGACY_GLADE=0
endif
PACKAGE_PATH=./pkg-$(PLATFORM)
BUILD_PATH=./build-$(PLATFORM)
BUILD_BIN=$(BUILD_PATH)/gc_dialer.py

UNIT_TEST=nosetests -w $(TEST_PATH)
STYLE_TEST=../../Python/tools/pep8.py --ignore=W191
LINT=pylint --rcfile=./support/pylint.rc
COVERAGE_TEST=figleaf
PROFILER=pyprofiler
CTAGS=ctags-exuberant

.PHONY: all test lint tags build package clean

all: test tags package

test: $(SOURCE)
	cd $(SOURCE_PATH) ; ./gc_dialer.py -t

lint: $(SOURCE_PATH)
	$(foreach file, $(SOURCE_PATH), $(LINT) $(file) ; )

tags: $(TAG_FILE) 

build: $(BUILD_BIN)
	mkdir -p $(BUILD_PATH)

	cp $(SOURCE_PATH)/gc_dialer_256.png $(BUILD_PATH)
	cp $(SOURCE_PATH)/gc_dialer_64.png $(BUILD_PATH)
	cp $(SOURCE_PATH)/gc_dialer_26.png $(BUILD_PATH)

	cp $(SOURCE_PATH)/gc_dialer.desktop $(BUILD_PATH)

	cp $(SOURCE_PATH)/gc_dialer.glade $(BUILD_PATH)

package: build
	mkdir -p $(PACKAGE_PATH)/build/usr/share/icons/hicolor/scalable/hildon
	mkdir -p $(PACKAGE_PATH)/build/usr/share/icons/hicolor/26x26/hildon
	mkdir -p $(PACKAGE_PATH)/build/usr/share/icons/hicolor/64x64/hildon
	mkdir -p $(PACKAGE_PATH)/build/usr/share/applications/hildon
	mkdir -p $(PACKAGE_PATH)/build/usr/local/lib
	mkdir -p $(PACKAGE_PATH)/build/usr/local/bin

	cp $(BUILD_PATH)/gc_dialer_256.png $(PACKAGE_PATH)/build/usr/share/icons/hicolor/scalable/hildon/gc_dialer.png
	cp $(BUILD_PATH)/gc_dialer_64.png $(PACKAGE_PATH)/build/usr/share/icons/hicolor/64x64/hildon/gc_dialer.png
	cp $(BUILD_PATH)/gc_dialer_26.png $(PACKAGE_PATH)/build/usr/share/icons/hicolor/26x26/hildon/gc_dialer.png

	cp $(BUILD_PATH)/gc_dialer.desktop $(PACKAGE_PATH)/build/usr/share/applications/hildon

	cp $(BUILD_PATH)/gc_dialer.glade $(PACKAGE_PATH)/build/usr/local/lib
	
	cp $(BUILD_BIN) $(PACKAGE_PATH)/build/usr/local/bin

	cp $(PYPACKAGE_FILE) $(PACKAGE_PATH)

clean:
	rm -Rf $(PACKAGE_PATH) $(BUILD_PATH)
	rm -Rf $(OBJ)

$(BUILD_BIN): $(SOURCE)
	mkdir -p $(dir $(BUILD_BIN))

	#Construct the program by cat-ing all the python files together
	echo "#!/usr/bin/python2.5" > $(BUILD_BIN)
	#echo "from __future__ import with_statement" >> $(PACKAGE_PATH)/usr/local/bin/gc_dialer.py
	cat gc_dialer/gc_dialer.py gc_dialer/gcbackend.py gc_dialer/browser_emu.py | grep -e '^import ' | sort -u >> $(BUILD_BIN)
	cat gc_dialer/browser_emu.py gc_dialer/gcbackend.py gc_dialer/gc_dialer.py | grep -v 'browser_emu' | grep -v 'gcbackend' | grep -v "#!" >> $(BUILD_BIN)
	chmod 755 $(BUILD_BIN)

$(TAG_FILE): $(SOURCE)
	mkdir -p $(dir $(TAG_FILE))
	$(CTAGS) -o $(TAG_FILE) $(SOURCE)
