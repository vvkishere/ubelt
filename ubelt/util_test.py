# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import, unicode_literals
import warnings
import sys
import six
from ubelt import util_mixins
from ubelt import util_str
from ubelt import util_colors
from os.path import exists


# prevents doctest import * from working
# __all__ = [
#     'doctest_package'
# ]


def parse_src_want(docsrc):
    """
    Breaks into sections of source code and result checks

    Args:
        docsrc (str):

    CommandLine:
        python -m ubelt.util_test parse_src_want

    References:
        https://stackoverflow.com/questions/46061949/parse-until-expr-complete

    Example:
        >>> from ubelt.util_test import *  # NOQA
        >>> from ubelt.meta import docscrape_google
        >>> import inspect
        >>> docstr = inspect.getdoc(parse_src_want)
        >>> blocks = dict(docscrape_google.split_google_docblocks(docstr))
        >>> docsrc = blocks['Example']
        >>> src, want = parse_src_want(docsrc)

    Example:
        >>> from ubelt.util_test import *  # NOQA
        >>> from ubelt.meta import docscrape_google
        >>> import inspect
        >>> docstr = inspect.getdoc(parse_src_want)
        >>> blocks = dict(docscrape_google.split_google_docblocks(docstr))
        >>> str = (
        ...   '''
        ...    TODO: be able to parse docstrings like this.
        ...    ''')
        >>> print('Intermediate want')
        Intermediate want
        >>> docsrc = blocks['Example']
        >>> src, want = parse_src_want(docsrc)
    """
    from ubelt.meta import static_analysis as static

    # TODO: new strategy.
    # Parse as much as possible until we get to a non-doctest line then check
    # if the syntax is a valid parse tree. if not, add the line and potentially
    # continue. Otherwise infer that it is a want line.

    # parse and differenatiate between doctest source and want statements.
    parsed = []
    current = []
    for linex, line in enumerate(docsrc.splitlines()):
        if not current and not line.startswith(('>>>', '...')):
            parsed.append(('want', line))
        else:
            prefix = line[:4]
            suffix = line[4:]
            if prefix.strip() not in {'>>>', '...', ''}:  # nocover
                raise SyntaxError(
                    'Bad indentation in doctest on line {}: {!r}'.format(
                        linex, line))
            current.append(suffix)
            if static.is_complete_statement(current):
                statement = ('\n'.join(current))
                parsed.append(('source', statement))
                current = []

    statements = [val for type_, val in parsed if type_ == 'source']
    wants = [val for type_, val in parsed if type_ == 'want']

    src = '\n'.join([line for val in statements for line in val.splitlines()])
    # take just the last want for now
    if len(wants) > 0:
        want = wants[-1]
    else:
        want = None

    # FIXME: hacks src to make output lines assign
    # to a special result variable instead
    # if want is not None and 'result = ' not in src:
    #     # Check if the last line has a "want"
    #     import ast
    #     tree = ast.parse(src)
    #     if isinstance(tree.body[-1], ast.Expr):  # pragma: no branch
    #         lines = src.splitlines()
    #         # Hack to insert result variable
    #         lines[-1] = 'result = ' + lines[-1]
    #         src = '\n'.join(lines)
    return src, want


class ExitTestException(Exception):
    pass


