import logging


_moduleLogger = logging.getLogger("merge_backend")


class MergedAddressBook(object):
	"""
	Merger of all addressbooks
	"""

	def __init__(self, addressbookFactories, sorter = None):
		self.__addressbookFactories = addressbookFactories
		self.__addressbooks = None
		self.__sort_contacts = sorter if sorter is not None else self.null_sorter

	def clear_caches(self):
		self.__addressbooks = None
		for factory in self.__addressbookFactories:
			factory.clear_caches()

	def get_addressbooks(self):
		"""
		@returns Iterable of (Address Book Factory, Book Id, Book Name)
		"""
		yield self, "", ""

	def open_addressbook(self, bookId):
		return self

	def contact_source_short_name(self, contactId):
		if self.__addressbooks is None:
			return ""
		bookIndex, originalId = contactId.split("-", 1)
		return self.__addressbooks[int(bookIndex)].contact_source_short_name(originalId)

	@staticmethod
	def factory_name():
		return "All Contacts"

	def get_contacts(self):
		"""
		@returns Iterable of (contact id, contact name)
		"""
		if self.__addressbooks is None:
			self.__addressbooks = list(
				factory.open_addressbook(id)
				for factory in self.__addressbookFactories
				for (f, id, name) in factory.get_addressbooks()
			)
		contacts = (
			("-".join([str(bookIndex), contactId]), contactName)
				for (bookIndex, addressbook) in enumerate(self.__addressbooks)
					for (contactId, contactName) in addressbook.get_contacts()
		)
		sortedContacts = self.__sort_contacts(contacts)
		return sortedContacts

	def get_contact_details(self, contactId):
		"""
		@returns Iterable of (Phone Type, Phone Number)
		"""
		if self.__addressbooks is None:
			return []
		bookIndex, originalId = contactId.split("-", 1)
		return self.__addressbooks[int(bookIndex)].get_contact_details(originalId)

	@staticmethod
	def null_sorter(contacts):
		"""
		Good for speed/low memory
		"""
		return contacts

	@staticmethod
	def basic_firtname_sorter(contacts):
		"""
		Expects names in "First Last" format
		"""
		contactsWithKey = [
			(contactName.rsplit(" ", 1)[0], (contactId, contactName))
				for (contactId, contactName) in contacts
		]
		contactsWithKey.sort()
		return (contactData for (lastName, contactData) in contactsWithKey)

	@staticmethod
	def basic_lastname_sorter(contacts):
		"""
		Expects names in "First Last" format
		"""
		contactsWithKey = [
			(contactName.rsplit(" ", 1)[-1], (contactId, contactName))
				for (contactId, contactName) in contacts
		]
		contactsWithKey.sort()
		return (contactData for (lastName, contactData) in contactsWithKey)

	@staticmethod
	def reversed_firtname_sorter(contacts):
		"""
		Expects names in "Last, First" format
		"""
		contactsWithKey = [
			(contactName.split(", ", 1)[-1], (contactId, contactName))
				for (contactId, contactName) in contacts
		]
		contactsWithKey.sort()
		return (contactData for (lastName, contactData) in contactsWithKey)

	@staticmethod
	def reversed_lastname_sorter(contacts):
		"""
		Expects names in "Last, First" format
		"""
		contactsWithKey = [
			(contactName.split(", ", 1)[0], (contactId, contactName))
				for (contactId, contactName) in contacts
		]
		contactsWithKey.sort()
		return (contactData for (lastName, contactData) in contactsWithKey)

	@staticmethod
	def guess_firstname(name):
		if ", " in name:
			return name.split(", ", 1)[-1]
		else:
			return name.rsplit(" ", 1)[0]

	@staticmethod
	def guess_lastname(name):
		if ", " in name:
			return name.split(", ", 1)[0]
		else:
			return name.rsplit(" ", 1)[-1]

	@classmethod
	def advanced_firstname_sorter(cls, contacts):
		contactsWithKey = [
			(cls.guess_firstname(contactName), (contactId, contactName))
				for (contactId, contactName) in contacts
		]
		contactsWithKey.sort()
		return (contactData for (lastName, contactData) in contactsWithKey)

	@classmethod
	def advanced_lastname_sorter(cls, contacts):
		contactsWithKey = [
			(cls.guess_lastname(contactName), (contactId, contactName))
				for (contactId, contactName) in contacts
		]
		contactsWithKey.sort()
		return (contactData for (lastName, contactData) in contactsWithKey)
