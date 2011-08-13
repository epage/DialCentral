PROJECT_NAME=dialcentral
PACKAGE_NAME=$(PROJECT_NAME)

SOURCE_PATH=$(PACKAGE_NAME)
SOURCE=$(shell find $(SOURCE_PATH) -iname "*.py")

PROGRAM=DialCentral
ICON_SIZES=26 32 48 64 80
ICONS=$(foreach size, $(ICON_SIZES), data/icons/$(size)/$(PROJECT_NAME).png)
PACKAGE_VARIANTS=fremantle harmattan ubuntu
DESKTOP_FILES=$(foreach variant, $(PACKAGE_VARIANTS), data/$(variant)/$(PROJECT_NAME).desktop)
SETUP_FILES=$(foreach variant, $(PACKAGE_VARIANTS), ./setup.$(variant).py)
DIST_BASE_PATH=./dist
DIST_PATHS=$(foreach variant, $(PACKAGE_VARIANTS), $(DIST_BASE_PATH)_$(variant)) $(DIST_BASE_PATH)_diablo

OBJ=$(SOURCE:.py=.pyc)
TAG_FILE=~/.ctags/$(PROJECT_NAME).tags
TODO_FILE=./TODO

DEBUGGER=winpdb
UNIT_TEST=nosetests --with-doctest -w .
SYNTAX_TEST=support/test_syntax.py
STYLE_TEST=../../Python/tools/pep8.py --ignore=W191,E501
LINT_RC=./support/pylint.rc
LINT=pylint --rcfile=$(LINT_RC)
PROFILE_GEN=python -m cProfile -o .profile
PROFILE_VIEW=python -m pstats .profile
TODO_FINDER=support/todo.py
CTAGS=ctags-exuberant


.PHONY: all run profile debug test build lint tags todo clean distclean

all: test

run: $(OBJ)
	$(PROGRAM)

profile: $(OBJ)
	$(PROFILE_GEN) $(PROGRAM)
	$(PROFILE_VIEW)

debug: $(OBJ)
	$(DEBUGGER) $(PROGRAM)

test: $(OBJ)
	$(UNIT_TEST)

_package_prep: $(OBJ) $(ICONS) $(SETUP_FILES) $(DESKTOP_FILES)

package_diablo: _package_prep
	rm -Rf $(DIST_BASE_PATH)_diablo/*
	./setup.fremantle.py sdist_diablo \
		-d $(DIST_BASE_PATH)_diablo \
		--install-purelib=/usr/lib/python2.5/site-packages
package_fremantle: _package_prep
	rm -Rf $(DIST_BASE_PATH)_fremantle/*
	./setup.fremantle.py sdist_fremantle \
		-d $(DIST_BASE_PATH)_fremantle \
		--install-purelib=/usr/lib/python2.5/site-packages
package_harmattan: _package_prep
	rm -Rf $(DIST_BASE_PATH)_harmattan/*
	./setup.harmattan.py sdist_harmattan \
		-d $(DIST_BASE_PATH)_harmattan \
		--install-purelib=/usr/lib/python2.6/dist-packages
package_ubuntu: _package_prep
	rm -Rf $(DIST_BASE_PATH)_ubuntu/*
	./setup.ubuntu.py sdist_ubuntu \
		-d $(DIST_BASE_PATH)_ubuntu
	mkdir $(DIST_BASE_PATH)_ubuntu/build
	cd $(DIST_BASE_PATH)_ubuntu/build ; tar -zxvf ../*.tar.gz
	cd $(DIST_BASE_PATH)_ubuntu/build ; dpkg-buildpackage -tc -rfakeroot -us -uc

package: package_diablo package_fremantle package_harmattan package_ubuntu

upload_diablo:
	dput diablo-extras-builder $(DIST_BASE_PATH)_diablo/$(PROJECT_NAME)*.changes
upload_fremantle:
	dput fremantle-extras-builder $(DIST_BASE_PATH)_fremantle/$(PROJECT_NAME)*.changes
upload_harmattan:
	./support/obs_upload.sh $(PROJECT_NAME) harmattan dist_harmattan
upload_ubuntu:
	cp $(DIST_BASE_PATH)_ubuntu/*.deb www/$(PROJECT_NAME).deb

upload: upload_diablo upload_fremantle upload_harmattan upload_ubuntu

lint: $(OBJ)
	$(foreach file, $(SOURCE), $(LINT) $(file) ; )

tags: $(TAG_FILE) 

todo: $(TODO_FILE)

clean:
	rm -Rf $(OBJ)
	rm -Rf $(TODO_FILE)
	rm -f $(ICONS) $(SETUP_FILES) $(DESKTOP_FILES)
	rm -Rf $(DIST_PATHS) ./build

distclean: clean
	find $(SOURCE_PATH) -name "*.*~" | xargs rm -f
	find $(SOURCE_PATH) -name "*.swp" | xargs rm -f
	find $(SOURCE_PATH) -name "*.bak" | xargs rm -f
	find $(SOURCE_PATH) -name ".*.swp" | xargs rm -f


$(SETUP_FILES): VARIANT=$(word 2, $(subst ., ,$@))

setup.fremantle.py: setup.py src/constants.py
	cog.py -c \
		-D DESKTOP_FILE_PATH=/usr/share/applications/hildon \
		-D INPUT_DESKTOP_FILE=data/$(VARIANT)/$(PROJECT_NAME).desktop \
		-D ICON_CATEGORY=hildon \
		-D ICON_SIZES=26,32,48 \
		-o $@ $<
	chmod +x $@

setup.harmattan.py: setup.py src/constants.py
	cog.py -c \
		-D DESKTOP_FILE_PATH=/usr/share/applications \
		-D INPUT_DESKTOP_FILE=data/$(VARIANT)/$(PROJECT_NAME).desktop \
		-D ICON_CATEGORY=apps \
		-D ICON_SIZES=64,80 \
		-o $@ $<
	chmod +x $@

setup.ubuntu.py: setup.py src/constants.py
	cog.py -c \
		-D DESKTOP_FILE_PATH=/usr/share/applications \
		-D INPUT_DESKTOP_FILE=data/$(VARIANT)/$(PROJECT_NAME).desktop \
		-D ICON_CATEGORY=apps \
		-D ICON_SIZES=32,48 \
		-o $@ $<
	chmod +x $@

$(ICONS): SIZE=$(word 3, $(subst /, ,$@))
$(ICONS): data/$(PROJECT_NAME).png support/scale.py
	mkdir -p $(dir $@)
	support/scale.py --input $< --output $@ --size $(SIZE)

$(DESKTOP_FILES): VARIANT=$(word 2, $(subst /, ,$@))
$(DESKTOP_FILES): data/template.desktop
	mkdir -p $(dir $@)
	cog.py -d \
		-D VARIANT=$(VARIANT) \
		-D PROGRAM=$(PROGRAM) \
		-D ICON_NAME=$(PROJECT_NAME) \
		-o $@ $<


$(TAG_FILE): $(OBJ)
	mkdir -p $(dir $(TAG_FILE))
	$(CTAGS) -o $(TAG_FILE) $(SOURCE)

$(TODO_FILE): $(SOURCE)
	@- $(TODO_FINDER) $(SOURCE) > $(TODO_FILE)

%.pyc: %.py
	$(SYNTAX_TEST) $<

#Makefile Debugging
#Target to print any variable, can be added to the dependencies of any other target
#Userfule flags for make, -d, -p, -n
print-%: ; @$(error $* is $($*) ($(value $*)) (from $(origin $*)))
