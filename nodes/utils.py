import importlib
import pytz.exceptions

from varstorage import models as var_models


def import_dot_path(path):
    path_splitted = path.split('.')
    module_name = '.'.join(path_splitted[:-1])
    var_name = path_splitted[-1]
    module = importlib.import_module(module_name)
    return getattr(module, var_name)


def get_configured_timezone():
    timezone_name = var_models.Variable.objects.get_value('timezone')
    try:
        return pytz.timezone(timezone_name)
    except pytz.exceptions.UnknownTimeZoneError:
        return pytz.UTC