class _AbstractTest(util_mixins.NiceRepr):

    def __nice__(self):
        return self.modname + ' ' + self.callname

    @property
    def cmdline(self):
        return 'python -m ' + self.modname + ' ' + self.unique_callname

    @property
    def unique_callname(self):
        return self.callname

    @property
    def valid_testnames(self):
        return {
            self.callname,
        }

    def is_disabled(self):
        return False

    def pre_run(self, verbose):
        if verbose >= 1:
            print('============')
            print('* BEGIN EXAMPLE : {}'.format(self.callname))
            print(self.cmdline)
            if verbose >= 2:
                print(self.format_src())
        else:  # nocover
            sys.stdout.write('.')
            sys.stdout.flush()

    def repr_failure(self, verbose=1):
        # TODO: print out nice line number
        lines = []
        if verbose > 0:
            lines += [
                '',
                'report failure',
                self.cmdline,
                self.format_src(),
            ]
        lines += [
            '* FAILURE: {}, {}'.format(self.callname, type(self.ex)),
            self.cap.text,
        ]
        # TODO: remove appropriate amount of traceback
        # exc_type, exc_value, exc_traceback = sys.exc_info()
        # exc_traceback = exc_traceback.tb_next
        # six.reraise(exc_type, exc_value, exc_traceback)
        return '\n'.join(lines)

    def report_failure(self, verbose):  # nocover
        self.repr_failure(verbose=verbose)

    def post_run(self, verbose):  # nocover
        if self.ex is None and verbose >= 1:
            if self.cap.text is not None:  # nocover
                assert isinstance(self.cap.text, six.text_type), 'do not use ascii'
            try:
                print(self.cap.text)
            except UnicodeEncodeError:  # nocover
                print('Weird travis bug')
                print('type(cap.text) = %r' % (type(self.cap.text),))
                print('cap.text = %r' % (self.cap.text,))
            print('* SUCCESS: {}'.format(self.callname))
        summary = {
            'passed': self.ex is None
        }
        return summary


class UnitTest(_AbstractTest):
    def __init__(self, calldef, modpath):
        from ubelt.meta import static_analysis as static
        self.modpath = modpath
        self.modname = static.modpath_to_modname(modpath)
        self.calldef = calldef
        self.callname = calldef.callname
        self._src = None
        self._want = None
        self.ex = None
        self.cap = None

    def format_src(self, linenums=True, colored=True):
        """
        Adds prefix and line numbers to a doctest

        Example:
            >>> from ubelt.util_test import *  # NOQA
            >>> package_name = 'ubelt'
            >>> testables = parse_unittestables(package_name)
            >>> self = next(testables)
            >>> print(self.format_src())
            >>> print(self.format_src(linenums=False, colored=False))
            >>> assert not self.is_disabled()
        """
        if self.calldef.lineno is None:
            raise Exception('cannot format source for {}'.format(self))
        with open(self.modpath) as file:
            lines = list(file.readlines())

        x1, x2 = self.calldef.lineno - 1, self.calldef.endlineno - 1
        src = ''.join(lines[x1:x2])
        if colored:
            src = util_colors.highlight_code(src, 'python')
        return src

    def run_example(self, verbose=None):
        """
        Executes the unit-test
        """
        if verbose is None:
            verbose = 2
        self.pre_run(verbose)
        # Prepare for actual test run
        test_locals = {}
        # TODO: generalize for non-function non-empty args
        src = util_str.codeblock(
            '''
            from {modname} import {callname}
            {callname}()
            ''').format(modname=self.modname, callname=self.callname)
        code = compile(src, '<string>', 'exec')
        self.cap = util_str.CaptureStdout(enabled=verbose <= 1)

        try:
            with self.cap:
                exec(code, test_locals)
        # Handle anything that could go wrong
        except ExitTestException:  # nocover
            if verbose > 0:
                print('Test gracefully exists')
        except Exception as ex:  # nocover
            self.ex = ex
            self.report_failure(verbose)
            raise

        return self.post_run(verbose)


