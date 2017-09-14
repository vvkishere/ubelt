"""
Goal is to handle:
    simple scalar types (int, float, complex, str)
    simple container types (list, tuples, sets) (requires pyparsing)

# TODO: parse nesting for a list
"""
import six
import types

if six.PY2:
    BooleanType = types.BooleanType
else:
    BooleanType = bool

NoneType = type(None)


def smartcast(var, strict=False):
    r"""
    An alternative to `eval` that checks if a string can easily cast to a
    standard python data type.

    This is an alternative to eval
    if the variable is a string tries to cast it to a reasonable value.
    maybe can just use eval.

    Args:
        var (unknown):

    Returns:
        unknown: some var

    CommandLine:
        python -m ubelt.util_smartcast --test-smartcast

    Example:
        >>> from ubelt.util_smartcast import *  # NOQA
        >>> assert smartcast('?') == '?'
        >>> assert smartcast('1') == 1
        >>> assert smartcast('1.0') == 1.0
        >>> assert smartcast('1.2') == 1.2
        >>> assert smartcast('True') == True
        >>> assert smartcast('None') is None
        >>> # Non-string types should just be returned as themselves
        >>> assert smartcast(1) == 1
        >>> assert smartcast(None) is None
    """
    if var is None:
        return None
    if isinstance(var, six.string_types):
        lower = var.lower()
        if lower == 'true':
            return True
        elif lower == 'false':
            return False
        elif lower == 'none':
            return None
        type_list = [int, float, complex]
        for data_type in type_list:
            try:
                return as_smart_type(var, data_type)
            except (TypeError, ValueError):
                pass
        if strict:
            raise TypeError('Could not smartcast var={!r}'.format(var))
        else:
            # We couldn't do anything, so just return the string
            return var
    else:
        return var


def as_smart_type(var, data_type):
    """
    casts var to type, and tries to be clever when var is a string, otherwise
    it simply calls `data_type(var)`.

    Args:
        var (object): variable (typically a string) to cast
        data_type (type or str): type to attempt to cast to

    Returns:
        object:

    CommandLine:
        python -m utool.util_type --exec-as_smart_type

    Example:
        >>> from utool.util_type import *  # NOQA
        >>> assert as_smart_type('1', None) == '1'
        >>> assert as_smart_type('1', int) == 1
        >>> assert as_smart_type('(1,3)', 'eval') == (1, 3)
        >>> assert as_smart_type('(1,3)', eval) == (1, 3)
        >>> assert as_smart_type('1::3', slice) == slice(1, None, 3)
    """
    if data_type is None or var is None:
        return var
    elif isinstance(data_type, six.string_types):
        # handle special ``types''
        if data_type == 'eval':
            return eval(var, {}, {})
        else:
            raise NotImplementedError('Unknown smart data_type=%r' % (data_type,))
    else:
        try:
            if issubclass(data_type, NoneType):
                return var
        except TypeError:
            pass
        if isinstance(var, six.string_types):
            if data_type is bool:
                return _smartcast_bool(var)
            elif data_type is slice:
                return _smartcast_slice(var)
            if data_type in [int, float, complex, eval]:
                return data_type(var)
            else:
                raise NotImplementedError(
                    'Cannot smart parse type={}'.format(data_type))
        else:
            return data_type(var)


def _smartcast_slice(var):
    args = [int(p) if p else None for p in var.split(':')]
    return slice(*args)


def _smartcast_bool(var):
    """
    Casts a string to a boolean.
    """
    lower = var.lower()
    if lower == 'true':
        return True
    elif lower == 'false':
        return False
    else:
        raise TypeError('string does not represent boolean')


