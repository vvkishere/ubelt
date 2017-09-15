import six
import hashlib
import uuid


_ALPHABET_27 = [
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o',
    'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']

_HASH_LEN2 = 32

if six.PY3:
    _stringlike = (str, bytes)  # NOQA
else:
    _stringlike = (basestring, bytes)  # NOQA

if six.PY3:
    def _int_to_bytes(int_):
        length = max(4, int_.bit_length())
        bytes_ = int_.to_bytes(length, byteorder='big')
        # bytes_ = int_.to_bytes(4, byteorder='big')
        # int_.to_bytes(8, byteorder='big')  # TODO: uncomment
        return bytes_

    def _bytes_to_int(bytes_):
        int_ = int.from_bytes(bytes_, 'big')
        return int_
else:
    def _py2_to_bytes(int_, length, byteorder='big'):
        h = '%x' % int_
        s = ('0' * (len(h) % 2) + h).zfill(length * 2).decode('hex')
        bytes_ =  s if byteorder == 'big' else s[::-1]
        return bytes_

    import codecs
    def _int_to_bytes(int_):
        length = max(4, int_.bit_length())
        bytes_ = _py2_to_bytes(int_, length, 'big')
        # bytes_ = struct.pack('>i', int_)
        return bytes_

    def _bytes_to_int(bytes_):
        int_ = int(codecs.encode(bytes_, 'hex'), 16)
        # int_ = struct.unpack('>i', bytes_)[0]
        # int_ = struct.unpack_from('>L', bytes_)[0]
        return int_


def hash_data(data, hashlen=None, alphabet=None):
    r"""
    Get a unique hash depending on the state of the data.

    Args:
        data (object): any sort of loosely organized data
        hashlen (None): (default = None)
        alphabet (None): (default = None)

    Returns:
        str: text -  hash string

    CommandLine:
        python -m ubelt.util_hash hash_data

    Example:
        >>> from ubelt.util_hash import *  # NOQA
        >>> counter = [0]
        >>> failed = []
        >>> def check_hash(input_, want=None):
        ...     count = counter[0] = counter[0] + 1
        ...     got = hash_data(input_)
        ...     #print('({}) {}'.format(count, got))
        ...     if want is not None and not got.startswith(want):
        ...         failed.append((got, input_, count, want))
        >>> check_hash('1', 'wuvrng')
        >>> check_hash(['1'], 'dekbfpby')
        >>> check_hash(tuple(['1']), 'dekbfpby')
        >>> check_hash(b'12', 'marreflbv')
        >>> check_hash([b'1', b'2'], 'nwfs')
        >>> check_hash(['1', '2', '3'], 'arfrp')
        >>> #check_hash(['1', np.array([1,2,3]), '3'], 'uyqwcq')
        >>> check_hash('123', 'ehkgxk')
        >>> check_hash(zip([1, 2, 3], [4, 5, 6]), 'mjcpwa')
        >>> #import numpy as np
        >>> #rng = np.random.RandomState(0)
        >>> #check_hash(rng.rand(100000), 'bdwosuey')
        >>> #for got, input_, count, want in failed:
        >>> #    print('failed {} on {}'.format(count, input_))
        >>> #    print('got={}, want={}'.format(got, want))
        >>> #assert not failed
    """
    if alphabet is None:
        alphabet = _ALPHABET_27
    if hashlen is None:
        hashlen = _HASH_LEN2
    if isinstance(data, _stringlike) and len(data) == 0:
        # Make a special hash for empty data
        text = (alphabet[0] * hashlen)
    else:
        hasher = hashlib.sha512()
        _update_hasher(hasher, data)
        # Get a 128 character hex string
        text = hasher.hexdigest()
        # Shorten length of string (by increasing base)
        hashstr2 = _convert_hexstr_to_bigbase(text, alphabet, bigbase=len(alphabet))
        # Truncate
        text = hashstr2[:hashlen]
        return text


def _update_hasher(hasher, data):
    """
    This is the clear winner over the generate version.
    Used by hash_data

    Example:
        >>> from ubelt.util_hash import *
        >>> from ubelt.util_hash import _update_hasher
        >>> hasher = hashlib.sha256()
        >>> data = [1, 2, ['a', 2, 'c']]
        >>> _update_hasher(hasher, data)
        >>> print(hasher.hexdigest())
        31991add5389e4bbca49530dfaee96f31035e3df4cd4fd4121a186728532c5b8

    """
    if isinstance(data, (tuple, list, zip)):
        needs_iteration = True
    # elif (util_type.HAVE_NUMPY and isinstance(data, np.ndarray) and
    #       data.dtype.kind == 'O'):
    #     # ndarrays of objects cannot be hashed directly.
    #     needs_iteration = True
    else:
        needs_iteration = False

    if needs_iteration:
        # try to nest quickly without recursive calls
        SEP = b'SEP'
        iter_prefix = b'ITER'
        iter_ = iter(data)
        hasher.update(iter_prefix)
        try:
            for item in iter_:
                prefix, hashable = _covert_to_hashable(data)
                binary_data = SEP + prefix + hashable
                hasher.update(binary_data)
        except TypeError:
            # need to use recursive calls
            # Update based on current item
            _update_hasher(hasher, item)
            for item in iter_:
                # Ensure the items have a spacer between them
                hasher.update(SEP)
                _update_hasher(hasher, item)
    else:
        prefix, hashable = _covert_to_hashable(data)
        binary_data = prefix + hashable
        hasher.update(binary_data)