class DocTest(_AbstractTest):
    """
    Holds information necessary to execute and verify a doctest

    Example:
        >>> # pytest.skip
        >>> from ubelt.util_test import *  # NOQA
        >>> package_name = 'ubelt'
        >>> testables = parse_doctestables(package_name)
        >>> self = next(testables)
        >>> print(self.want)
        >>> print(self.want)
        >>> print(self.valid_testnames)
    """

    def __init__(self, modpath, callname, block, num):
        from ubelt.meta import static_analysis as static
        self.modpath = modpath
        self.modname = static.modpath_to_modname(modpath)
        self.callname = callname
        self.block = block
        self.lineno = 0  # TODO
        self.num = num
        self._src = None
        self._want = None
        self.ex = None
        self.cap = None
        self.globs = {}

    @property
    def src(self):
        if self._src is None:
            self._parse()
        return self._src

    @property
    def want(self):
        if self._want is None:
            self._parse()
        return self._want

    def _parse(self):
        self._src, self._want = parse_src_want(self.block)

    def is_disabled(self):
        return self.block.startswith('>>> # DISABLE_DOCTEST')

    @property
    def unique_callname(self):
        return self.callname + ':' + str(self.num)

    @property
    def valid_testnames(self):
        return {
            self.callname,
            self.unique_callname,
        }

    def format_src(self, linenums=True, colored=True):
        """
        Adds prefix and line numbers to a doctest

        Example:
            >>> # pytest.skip
            >>> from ubelt.util_test import *  # NOQA
            >>> package_name = 'ubelt'
            >>> testables = parse_doctestables(package_name)
            >>> self = next(testables)
            >>> print(self.format_src())
            >>> print(self.format_src(linenums=False, colored=False))
            >>> assert not self.is_disabled()
        """
        doctest_src = self.src
        doctest_src = util_str.indent(doctest_src, '>>> ')
        if linenums:
            doctest_src = '\n'.join([
                '%3d %s' % (count, line)
                for count, line in enumerate(doctest_src.splitlines(), start=1)])
        if colored:
            doctest_src = util_colors.highlight_code(doctest_src, 'python')
        return doctest_src

    def run_example(self, verbose=None):
        """
        Executes the doctest

        TODO:
            * break src and want into multiple parts

        Notes:
            * There is no difference between locals/globals in exec context
            Only pass in one dict, otherwise there is weird behavior
            References: https://bugs.python.org/issue13557
        """
        if verbose is None:
            verbose = 2
        self._parse()
        self.pre_run(verbose)
        # Prepare for actual test run
        test_globals = self.globs
        self.cap = util_str.CaptureStdout(enabled=verbose <= 1)
        code = compile(self.src, '<string>', 'exec')
        try:
            with self.cap:
                exec(code, test_globals)
        # Handle anything that could go wrong
        except ExitTestException:  # nocover
            if verbose > 0:
                print('Test gracefully exists')
        except Exception as ex:  # nocover
            self.ex = ex
            self.report_failure(verbose)
            raise

        return self.post_run(verbose)


def parse_docstr_examples(docstr, callname=None, modpath=None):
    """
    Parses Google-style doctests from a docstr and generates example objects
    """
    try:
        from ubelt.meta import docscrape_google
        blocks = docscrape_google.split_google_docblocks(docstr)
        example_blocks = []
        for type_, block in blocks:
            if type_.startswith('Example'):
                example_blocks.append((type_, block))
            if type_.startswith('Doctest'):
                example_blocks.append((type_, block))
        for num, (type_, block) in enumerate(example_blocks):
            example = DocTest(modpath, callname, block, num)
            yield example
    except Exception as ex:  # nocover
        msg = ('Cannot scrape callname={} in modpath={}.\n'
               'Caused by={}')
        msg = msg.format(callname, modpath, ex)
        raise Exception(msg)


def package_calldefs(package_name, exclude=[], strict=False):
    """
    Statically generates all callable definitions in a package
    """
    from ubelt.meta import static_analysis as static

    modnames = static.package_modnames(package_name, exclude=exclude)
    for modname in modnames:
        modpath = static.modname_to_modpath(modname, hide_init=False)
        if not exists(modpath):  # nocover
            warnings.warn(
                'Module {} does not exist. '
                'Is it an old pyc file?'.format(modname))
            continue
        try:
            calldefs = static.parse_calldefs(fpath=modpath)
        except SyntaxError as ex:  # nocover
            msg = 'Cannot parse module={} at path={}.\nCaused by={}'
            msg = msg.format(modname, modpath, ex)
            if strict:
                raise Exception(msg)
            else:
                warnings.warn(msg)
                continue
        else:
            yield calldefs, modpath


