"""
TODO: work me in
"""

import sys
import functools
import six
import types


def get_funcglobals(func):
    if six.PY2:
        return getattr(func, 'func_globals')
    else:
        return getattr(func, '__globals__')


def get_method_func(method):
    try:
        return method.im_func if six.PY2 else method.__func__
    except AttributeError:
        # check if this is a method-wrapper type
        if isinstance(method, type(all.__call__)):
            # in which case there is no underlying function
            return None
        raise


# TODO: use six.text_type
def get_funcname(func):
    """
    Weird behavior for classes
    I dont know why this returns type / None
    import lasagne
    lasagne.layers.InputLayer
    lasagne.layers.InputLayer.__module__
    lasagne.layers.InputLayer.__class__.__name__ == 'type'
    lasagne.layers.InputLayer.__class__ is type
    wtf
    """
    if six.PY2:
        try:
            return getattr(func, 'func_name')
        except AttributeError:
            builtin_function_name_dict = {
                len:    'len',
                zip:    'zip',
                range:  'range',
                map:    'map',
                type:   'type',
            }
            if func in builtin_function_name_dict:
                return builtin_function_name_dict[func]
            elif isinstance(func, functools.partial):
                return get_funcname(func.func)
            elif isinstance(func, six.class_types):
                return func.__name__
                #return str(func).replace('<class \'', '').replace('\'>', '')
            elif hasattr(func, '__class__'):
                return func.__class__.__name__
            else:
                print('Error inspecting func type')
                print(type(func))
                raise
    else:
        try:
            return getattr(func, '__name__')
        except AttributeError:
            if isinstance(func, functools.partial):
                return get_funcname(func.func)
            if isinstance(func, types.BuiltinFunctionType):
                # for cv2.imread
                #return str(cv2.imread).replace('>', '').replace('<built-in function', '')
                return str(func).replace('<built-in function', '<')
            else:
                raise


def reload_class(self, verbose=True, reload_module=True):
    """
    special class reloading function
    This function is often injected as rrr of classes
    """
    import utool as ut
    classname = self.__class__.__name__
    try:
        modname = self.__class__.__module__
        if verbose:
            print('[class] reloading ' + classname + ' from ' + modname)
        # --HACK--
        if hasattr(self, '_on_reload'):
            if verbose > 1:
                print('[class] calling _on_reload for ' + classname)
            self._on_reload()
        elif verbose > 1:
            print('[class] ' + classname + ' does not have an _on_reload function')

        # Do for all inheriting classes
        def find_base_clases(_class, find_base_clases=None):
            class_list = []
            for _baseclass in _class.__bases__:
                parents = find_base_clases(_baseclass, find_base_clases)
                class_list.extend(parents)
            if _class is not object:
                class_list.append(_class)
            return class_list

        head_class = self.__class__
        # Determine if parents need reloading
        class_list = find_base_clases(head_class, find_base_clases)
        # HACK
        # ignore = {HashComparable2}
        ignore = {}
        class_list = [_class for _class in class_list
                      if _class not in ignore]
        for _class in class_list:
            if verbose:
                print('[class] reloading parent ' + _class.__name__ +
                      ' from ' + _class.__module__)
            if _class.__module__ == '__main__':
                # Attempt to find the module that is the main module
                # This may be very hacky and potentially break
                main_module_ = sys.modules[_class.__module__]
                main_modname = ut.get_modname_from_modpath(main_module_.__file__)
                module_ = sys.modules[main_modname]
            else:
                module_ = sys.modules[_class.__module__]
            if hasattr(module_, 'rrr'):
                if reload_module:
                    module_.rrr(verbose=verbose)
            else:
                if reload_module:
                    import imp
                    if verbose:
                        print('[class] reloading ' + _class.__module__ + ' with imp')
                    try:
                        imp.reload(module_)
                    except (ImportError, AttributeError):
                        print('[class] fallback reloading ' + _class.__module__ +
                              ' with imp')
                        # one last thing to try. probably used ut.import_module_from_fpath
                        # when importing this module
                        imp.load_source(module_.__name__, module_.__file__)
            # Reset class attributes
            _newclass = getattr(module_, _class.__name__)
            reload_class_methods(self, _newclass, verbose=verbose)

        # --HACK--
        # TODO: handle injected definitions
        if hasattr(self, '_initialize_self'):
            if verbose > 1:
                print('[class] calling _initialize_self for ' + classname)
            self._initialize_self()
        elif verbose > 1:
            print('[class] ' + classname + ' does not have an _initialize_self function')
    except Exception as ex:
        ut.printex(ex, 'Error Reloading Class', keys=[
            'modname', 'module', 'class_', 'class_list', 'self', ])
        raise