def parse_nestings2(string, nesters=['()', '[]', '<>', "''", '""'], escape='\\'):
    r"""
    References:
        http://stackoverflow.com/questions/4801403/pyparsing-nested-mutiple-opener-clo

    Example:
        >>> from utool.util_gridsearch import *  # NOQA
        >>> import utool as ut
        >>> string = r'lambda u: sign(u) * abs(u)**3.0 * greater(u, 0)'
        >>> parsed_blocks = parse_nestings2(string)
        >>> print('parsed_blocks = {!r}'.format(parsed_blocks))
        >>> string = r'lambda u: sign("\"u(\'fdfds\')") * abs(u)**3.0 * greater(u, 0)'
        >>> parsed_blocks = parse_nestings2(string)
        >>> print('parsed_blocks = {!r}'.format(parsed_blocks))
        >>> recombined = recombine_nestings(parsed_blocks)
        >>> print('PARSED_BLOCKS = ' + ut.repr3(parsed_blocks, nl=1))
        >>> print('recombined = %r' % (recombined,))
        >>> print('orig       = %r' % (string,))
    """
    import pyparsing as pp

    def as_tagged(parent, doctag=None):
        """Returns the parse results as XML. Tags are created for tokens and lists that have defined results names."""
        namedItems = dict((v[1], k) for (k, vlist) in parent._ParseResults__tokdict.items()
                          for v in vlist)
        # collapse out indents if formatting is not desired
        parentTag = None
        if doctag is not None:
            parentTag = doctag
        else:
            if parent._ParseResults__name:
                parentTag = parent._ParseResults__name
        if not parentTag:
            parentTag = "ITEM"
        out = []
        for i, res in enumerate(parent._ParseResults__toklist):
            if isinstance(res, pp.ParseResults):
                if i in namedItems:
                    child = as_tagged(res, namedItems[i])
                else:
                    child = as_tagged(res, None)
                out.append(child)
            else:
                # individual token, see if there is a name for it
                resTag = None
                if i in namedItems:
                    resTag = namedItems[i]
                if not resTag:
                    resTag = "ITEM"
                child = (resTag, pp._ustr(res))
                out += [child]
        return (parentTag, out)

    def combine_nested(opener, closer, content, name=None):
        r"""
        opener, closer, content = '(', ')', nest_body
        """
        ret1 = pp.Forward()
        # if opener == closer:
        #     closer = pp.Regex('(?<!' + re.escape(closer) + ')')
        # _NEST = ut.identity
        #_NEST = pp.Suppress
        # opener_ = _NEST(opener)
        # closer_ = _NEST(closer)
        opener_ = opener
        closer_ = closer

        group = pp.Group(opener_ + pp.ZeroOrMore(content) + closer_)
        ret2 = ret1 << group
        if ret2 is None:
            ret2 = ret1
        else:
            pass
            #raise AssertionError('Weird pyparsing behavior. Comment this line if encountered. pp.__version__ = %r' % (pp.__version__,))
        if name is None:
            ret3 = ret2
        else:
            ret3 = ret2.setResultsName(name)
        assert ret3 is not None, 'cannot have a None return'
        return ret3

    # Current Best Grammar
    nest_body = pp.Forward()
    nest_expr_list = []
    for left, right in nesters:
        if left == right:
            # Treat left==right nestings as quoted strings
            q = left
            quotedString = pp.Group(q + pp.Regex(r'(?:[^{q}\n\r\\]|(?:{q}{q})|(?:\\(?:[^x]|x[0-9a-fA-F]+)))*'.format(q=q)) + q)
            nest_expr = quotedString.setResultsName('nest' + left + right)
        else:
            nest_expr = combine_nested(left, right, content=nest_body, name='nest' + left + right)
        nest_expr_list.append(nest_expr)

    # quotedString = Combine(Regex(r'"(?:[^"\n\r\\]|(?:"")|(?:\\(?:[^x]|x[0-9a-fA-F]+)))*')+'"'|
    #                        Regex(r"'(?:[^'\n\r\\]|(?:'')|(?:\\(?:[^x]|x[0-9a-fA-F]+)))*")+"'").setName("quotedString using single or double quotes")

    nonBracePrintables = ''.join(c for c in pp.printables if c not in ''.join(nesters)) + ' '
    nonNested = pp.Word(nonBracePrintables).setResultsName('nonNested')
    # nonNested = (pp.Word(nonBracePrintables) | pp.quotedString).setResultsName('nonNested')
    nonNested = nonNested.leaveWhitespace()

    # if with_curl and not with_paren and not with_brak:
    nest_body_input = nonNested
    for nest_expr in nest_expr_list:
        nest_body_input = nest_body_input | nest_expr

    nest_body << nest_body_input

    nest_body = nest_body.leaveWhitespace()
    parser = pp.ZeroOrMore(nest_body)

    debug_ = 0

    if len(string) > 0:
        tokens = parser.parseString(string)
        import ubelt as ub
        if debug_:
            print('string = %r' % (string,))
            print('tokens List: ' + ub.repr2(tokens.asList(), nl=1))
            print('tokens XML: ' + tokens.asXML())
        parsed_blocks = as_tagged(tokens)[1]
        if debug_:
            print('PARSED_BLOCKS = ' + ub.repr3(parsed_blocks, nl=1))
    else:
        parsed_blocks = []
    return parsed_blocks


def recombine_nestings(parsed_blocks):
    if len(parsed_blocks) == 0:
        return ''
    values = [block[1] for block in parsed_blocks]
    literals = [recombine_nestings(v) if isinstance(v, list) else v for v in values]
    recombined = ''.join(literals)
    return recombined