def parse_doctestables(package_name, exclude=[], strict=False):
    r"""
    Finds all functions/callables with Google-style example blocks

    CommandLine:
        python -m ubelt.util_test parse_doctestables

    Example:
        >>> # pytest.skip
        >>> from ubelt.util_test import *  # NOQA
        >>> package_name = 'ubelt'
        >>> testables = list(parse_doctestables(package_name))
        >>> this_example = None
        >>> for example in testables:
        >>>     print(example)
        >>>     if example.callname == 'parse_doctestables':
        >>>         this_example = example
        >>> assert this_example is not None
        >>> assert this_example.callname == 'parse_doctestables'
    """
    for calldefs, modpath in package_calldefs(package_name, exclude, strict):
        for callname, calldef in calldefs.items():
            docstr = calldef.docstr
            if calldef.docstr is not None:
                for example in parse_docstr_examples(docstr, callname, modpath):
                    yield example


def unittest_calldefs(package_name, exclude=[], strict=False):
    """
    Statically generates all callable definitions in a package tests dir
    """
    from ubelt.meta import static_analysis as static
    from os.path import join
    import glob

    basepath = static.modname_to_modpath(package_name, hide_init=True)
    # TODO: generalize
    globpat = join(basepath, 'tests', 'test_*')
    for test_path in glob.glob(globpat, recursive=True):
        modpath = test_path
        try:
            calldefs = static.parse_calldefs(fpath=modpath)
        except SyntaxError as ex:  # nocover
            msg = 'Cannot parse modpath={}.\nCaused by={}'
            msg = msg.format(modpath, ex)
            if strict:
                raise Exception(msg)
            else:
                warnings.warn(msg)
                continue
        else:
            yield calldefs, modpath


def parse_unittestables(package_name, verbose=False):
    """
    Finds all unit tests (functions / methods prefixed with test_) in a package

    CommandLine:
        python -m ubelt.util_test parse_unittestables

    Example:
        >>> from ubelt.util_test import *  # NOQA
        >>> package_name = 'ubelt'
        >>> testables = list(parse_unittestables(package_name, verbose=True))
    """
    for calldefs, modpath in unittest_calldefs(package_name):
        for callname, calldef in calldefs.items():
            if callname.startswith('test_'):
                testable = UnitTest(calldef, modpath)
                yield testable


class CoverageContext(object):  # nocover
    """
    Context based wrapper around the coverage object
    (configured for ubelt)
    """

    def __init__(self, modnames, enabled=True):
        self.modnames = modnames
        self.enabled = enabled

    def coverage_exclusions(self):
        exclude_lines = [
            'pragma: no cover',
            '.*  # pragma: no cover',
            '.*  # nocover',
            'def __repr__',
            'raise AssertionError',
            'raise NotImplementedError',
            'if 0:',
            'if trace is not None',
            'verbose = .*',
            'raise',
            'pass',
            'if _debug:',
            'if __name__ == .__main__.:',
            'print(.*)',
            # Exclude this function as well
        ]
        if six.PY2:
            exclude_lines.append('.*if six.PY3:')
        elif six.PY3:
            exclude_lines.append('.*if six.PY2:')
        return exclude_lines

    def _write_coveragerc(self):
        # Dump the coveragerc file for codecov.io
        # Doesn't seem to work :(
        # rcpath = '.coveragerc'
        # if not exists(rcpath) and not exists('__init__.py'):
        #     import textwrap
        #     rctext = textwrap.dedent(
        #         r'''
        #         [report]
        #         exclude_lines =
        #         '''
        #     )
        #     rctext += util_str.indent('\n'.join(exclude_lines))
        #     from ubelt import util_io
        #     util_io.writeto(rcpath, rctext)
        pass

    def start(self):
        import coverage
        self.cov = coverage.Coverage(source=self.modnames)
        for line in self.coverage_exclusions():
            self.cov.exclude(line)
        print('Starting coverage')
        # self._write_coveragerc()
        self.cov.start()
        # Hack to reload modules for coverage
        import imp
        for modname in self.modnames:
            if modname in sys.modules:
                # print('realoading modname = %r' % (modname,))
                imp.reload(sys.modules[modname])

    def stop(self):
        print('Stoping coverage')
        self.cov.stop()
        print('Saving coverage for codecov')
        self.cov.save()
        print('Generating coverage html report')
        self.cov.html_report()
        from six.moves import cStringIO
        stream = cStringIO()
        cov_percent = self.cov.report(file=stream)  # NOQA
        stream.seek(0)
        cov_report = stream.read()
        print('Coverage Report:')
        print(cov_report)

    def __enter__(self):
        if self.enabled:
            self.start()
        return self

    def __exit__(self, type_, value, trace):
        if self.enabled:
            self.stop()


