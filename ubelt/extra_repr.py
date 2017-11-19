

def array_repr2(arr, max_line_width=None, precision=None, suppress_small=None,
                force_dtype=False, with_dtype=None, **kwargs):
    """ extended version of np.core.numeric.array_repr

    ut.editfile(np.core.numeric.__file__)

    On linux:
    _typelessdata [numpy.int64, numpy.float64, numpy.complex128, numpy.int64]

    On BakerStreet
    _typelessdata [numpy.int32, numpy.float64, numpy.complex128, numpy.int32]

    # WEIRD
    np.int64 is np.int64
    _typelessdata[0] is _typelessdata[-1]
    _typelessdata[0] == _typelessdata[-1]

    TODO:
        replace force_dtype with with_dtype


    id(_typelessdata[-1])
    id(_typelessdata[0])


    from numpy.core.numeric import _typelessdata
    _typelessdata

    References:
        http://stackoverflow.com/questions/28455982/why-are-there-two-np-int64s
        -in-numpy-core-numeric-typelessdata-why-is-numpy-in/28461928#28461928
    """
    import numpy as np
    from numpy.core.numeric import _typelessdata

    if arr.__class__ is not np.ndarray:
        cName = arr.__class__.__name__
    else:
        cName = 'array'

    prefix = cName + '('

    if arr.size > 0 or arr.shape == (0,):
        separator = ', '
        lst = array2string2(
            arr, max_line_width, precision, suppress_small, separator, prefix,
            **kwargs)
    else:
        # show zero-length shape unless it is (0,)
        lst = '[], shape=%s' % (repr(arr.shape),)

    skipdtype = ((arr.dtype.type in _typelessdata) and arr.size > 0)

    if with_dtype is None:
        with_dtype = not (skipdtype and not (cName == 'array' and force_dtype))

    if not with_dtype:
        return '%s(%s)' % (cName, lst)
    else:
        typename = arr.dtype.name
        # Quote typename in the output if it is 'complex'.
        if typename and not (typename[0].isalpha() and typename.isalnum()):
            typename = '\'%s\'' % typename

        lf = ''
        if issubclass(arr.dtype.type, np.flexible):
            if arr.dtype.names:
                typename = '%s' % six.text_type(arr.dtype)
            else:
                typename = '\'%s\'' % six.text_type(arr.dtype)
            lf = '\n' + ' ' * len(prefix)
        return cName + '(%s, %sdtype=%s)' % (lst, lf, typename)


def array2string2(a, max_line_width=None, precision=None, suppress_small=None,
                  separator=' ', prefix="", style=repr, formatter=None,
                  threshold=None):
    """
    expanded version of np.core.arrayprint.array2string
    """
    import numpy as np

    if a.shape == ():
        x = a.item()
        try:
            import warnings
            lst = a._format(x)
            msg = "The `_format` attribute is deprecated in Numpy " \
                  "2.0 and will be removed in 2.1. Use the " \
                  "`formatter` kw instead."
            warnings.warn(msg, DeprecationWarning)
        except AttributeError:
            if isinstance(x, tuple):
                x = np.core.arrayprint._convert_arrays(x)
            lst = style(x)
    elif reduce(np.core.arrayprint.product, a.shape) == 0:
        # treat as a null array if any of shape elements == 0
        lst = "[]"
    else:
        lst = _array2string2(
            a, max_line_width, precision, suppress_small, separator, prefix,
            formatter=formatter, threshold=threshold)
    return lst


