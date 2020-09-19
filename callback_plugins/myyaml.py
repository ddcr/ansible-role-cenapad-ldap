from __future__ import (absolute_import, division, print_function,
                        with_statement)

import difflib
import json
import re
import string
import sys
import warnings

import yaml

from ansible import constants as C
from ansible.module_utils._text import to_bytes, to_text
from ansible.module_utils.six import string_types
from ansible.parsing.yaml.dumper import AnsibleDumper
from ansible.plugins.callback import CallbackBase, strip_internal_keys
from ansible.plugins.callback.default import CallbackModule as Default
from ansible.utils.color import stringc

__metaclass__ = type



DOCUMENTATION = '''
    callback: myyaml
    type: stdout
    short_description: import yaml formated stdout/stderr from ansible > 2.4
    description:
      - Ansible with improved output easier to read
    version_added: 2.4
    extends_documentation_fragment:
      - default_callback
    requirements:
      - set as stdout in configuration
'''
#----------------------------------------------------------------
# source: http://stackoverflow.com/a/15423007/115478
# This is to display long string with \n (multi-line string) as
# a literal scalar in YAML:
#
# my_obj.short = "Hello"
# my_obj.long = "Line1\nLine2\nLine3"
#
# results in
#
# short: "Hello"
# long: |
#     Line1
#     Line2
#     Line3
#----------------------------------------------------------------

def should_use_block(value):
    for c in u"\u000a\u000d\u001c\u001d\u001e\u0085\u2028\u2029":
        if c in value:
            return True
    return False


def my_represent_scalar(self, tag, value, style=None):
    if style is None:
        # this is the bit included in the original definition
        if should_use_block(value):
            style = '|'
            #
            # DDCR: source here is from recent versions of ansible;
            #       they added more stuff below ...
            #
            # we care more about readable than accuracy, so...
            # ...no trailing space
            value = value.rstrip()
            # ...and non-printable characters
            value = ''.join(x for x in value if x in string.printable)
            # ...tabs prevent blocks from expanding
            value = value.expandtabs()
            # ...and odd bits of whitespace
            value = re.sub(r'[\x0b\x0c\r]', '', value)
            # ...as does trailing space
            value = re.sub(r' +\n', '\n', value)
        else:
            style = self.default_style
    node = yaml.representer.ScalarNode(tag, value, style=style)
    if self.alias_key is not None:
        self.represented_objects[self.alias_key] = node
    return node


def my_serialize_diff(diff):
    return to_text(yaml.dump(diff, allow_unicode=True, width=1000, Dumper=AnsibleDumper, default_flow_style=False))