class Harness(object):  # nocover
    """
    Main entry point for general testing
    run via: `Harness(<pkgname>).run('all')`
    """
    def __init__(self, package_name, doc=True, unit=True, verbose=None):
        self.package_name = package_name
        self.testables = []
        self.doc = doc
        self.unit = unit

        if verbose is None:
            if '--verbose' in sys.argv:
                verbose = 2
            elif '--quiet' in sys.argv:
                verbose = 0
            else:
                verbose = 1
        self.verbose = verbose

    def collect(self):
        if self.doc:
            self.doctestables = list(parse_doctestables(self.package_name))
            self.testables += self.doctestables
        if self.unit:
            self.unittestables = list(parse_doctestables(self.package_name))
            self.testables += self.unittestables

    def refine(self, command):
        print('gathering tests')
        enabled_tests = []
        run_all = command == 'all'
        for test in self.testables:
            if run_all or command in test.valid_testnames:
                if run_all and test.is_disabled():
                    continue
                enabled_tests.append(test)
        self.enabled_tests = enabled_tests

    def run(self, command, check_coverage=None):
        if command == 'list':
            print('Listing tests')

        if command is None:
            # Display help if command is not specified
            print('No testname given. Use `all` to run everything or')
            print('Pick from a list of valid choices:')
            command = 'list'

        self.collect()

        if command == 'list':
            print('\n'.join([test.cmdline for test in self.testables]))

        self.refine(command)

        if check_coverage is None:
            check_coverage = command == 'all'

        from ubelt.meta import static_analysis as static
        modnames = list(static.package_modnames(self.package_name))
        # modnames = list({e.modname for e in self.enabled_tests})
        with CoverageContext(modnames, enabled=check_coverage):
            n_total = len(self.enabled_tests)
            print('running %d test(s)' % (n_total))
            summaries = []
            for test in self.enabled_tests:
                summary = test.run_example(verbose=self.verbose)
                summaries.append(summary)
            if self.verbose <= 0:
                print('')
            n_passed = sum(s['passed'] for s in summaries)
            print('Finished tests')
            print('%d / %d passed'  % (n_passed, n_total))

        # TODO: test summary
        return n_passed == n_total


def doctest_package(package_name=None, command=None, argv=None,
                    check_coverage=None, verbose=None):  # nocover
    r"""
    Executes requested google-style doctests in a package.
    Main entry point into the testing framework.

    Args:
        package_name (str): name of the package
        command (str): determines which doctests to run.
            if command is None, this is determined by parsing sys.argv
        argv (list): if None uses sys.argv
        verbose (bool):  verbosity flag
        exclude (list): ignores any modname matching any of these
            glob-like patterns
        check_coverage (None): if True outputs coverage report

    CommandLine:
        python -m ubelt.util_test doctest_package

    Example:
        >>> # pytest.skip
        >>> from ubelt.util_test import *  # NOQA
        >>> package_name = 'ubelt.util_test'
        >>> result = doctest_package(package_name, 'list', argv=[''])
    """
    from ubelt.meta import static_analysis as static
    from ubelt.meta import dynamic_analysis
    print('Start doctest_package({})'.format(package_name))

    if package_name is None:
        # Determine package name via caller if not specified
        frame_parent = dynamic_analysis.get_parent_frame()
        frame_fpath = frame_parent.f_globals['__file__']
        package_name = static.modpath_to_modname(frame_fpath)

    if command is None:
        if argv is None:
            argv = sys.argv
        # Determine command via sys.argv if not specified
        argv = argv[1:]
        if len(argv) >= 1:
            command = argv[0]
        else:
            command = None

    tester = Harness(package_name, doc=True, unit=False, verbose=verbose)
    result = tester.run(command)
    return result


if __name__ == '__main__':
    r"""
    CommandLine:
        python -m ubelt.util_test
        python -m ubelt.util_test all
    """
    import ubelt as ub  # NOQA
    ub.doctest_package()