def _covert_to_hashable(data):
    r"""
    Args:
        data (object): arbitrary data

    Returns:
        tuple(bytes, bytes): prefix, hashable:
            indicates the


    CommandLine:
        python -m ubelt.util_hash _covert_to_hashable

    Example:
        >>> from ubelt.util_hash import *  # NOQA
        >>> from ubelt.util_hash import _covert_to_hashable  # NOQA
        >>> import ubelt as ub
        >>> assert _covert_to_hashable('string') == (b'', b'string')
        >>> assert _covert_to_hashable(1) == (b'', b'\x00\x00\x00\x01')
        >>> assert _covert_to_hashable(1.0) == (b'', b'1.0')
    """
    if isinstance(data, six.binary_type):
        hashable = data
        prefix = b'TXT'
    # elif util_type.HAVE_NUMPY and isinstance(data, np.ndarray):
    #     if data.dtype.kind == 'O':
    #         msg = '[ub] hashing ndarrays with dtype=object is unstable'
    #         warnings.warn(msg, RuntimeWarning)
    #         hashable = data.dumps()
    #     else:
    #         hashable = data.tobytes()
    #     prefix = b'NDARR'
    elif isinstance(data, six.text_type):
        # convert unicode into bytes
        hashable = data.encode('utf-8')
        prefix = b'TXT'
    elif isinstance(data, uuid.UUID):
        hashable = data.bytes
        prefix = b'UUID'
    elif isinstance(data, int):
        # warnings.warn('[util_hash] Hashing ints is slow, numpy is prefered')
        hashable = _int_to_bytes(data)
        # hashable = data.to_bytes(8, byteorder='big')
        prefix = b'INT'
    elif isinstance(data, float):
        hashable = repr(data).encode('utf8')
        prefix = b'FLT'
    # elif util_type.HAVE_NUMPY and isinstance(data, np.int64):
    #     return _covert_to_hashable(int(data))
    # elif util_type.HAVE_NUMPY and isinstance(data, np.float64):
    #     a, b = float(data).as_integer_ratio()
    #     hashable = (a.to_bytes(8, byteorder='big') +
    #                 b.to_bytes(8, byteorder='big'))
    #     prefix = b'FLOAT'
    else:
        raise TypeError('unknown hashable type=%r' % (type(data)))
    prefix = b''
    return prefix, hashable


def _convert_hexstr_to_bigbase(hexstr, alphabet, bigbase):
    r"""
    Packs a long hexstr into a shorter length string with a larger base

    Example:
        >>> from ubelt.util_hash import _ALPHABET_27
        >>> from ubelt.util_hash import _convert_hexstr_to_bigbase
        >>> newbase_str = _convert_hexstr_to_bigbase(
        ...     'ffffffff', _ALPHABET_27, len(_ALPHABET_27))
        >>> print(newbase_str)
        vxlrmxn

    Sympy:
        >>> import sympy as sy
        >>> # Determine the length savings with lossless conversion
        >>> consts = dict(hexbase=16, hexlen=256, bigbase=27)
        >>> symbols = sy.symbols('hexbase, hexlen, bigbase, newlen')
        >>> haexbase, hexlen, bigbase, newlen = symbols
        >>> eqn = sy.Eq(16 ** hexlen,  bigbase ** newlen)
        >>> newlen_ans = sy.solve(eqn, newlen)[0].subs(consts).evalf()
        >>> print('newlen_ans = %r' % (newlen_ans,))
        >>> # for a 27 char alphabet we can get 216
        >>> print('Required length for lossless conversion len2 = %r' % (len2,))
        >>> def info(base, len):
        ...     bits = base ** len
        ...     print('base = %r' % (base,))
        ...     print('len = %r' % (len,))
        ...     print('bits = %r' % (bits,))
        >>> info(16, 256)
        >>> info(27, 16)
        >>> info(27, 64)
        >>> info(27, 216)
    """
    x = int(hexstr, 16)  # first convert to base 16
    if x == 0:
        return '0'
    sign = 1 if x > 0 else -1
    x *= sign
    digits = []
    while x:
        digits.append(alphabet[x % bigbase])
        x //= bigbase
    if sign < 0:
        digits.append('-')
        digits.reverse()
    newbase_str = ''.join(digits)
    return newbase_str


if __name__ == '__main__':
    r"""
    CommandLine:
        python -m ubelt.util_hash
    """
    import ubelt as ub  # NOQA
    ub.doctest_package()
