from ubelt.util_hash import _int_to_bytes, _bytes_to_int


def _test_int_byte_conversion():
    import itertools as it
    import ubelt as ub
    inputs = list(it.chain(
        range(0, 10),
        (2 ** i for i in range(0, 256, 32)),
        (2 ** i + 1 for i in range(0, 256, 32)),
    ))
    for int_0 in inputs:
        print('---')
        print('int_0 = %s' % (ub.repr2(int_0),))
        bytes_ = _int_to_bytes(int_0)
        int_ = _bytes_to_int(bytes_)
        print('bytes_ = %s' % (ub.repr2(bytes_),))
        print('int_ = %s' % (ub.repr2(int_),))
        assert int_ == int_0


# def test_update_hasher():
#     import ubelt
#     rng = np.random.RandomState(0)
#     # str1 = rng.rand(0).dumps()
#     str1 = b'SEP'
#     str2 = rng.rand(10000).dumps()
#     for timer in ubelt.Timerit(100, label='twocall'):
#         hasher = hashlib.sha256()
#         with timer:
#             hasher.update(str1)
#             hasher.update(str2)
#     a = hasher.hexdigest()
#     for timer in ubelt.Timerit(100, label='concat'):
#         hasher = hashlib.sha256()
#         with timer:
#             hasher.update(str1 + str2)
#     b = hasher.hexdigest()
#     assert a == b
#     # CONCLUSION: Faster to concat in case of prefixes and seps

#     nested_data = {'1': [rng.rand(100), '2', '3'],
#                    '2': ['1', '2', '3', '4', '5'],
#                    '3': [('1', '2'), ('3', '4'), ('5', '6')]}
#     data = list(nested_data.values())

#     for timer in ubelt.Timerit(1000, label='cat-generate'):
#         hasher = hashlib.sha256()
#         with timer:
#             hasher.update(b''.join(_bytes_generator(data)))

#     for timer in ubelt.Timerit(1000, label='inc-generate'):
#         hasher = hashlib.sha256()
#         with timer:
#             for b in _bytes_generator(data):
#                 hasher.update(b)

#     for timer in ubelt.Timerit(1000, label='inc-generate'):
#         hasher = hashlib.sha256()
#         with timer:
#             for b in _bytes_generator(data):
#                 hasher.update(b)

#     for timer in ubelt.Timerit(1000, label='chunk-inc-generate'):
#         hasher = hashlib.sha256()
#         import ubelt as ub
#         with timer:
#             for chunk in ub.chunks(_bytes_generator(data), 5):
#                 hasher.update(b''.join(chunk))

#     for timer in ubelt.Timerit(1000, label='inc-update'):
#         hasher = hashlib.sha256()
#         with timer:
#             _update_hasher(hasher, data)

#     data = ub.lorium_ipsum()
#     hash_data(data)
#     ub.hashstr27(data)
#     # %timeit hash_data(data)
#     # %timeit ub.hashstr27(repr(data))

#     for timer in ubelt.Timerit(100, label='twocall'):
#         hasher = hashlib.sha256()
#         with timer:
#             hash_data(data)

#     hasher = hashlib.sha256()
#     hasher.update(memoryview(np.array([1])))
#     print(hasher.hexdigest())

#     hasher = hashlib.sha256()
#     hasher.update(np.array(['1'], dtype=object))
#     print(hasher.hexdigest())
