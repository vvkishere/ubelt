"""
By default ubelt should work without any dependency on numpy. However, certain
functions should be able to know about the ndarray type. If numpy exists, these
functions will be available. However, ubelt will not import numpy by default.
(to avoid loading the shared lib)

Perhaps it would be better if ubelt had a plugin structure.  In fact, that is
probably the correct way to do this.
"""
