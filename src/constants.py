import os

__pretty_app_name__ = "DialCentral"
__app_name__ = "dialcentral"
__version__ = "1.2.8"
__build__ = 0
__app_magic__ = 0xdeadbeef
_data_path_ = os.path.join(os.path.expanduser("~"), ".%s" % __app_name__)
_user_settings_ = "%s/settings.ini" % _data_path_
_custom_notifier_settings_ = "%s/notifier.ini" % _data_path_
_user_logpath_ = "%s/%s.log" % (_data_path_, __app_name__)
_notifier_logpath_ = "%s/notifier.log" % _data_path_
IS_MAEMO = True
