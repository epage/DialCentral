PROJECT_NAME=DialCentral
SOURCE_PATH=src
SOURCE=$(SOURCE_PATH)/dialcentral/gc_dialer.py $(SOURCE_PATH)/dialcentral/evo_backend.py $(SOURCE_PATH)/dialcentral/gc_backend.py $(SOURCE_PATH)/dialcentral/browser_emu.py
OBJ=$(SOURCE:.py=.pyc)
TAG_FILE=~/.ctags/$(PROJECT_NAME).tags

DEBUGGER=winpdb
UNIT_TEST=nosetests -w $(TEST_PATH)
STYLE_TEST=../../Python/tools/pep8.py --ignore=W191
LINT_RC=./support/pylint.rc
LINT=pylint --rcfile=$(LINT_RC)
COVERAGE_TEST=figleaf
PROFILER=pyprofiler
CTAGS=ctags-exuberant

.PHONY: all run debug test lint tags package clean

all: test package

run: $(SOURCE)
	cd $(SOURCE_PATH)/dialcentral ; ./gc_dialer.py

debug: $(SOURCE)
	cd $(SOURCE_PATH)/dialcentral ; $(DEBUGGER) ./gc_dialer.py

test: $(SOURCE)
	cd $(SOURCE_PATH)/dialcentral ; ./gc_dialer.py -t

package:
	./builddeb.py

lint:
	$(foreach file, $(SOURCE), $(LINT) $(file) ; )

tags: $(TAG_FILE) 

clean:
	rm -Rf $(OBJ)

$(TAG_FILE): $(SOURCE)
	mkdir -p $(dir $(TAG_FILE))
	$(CTAGS) -o $(TAG_FILE) $(SOURCE)

#Makefile Debugging
#Target to print any variable, can be added to the dependencies of any other target
#Userfule flags for make, -d, -p, -n
print-%: ; @$(error $* is $($*) ($(value $*)) (from $(origin $*)))
