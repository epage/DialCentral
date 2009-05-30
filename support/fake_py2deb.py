import pprint


class Py2deb(object):

	def __init__(self, appName):
		self._appName = appName
		self.description = ""
		self.author = ""
		self.mail = ""
		self.license = ""
		self.depends = ""
		self.section = ""
		self.arch = ""
		self.ugency = ""
		self.distribution = ""
		self.repository = ""
		self.changelog = ""
		self.postinstall = ""
		self.icon = ""
		self._install = {}

	def generate(self, appVersion, appBuild, changelog, tar, dsc, changes, build, src):
		return """
Package: %s
version: %s-%s
Changes:
%s

Build Options:
	Tar: %s
	Dsc: %s
	Changes: %s
	Build: %s
	Src: %s
		""" % (
			self._appName, appVersion, appBuild, changelog, tar, dsc, changes, build, src
		)

	def __str__(self):
		parts = []
		parts.append("%s Package Settings:" % (self._appName, ))
		for settingName in dir(self):
			if settingName.startswith("_"):
				continue
			parts.append("\t%s: %s" % (settingName, getattr(self, settingName)))

		parts.append(pprint.pformat(self._install))

		return "\n".join(parts)

	def __getitem__(self, key):
		return self._install[key]

	def __setitem__(self, key, item):
		self._install[key] = item