def _array2string2(a, max_line_width, precision, suppress_small, separator=' ',
                   prefix="", formatter=None, threshold=None):
    """
    expanded version of np.core.arrayprint._array2string
    TODO: make a numpy pull request with a fixed version

    """
    arrayprint = np.core.arrayprint

    if max_line_width is None:
        max_line_width = arrayprint._line_width

    if precision is None:
        precision = arrayprint._float_output_precision

    if suppress_small is None:
        suppress_small = arrayprint._float_output_suppress_small

    if formatter is None:
        formatter = arrayprint._formatter

    if threshold is None:
        threshold = arrayprint._summaryThreshold

    if threshold > 0 and a.size > threshold:
        summary_insert = "..., "
        data = arrayprint._leading_trailing(a)
    else:
        summary_insert = ""
        data = arrayprint.ravel(a)

    formatdict = {'bool' : arrayprint._boolFormatter,
                  'int' : arrayprint.IntegerFormat(data),
                  'float' : arrayprint.FloatFormat(data, precision, suppress_small),
                  'longfloat' : arrayprint.LongFloatFormat(precision),
                  'complexfloat' : arrayprint.ComplexFormat(data, precision,
                                                            suppress_small),
                  'longcomplexfloat' : arrayprint.LongComplexFormat(precision),
                  'datetime' : arrayprint.DatetimeFormat(data),
                  'timedelta' : arrayprint.TimedeltaFormat(data),
                  'numpystr' : arrayprint.repr_format,
                  'str' : str}

    if formatter is not None:
        fkeys = [k for k in formatter.keys() if formatter[k] is not None]
        if 'all' in fkeys:
            for key in formatdict.keys():
                formatdict[key] = formatter['all']
        if 'int_kind' in fkeys:
            for key in ['int']:
                formatdict[key] = formatter['int_kind']
        if 'float_kind' in fkeys:
            for key in ['float', 'longfloat']:
                formatdict[key] = formatter['float_kind']
        if 'complex_kind' in fkeys:
            for key in ['complexfloat', 'longcomplexfloat']:
                formatdict[key] = formatter['complex_kind']
        if 'str_kind' in fkeys:
            for key in ['numpystr', 'str']:
                formatdict[key] = formatter['str_kind']
        for key in formatdict.keys():
            if key in fkeys:
                formatdict[key] = formatter[key]

    try:
        format_function = a._format
        msg = "The `_format` attribute is deprecated in Numpy 2.0 and " \
              "will be removed in 2.1. Use the `formatter` kw instead."
        import warnings
        warnings.warn(msg, DeprecationWarning)
    except AttributeError:
        # find the right formatting function for the array
        dtypeobj = a.dtype.type
        if issubclass(dtypeobj, np.core.arrayprint._nt.bool_):
            format_function = formatdict['bool']
        elif issubclass(dtypeobj, np.core.arrayprint._nt.integer):
            if issubclass(dtypeobj, np.core.arrayprint._nt.timedelta64):
                format_function = formatdict['timedelta']
            else:
                format_function = formatdict['int']
        elif issubclass(dtypeobj, np.core.arrayprint._nt.floating):
            if issubclass(dtypeobj, np.core.arrayprint._nt.longfloat):
                format_function = formatdict['longfloat']
            else:
                format_function = formatdict['float']
        elif issubclass(dtypeobj, np.core.arrayprint._nt.complexfloating):
            if issubclass(dtypeobj, np.core.arrayprint._nt.clongfloat):
                format_function = formatdict['longcomplexfloat']
            else:
                format_function = formatdict['complexfloat']
        elif issubclass(dtypeobj, (np.core.arrayprint._nt.unicode_,
                                   np.core.arrayprint._nt.string_)):
            format_function = formatdict['numpystr']
        elif issubclass(dtypeobj, np.core.arrayprint._nt.datetime64):
            format_function = formatdict['datetime']
        else:
            format_function = formatdict['numpystr']

    # skip over "["
    next_line_prefix = " "
    # skip over array(
    next_line_prefix += " " * len(prefix)

    lst = np.core.arrayprint._formatArray(a, format_function, len(a.shape), max_line_width,
                                          next_line_prefix, separator,
                                          np.core.arrayprint._summaryEdgeItems, summary_insert)[:-1]
    return lst


def numpy_str(arr, strvals=False, precision=None, pr=None,
              force_dtype=False,
              with_dtype=None, suppress_small=None, max_line_width=None,
              threshold=None, **kwargs):
    """
    suppress_small = False turns off scientific representation
    """
    kwargs = kwargs.copy()
    if 'suppress' in kwargs:
        suppress_small = kwargs['suppress']
    if max_line_width is None and 'linewidth' in kwargs:
        max_line_width = kwargs.pop('linewidth')

    if pr is not None:
        precision = pr
    # TODO: make this a util_str func for numpy reprs
    if strvals:
        valstr = np.array_str(arr, precision=precision,
                              suppress_small=suppress_small, **kwargs)
    else:
        #valstr = np.array_repr(arr, precision=precision)
        valstr = array_repr2(arr, precision=precision, force_dtype=force_dtype,
                             with_dtype=with_dtype,
                             suppress_small=suppress_small,
                             max_line_width=max_line_width,
                             threshold=threshold, **kwargs)
        numpy_vals = itertools.chain(util_type.NUMPY_SCALAR_NAMES, ['array'])
        for npval in numpy_vals:
            valstr = valstr.replace(npval, 'np.' + npval)
        if valstr.find('\n') >= 0:
            # Align multiline arrays
            valstr = valstr.replace('\n', '\n   ')
    return valstr


