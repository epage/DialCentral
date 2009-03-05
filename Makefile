PROJECT_NAME=dialcentral
SOURCE_PATH=src
SOURCE=$(SOURCE_PATH)/gc_dialer.py $(SOURCE_PATH)/gc_views.py $(SOURCE_PATH)/null_views.py $(SOURCE_PATH)/file_backend.py $(SOURCE_PATH)/evo_backend.py $(SOURCE_PATH)/gc_backend.py $(SOURCE_PATH)/browser_emu.py $(SOURCE_PATH)/__init__.py
PROGRAM=$(SOURCE_PATH)/$(PROJECT_NAME).py
OBJ=$(SOURCE:.py=.pyc)
BUILD_PATH=./build/
TAG_FILE=~/.ctags/$(PROJECT_NAME).tags

DEBUGGER=winpdb
UNIT_TEST=nosetests --with-doctest -w .
STYLE_TEST=../../Python/tools/pep8.py --ignore=W191
LINT_RC=./support/pylint.rc
LINT=pylint --rcfile=$(LINT_RC)
PROFILE_GEN=python -m cProfile -o .profile
PROFILE_VIEW=python -m pstats .profile
CTAGS=ctags-exuberant

.PHONY: all run debug test lint tags package clean distclean

all: test package

run: $(SOURCE)
	$(SOURCE_PATH)/gc_dialer.py

profile: $(SOURCE)
	$(PROFILE_GEN) $(PROGRAM)
	$(PROFILE_VIEW)

debug: $(SOURCE)
	$(DEBUGGER) $(PROGRAM)

test: $(SOURCE)
	$(UNIT_TEST)

package:
	rm -Rf $(BUILD_PATH)
	mkdir $(BUILD_PATH)
	cp $(SOURCE_PATH)/$(PROJECT_NAME).py  $(BUILD_PATH)
	cp $(SOURCE_PATH)/gc_dialer.glade  $(BUILD_PATH)
	cp $(SOURCE)  $(BUILD_PATH)
	cp support/$(PROJECT_NAME).desktop $(BUILD_PATH)
	cp support/icons/hicolor/26x26/hildon/$(PROJECT_NAME).png $(BUILD_PATH)/26x26-$(PROJECT_NAME).png
	cp support/icons/hicolor/64x64/hildon/$(PROJECT_NAME).png $(BUILD_PATH)/64x64-$(PROJECT_NAME).png
	cp support/icons/hicolor/scalable/hildon/$(PROJECT_NAME).png $(BUILD_PATH)/scale-$(PROJECT_NAME).png
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
	find $(SOURCE_PATH) -name "*.*~" | xargs rm -f
	find $(SOURCE_PATH) -name "*.swp" | xargs rm -f
	find $(SOURCE_PATH) -name "*.bak" | xargs rm -f
	find $(SOURCE_PATH) -name ".*.swp" | xargs rm -f

$(TAG_FILE): $(SOURCE)
	mkdir -p $(dir $(TAG_FILE))
	$(CTAGS) -o $(TAG_FILE) $(SOURCE)

#Makefile Debugging
#Target to print any variable, can be added to the dependencies of any other target
#Userfule flags for make, -d, -p, -n
print-%: ; @$(error $* is $($*) ($(value $*)) (from $(origin $*)))