def reload_class_methods(self, class_, verbose=True):
    """
    rebinds all class methods

    Args:
        self (object): class instance to reload
        class_ (type): type to reload as

    Example:
        >>> # DISABLE_DOCTEST
        >>> from utool.util_class import *  # NOQA
        >>> self = '?'
        >>> class_ = '?'
        >>> result = reload_class_methods(self, class_)
        >>> print(result)
    """
    if verbose:
        print('[util_class] Reloading self=%r as class_=%r' % (self, class_))
    self.__class__ = class_
    for key in dir(class_):
        # Get unbound reloaded method
        func = getattr(class_, key)
        if isinstance(func, types.MethodType):
            # inject it into the old instance
            inject_func_as_method(self, func, class_=class_,
                                  allow_override=True,
                                  verbose=verbose)


def inject_func_as_method(self, func, method_name=None, class_=None,
                          allow_override=False, allow_main=False,
                          verbose=True, override=None, force=False):
    """ Injects a function into an object as a method

    Wraps func as a bound method of self. Then injects func into self
    It is preferable to use make_class_method_decorator and inject_instance

    Args:
       self (object): class instance
       func : some function whos first arugment is a class instance
       method_name (str) : default=func.__name__, if specified renames the method
       class_ (type) : if func is an unbound method of this class


    References:
        http://stackoverflow.com/questions/1015307/python-bind-an-unbound-method
    """
    if override is not None:
        # TODO depcirate allow_override
        allow_override = override
    if method_name is None:
        method_name = get_funcname(func)
    if force:
        allow_override = True
        allow_main = True
    old_method = getattr(self, method_name, None)
    # Bind function to the class instance
    #new_method = types.MethodType(func, self, self.__class__)
    new_method = func.__get__(self, self.__class__)
    #new_method = profile(func.__get__(self, self.__class__))

    if old_method is not None:
        old_im_func = get_method_func(old_method)
        new_im_func = get_method_func(new_method)
        if not allow_main and old_im_func is not None and (
                get_funcglobals(old_im_func)['__name__'] != '__main__' and
                get_funcglobals(new_im_func)['__name__'] == '__main__'):
            if True:
                print('[util_class] skipping re-inject of %r from __main__' % method_name)
            return
        if old_method is new_method or old_im_func is new_im_func:
            #if verbose and util_arg.NOT_QUIET:
            #    print('WARNING: Skipping injecting the same function twice: %r' % new_method)
                #print('WARNING: Injecting the same function twice: %r' % new_method)
            return
        elif allow_override is False:
            raise AssertionError(
                'Overrides are not allowed. Already have method_name=%r' %
                (method_name))
        elif allow_override == 'warn':
            print(
                'WARNING: Overrides are not allowed. Already have method_name=%r. Skipping' %
                (method_name))
            return
        elif allow_override == 'override+warn':
            #import utool as ut
            #ut.embed()
            print('WARNING: Overrides are allowed, but dangerous. method_name=%r.' %
                  (method_name))
            print('old_method = %r, im_func=%s' % (old_method, str(old_im_func)))
            print('new_method = %r, im_func=%s' % (new_method, str(new_im_func)))
            print(get_funcglobals(old_im_func)['__name__'])
            print(get_funcglobals(new_im_func)['__name__'])
        # TODO: does this actually decrement the refcount enough?
        del old_method
    setattr(self, method_name, new_method)


def inject_func_as_property(self, func, method_name=None, class_=None):
    """
    WARNING:
        properties are more safely injected using metaclasses

    References:
        http://stackoverflow.com/questions/13850114/dynamically-adding-methods-with-or-without-metaclass-in-python
    """
    if method_name is None:
        method_name = get_funcname(func)
    #new_method = func.__get__(self, self.__class__)
    new_property = property(func)
    setattr(self.__class__, method_name, new_property)
