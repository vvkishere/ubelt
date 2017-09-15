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
        python -m ubelt.util_type --exec-as_smart_type

    Example:
        >>> from ubelt.util_smartcast import *  # NOQA
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
            # TODO:
            #    use parse_nestings to smartcast lists/tuples/sets
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


def parse_nestings(string, nesters=['()', '[]', '{}', '<>', "''", '""'], escape='\\'):
    r"""
    Recursively partitions strings into nested or quoted expressions.

    By default four types of nesters (paren, brak, curly, and angle) are
    recognied along with double and single quotes. Different nesters can be
    specified for custom uses.

    SeeAlso:
        recombine_nestings - takes the result of this function

    Returns:
        list: an abstract syntax tree represented as a list of lists

    References:
        http://stackoverflow.com/questions/4801403/pyparsing-nested-mutiple-opener-clo

    Example:
        >>> from ubelt.util_smartcast import *  # NOQA
        >>> import ubelt as ub
        >>> string = r'lambda u: sign("\"u(\'fdfds\')") * abs(u)**3.0 * greater(u, 0)'
        >>> parse_tree = parse_nestings(string)
        >>> print('parse_tree = {}'.format(ub.repr2(parse_tree, nl=3, si=True)))
        >>> assert recombine_nestings(parse_tree) == string
    """
    import pyparsing as pp

    def as_tagged_tree(parent, doctag=None):
        """Returns the parse results as XML. Tags are created for tokens and lists that have defined results names."""
        namedItems = dict(
            (v[1], k)
            for (k, vlist) in parent._ParseResults__tokdict.items()
            for v in vlist
        )
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
                    child = as_tagged_tree(res, namedItems[i])
                else:
                    child = as_tagged_tree(res, None)
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
        # return out
        return (parentTag, out)

    def combine_nested(opener, closer, content, name=None):
        r"""
        opener, closer, content = '(', ')', nest_body
        """
        ret1 = pp.Forward()
        group = pp.Group(opener + pp.ZeroOrMore(content) + closer)
        ret2 = ret1 << group
        ret3 = ret2
        if name is not None:
            ret3 = ret2.setResultsName(name)
        return ret3

    def regex_or(*patterns):
        """ matches one of the patterns """
        return '{}'.format('|'.join(patterns))

    def nocapture(pat):
        """ A non-capturing version of regular parentheses """
        return '(?:{})'.format(pat)

    # Current Best Grammar
    nest_body = pp.Forward()
    nest_expr_list = []
    for left, right in nesters:
        if left == right:
            # Treat left==right nestings as quoted strings
            q = left
            quote_pat_fmt = (nocapture(regex_or(
                r'[^{quote}\n\r\\]',
                nocapture('{quote}{quote}'),
                nocapture(r'\\' + nocapture(regex_or(
                    '[^x]',
                    'x[0-9a-fA-F]+')
                ))
            )) + '*')
            quote_pat_fmt = r'(?:[^{quote}\n\r\\]|(?:{quote}{quote})|(?:\\(?:[^x]|x[0-9a-fA-F]+)))*'
            quote_pat = quote_pat_fmt.format(quote=q)
            quotedString = pp.Group(q + pp.Regex(quote_pat) + q)
            nest_expr = quotedString.setResultsName('nest' + left + right)
        else:
            nest_expr = combine_nested(left, right, content=nest_body, name='nest' + left + right)
        nest_expr_list.append(nest_expr)

    # quotedString = Combine(Regex(r'"(?:[^"\n\r\\]|(?:"")|(?:\\(?:[^x]|x[0-9a-fA-F]+)))*')+'"'|
    #                        Regex(r"'(?:[^'\n\r\\]|(?:'')|(?:\\(?:[^x]|x[0-9a-fA-F]+)))*")+"'").setName("quotedString using single or double quotes")

    nonBracePrintables = ''.join(c for c in pp.printables if c not in ''.join(nesters)) + ' '
    nonNested = pp.Word(nonBracePrintables).setResultsName('nonNested')
    nonNested = nonNested.leaveWhitespace()

    # The body might be a non-nested set of characters
    nest_body_input = nonNested
    # Allow each type of nested expression to be present in the body
    for nest_expr in nest_expr_list:
        nest_body_input = nest_body_input | nest_expr

    nest_body << nest_body_input

    nest_body = nest_body.leaveWhitespace()
    parser = pp.ZeroOrMore(nest_body)

    if len(string) > 0:
        tokens = parser.parseString(string)
        # parse_tree = tokens.asList()
        parse_tree = as_tagged_tree(tokens)
    else:
        # parse_tree = []
        parse_tree = ('nonNested', [])
    return parse_tree


def recombine_nestings(parse_tree):
    values = parse_tree[1]
    if isinstance(values, list):
        literals = map(recombine_nestings, values)
        recombined = ''.join(literals)
    else:
        recombined = values
    return recombined