class CallbackModule(Default):
    """Output YAML instead of JSON
    """ 

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'myyaml'
    
    def __init__(self):
        super(CallbackModule, self).__init__()
        yaml.representer.BaseRepresenter.represent_scalar = my_represent_scalar

    def _dump_results(self, result, indent=None, sort_keys=True, keep_invocation=False):
        if result.get('_ansible_no_log', False):
            return json.dumps(dict(censored="the output has been hidden due to the fact that 'no_log: true' was specified for this result"))

        # This is only needed if using json
        # if not indent and (result.get('_ansible_verbose_always') or self._display.verbosity > 2):
        #     indent = 4

        # All result keys stating with _ansible_ are internal, so remove them from the result before we output anything.
        abridged_result = strip_internal_keys(result)

        # remove invocation unless specifically wanting it
        if not keep_invocation and self._display.verbosity < 3 and 'invocation' in result:
            del abridged_result['invocation']

        # remove diff information from screen output
        if self._display.verbosity < 3 and 'diff' in result:
            del abridged_result['diff']

        # remove exception from screen output
        if 'exception' in abridged_result:
            del abridged_result['exception']

        # now dump in YAML format. Remove more items from abridged_result ...
        dumped = ''

        if 'changed' in abridged_result:
            dumped += 'changed=' + str(abridged_result['changed']).lower() + ' '
            del abridged_result['changed']

        if 'skipped' in abridged_result:
            dumped += 'skipped=' + \
                str(abridged_result['skipped']).lower() + ' '
            del abridged_result['skipped']

        # if we already have stdout, we don't need stdout_lines
        if 'stdout' in abridged_result and 'stdout_lines' in abridged_result:
            abridged_result['stdout_lines'] = '<omitted>'

        # if we already have stderr, we don't need stderr_lines
        if 'stderr' in abridged_result and 'stderr_lines' in abridged_result:
            abridged_result['stderr_lines'] = '<omitted>'

        if abridged_result:
            dumped += '\n'
            dumped += to_text(yaml.dump(abridged_result, allow_unicode=True, width=1000, Dumper=AnsibleDumper, default_flow_style=False))
       
        # indent by a couple of spaces
        dumped = '\n  '.join(dumped.split('\n')).rstrip()
        return dumped

    def _get_diff(self, difflist):

        if not isinstance(difflist, list):
            difflist = [difflist]

        ret = []
        for diff in difflist:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    if 'dst_binary' in diff:
                        ret.append(
                            "diff skipped: destination file appears to be binary\n")
                    if 'src_binary' in diff:
                        ret.append(
                            "diff skipped: source file appears to be binary\n")
                    if 'dst_larger' in diff:
                        ret.append(
                            "diff skipped: destination file size is greater than %d\n" % diff['dst_larger'])
                    if 'src_larger' in diff:
                        ret.append(
                            "diff skipped: source file size is greater than %d\n" % diff['src_larger'])
                    if 'before' in diff and 'after' in diff:
                        # format complex structures into 'files'
                        for x in ['before', 'after']:
                            if isinstance(diff[x], dict):
                                # diff[x] = json.dumps(
                                #     diff[x], sort_keys=True, indent=4, separators=(',', ': ')) + '\n'
                                diff[x] = my_serialize_diff(diff[x])
                        if 'before_header' in diff:
                            before_header = "before: %s" % diff['before_header']
                        else:
                            before_header = 'before'
                        if 'after_header' in diff:
                            after_header = "after: %s" % diff['after_header']
                        else:
                            after_header = 'after'
                        before_lines = to_text(diff['before']).splitlines(True)
                        after_lines = to_text(diff['after']).splitlines(True)
                        if before_lines and not before_lines[-1].endswith('\n'):
                            before_lines[-1] += '\n\\ No newline at end of file\n'
                        if after_lines and not after_lines[-1].endswith('\n'):
                            after_lines[-1] += '\n\\ No newline at end of file\n'
                        differ = difflib.unified_diff(before_lines,
                                                      after_lines,
                                                      fromfile=before_header,
                                                      tofile=after_header,
                                                      fromfiledate='',
                                                      tofiledate='',
                                                      n=C.DIFF_CONTEXT)
                        difflines = list(differ)
                        if len(difflines) >= 3 and sys.version_info[:2] == (2, 6):
                            # difflib in Python 2.6 adds trailing spaces after
                            # filenames in the -- before/++ after headers.
                            difflines[0] = difflines[0].replace(' \n', '\n')
                            difflines[1] = difflines[1].replace(' \n', '\n')
                            # it also treats empty files differently
                            difflines[2] = difflines[2].replace('-1,0', '-0,0').replace('+1,0', '+0,0')
                        has_diff = False
                        for line in difflines:
                            has_diff = True
                            if line.startswith('+'):
                                line = stringc(line, C.COLOR_DIFF_ADD)
                            elif line.startswith('-'):
                                line = stringc(line, C.COLOR_DIFF_REMOVE)
                            elif line.startswith('@@'):
                                line = stringc(line, C.COLOR_DIFF_LINES)
                            ret.append(line)
                        if has_diff:
                            ret.append('\n')
                    if 'prepared' in diff:
                        ret.append(to_text(diff['prepared']))
            except UnicodeDecodeError:
                ret.append(
                    ">> the files are different, but the diff library cannot compare unicode strings\n\n")
        return u''.join(ret)
