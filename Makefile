PROJECT_NAME=dialcentral
SOURCE_PATH=src
SOURCE=$(SOURCE_PATH)/gc_dialer.py $(SOURCE_PATH)/evo_backend.py $(SOURCE_PATH)/gc_backend.py $(SOURCE_PATH)/browser_emu.py
OBJ=$(SOURCE:.py=.pyc)
TAG_FILE=~/.ctags/$(PROJECT_NAME).tags
BUILD_PATH=./build/

DEBUGGER=winpdb
UNIT_TEST=nosetests -w $(TEST_PATH)
STYLE_TEST=../../Python/tools/pep8.py --ignore=W191
LINT_RC=./support/pylint.rc
LINT=pylint --rcfile=$(LINT_RC)
COVERAGE_TEST=figleaf
PROFILER=pyprofiler
CTAGS=ctags-exuberant

.PHONY: all run debug test lint tags package clean distclean

all: test package

run: $(SOURCE)
	cd $(SOURCE_PATH)/ ; ./gc_dialer.py

debug: $(SOURCE)
	cd $(SOURCE_PATH)/ ; $(DEBUGGER) ./gc_dialer.py

test: $(SOURCE)
	cd $(SOURCE_PATH)/ ; ./gc_dialer.py -t

package:
	rm -Rf $(BUILD_PATH)
	mkdir $(BUILD_PATH)
	cp $(SOURCE_PATH)/$(PROJECT_NAME).py  $(BUILD_PATH)
	cp $(SOURCE_PATH)/gc_dialer.glade  $(BUILD_PATH)
	cp $(SOURCE)  $(BUILD_PATH)
	cp support/$(PROJECT_NAME).desktop $(BUILD_PATH)
	cp support/icons/hicolor/26x26/hildon/$(PROJECT_NAME).png $(BUILD_PATH)/26x26-$(PROJECT_NAME).png
	cp support/icons/hicolor/64x64/hildon/$(PROJECT_NAME).png $(BUILD_PATH)/64x64-$(PROJECT_NAME).png
	cp support/icons/hicolor/scalable/hildon/$(PROJECT_NAME).png $(BUILD_PATH)/scalable-$(PROJECT_NAME).png
	cp support/builddeb.py $(BUILD_PATH)

lint:
	$(foreach file, $(SOURCE), $(LINT) $(file) ; )

tags: $(TAG_FILE) 

clean:
	rm -Rf $(OBJ)
	rm -Rf $(BUILD_PATH)

distclean:
	rm -Rf $(OBJ)
	rm -Rf $(BUILD_PATH)
	rm -Rf $(TAG_FILE)

$(TAG_FILE): $(SOURCE)
	mkdir -p $(dir $(TAG_FILE))
	$(CTAGS) -o $(TAG_FILE) $(SOURCE)

#Makefile Debugging
#Target to print any variable, can be added to the dependencies of any other target
#Userfule flags for make, -d, -p, -n
print-%: ; @$(error $* is $($*) ($(value $*)) (from $(origin $*)))
