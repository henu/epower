import importlib


def import_dot_path(path):
    path_splitted = path.split('.')
    module_name = '.'.join(path_splitted[:-1])
    var_name = path_splitted[-1]
    module = importlib.import_module(module_name)
    return getattr(module, var_name)
