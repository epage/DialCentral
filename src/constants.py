import os

__pretty_app_name__ = "DialCentral"
__app_name__ = "dialcentral"
__version__ = "1.1.5"
__build__ = 0
__app_magic__ = 0xdeadbeef
_data_path_ = os.path.join(os.path.expanduser("~"), ".dialcentral")
_user_settings_ = "%s/settings.ini" % _data_path_
_custom_notifier_settings_ = "%s/notifier.ini" % _data_path_
_user_logpath_ = "%s/dialcentral.log" % _data_path_
_notifier_logpath_ = "%s/notifier.log" % _data_path_
