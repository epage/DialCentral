import os

__pretty_app_name__ = "DialCentral"
__app_name__ = "dialcentral"
__version__ = "1.0.8"
__build__ = 2
__app_magic__ = 0xdeadbeef
_data_path_ = os.path.join(os.path.expanduser("~"), ".dialcentral")
_user_settings_ = "%s/settings.ini" % _data_path_
