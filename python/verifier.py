#!/usr/bin/python -S
#
# Copyright (C) 2009 Andy Chu
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Demonstration of how to write verifiers.

Since the tests are in Python, we of course can just import the Python
implementation of json-template to test it.

This uses the command line tool python/expand.py to demonstrate one way to test implementations in other languages.
"""

__author__ = 'Andy Chu'

import sys
try:
  import json
except ImportError:
  import simplejson as json

from taste import os_process
import taste

import base_verifier  # TODO: Move this into a package

import jsontemplate  # module under *direct* test
from jsontemplate import formatters


class InternalTemplateVerifier(base_verifier.JsonTemplateVerifier):
  """Verifies template behavior in-process."""

  LABELS = ['python']

  def Expansion(
      self, template_def, dictionary, expected, ignore_whitespace=False,
      ignore_all_whitespace=False, all_formatters=False):
    """
    Args:
      template_def: taste.ClassDef instance.
    """
    if all_formatters:
      template_def.kwargs['more_formatters'] = formatters.PythonPercentFormat

    template = jsontemplate.Template(*template_def.args, **template_def.kwargs)

    left = expected
    right = template.expand(dictionary)

    self.LongStringsEqual(left, right, ignore_whitespace=ignore_whitespace)

  def EvaluationError(self, exception, template_def, data_dict):
    template = jsontemplate.Template(*template_def.args, **template_def.kwargs)
    self.Raises(exception, template.expand, data_dict)

  def CompilationError(self, exception, *args, **kwargs):
    self.Raises(exception, jsontemplate.Template, *args, **kwargs)


class ExternalVerifier(base_verifier.JsonTemplateVerifier):
  """Verifies template behavior in an external process."""

  LABELS = ['python']

  def __init__(self, script_path):
    taste.StandardVerifier.__init__(self)
    self.script_path = script_path
    self.runner = os_process.Runner(universal_newlines=True)

  def _RunScript(self, template_str, dictionary, all_formatters=False):
    data = json.dumps(dictionary)
    argv = [self.script_path, template_str, data]
    if all_formatters:
      argv.append('--more-formatters')
    return self.runner.Result(argv)

  @staticmethod
  def _MakeTemplateStr(template_def):
    template_str = template_def.args[0]
    options = template_def.kwargs

    if options:
      lines = []
      for k, v in options.iteritems():
        lines.append('%s: %s\n' % (k.replace('_', '-'), v))
      header = ''.join(lines) + '\n'
    else:
      header = ''

    return header + template_str

  def Expansion(
      self, template_def, dictionary, expected, ignore_whitespace=False,
      ignore_all_whitespace=False, all_formatters=False):
    """
    Args:
      template_def: ClassDef instance that defines a Template.
    """
    template_str = self._MakeTemplateStr(template_def)
    result = self._RunScript(
        template_str, dictionary, all_formatters=all_formatters)

    self.Equal(result.exit_code, 0, 'stderr: %r' % result.stderr)
    self.LongStringsEqual(
        result.stdout, expected, ignore_whitespace=ignore_whitespace,
        ignore_all_whitespace=ignore_all_whitespace)

  def EvaluationError(self, exception, template_def, data_dict):
    template_str = self._MakeTemplateStr(template_def)
    result = self._RunScript(template_str, data_dict)

    self.Equal(result.exit_code, 1)
    print exception.__name__
    self.In(exception.__name__, result.stderr)

  def CompilationError(self, exception, *args, **kwargs):
    template_def = taste.ClassDef(*args, **kwargs)
    template_str = self._MakeTemplateStr(template_def)
    result = self._RunScript(template_str, {})
    self.Equal(result.exit_code, 1)
    print exception.__name__
    self.In(exception.__name__, result.stderr)
