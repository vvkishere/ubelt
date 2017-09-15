# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from os.path import splitext, split, join


def augpath(path, suffix='', prefix='', ext=None):
    """
    Augments a filename with a suffix and/or a prefix while maintaining or
    modifying the extension.

    Args:
        path (str):
        suffix (str): text to place after the basename before the extension
        prefix (str): text to place before the basename
        ext (str): if specified, replaces the file extension

    Returns:
        str: newpath

    Example:
        >>> import ubelt as ub
        >>> path = 'foo.bar'
        >>> assert ub.augpath(path, prefix='pref_') == 'pref_foo.bar'
        >>> assert ub.augpath(path, suffix='_suff') == 'foo_suff.bar'
        >>> assert ub.augpath(path, ext='.baz') == 'foo.baz'
    """
    # Breakup path
    dpath, fname = split(path)
    fname_noext, orig_ext = splitext(fname)
    if ext is None:
        ext = orig_ext
    # Augment and recombine into new path
    new_fname = ''.join((prefix, fname_noext, suffix, ext))
    newpath = join(dpath, new_fname)
    return newpath


if __name__ == '__main__':
    r"""
    CommandLine:
        python -m ubelt.util_path
        python -m ubelt.util_path all
    """
    import ubelt as ub  # NOQA
    ub.doctest_package()
