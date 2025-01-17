# -*- coding: utf-8 -*-
# (c) 2015, Toshio Kuratomi <tkuratomi@ansible.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

# Make coding more python3-ish
from __future__ import (absolute_import, division)
__metaclass__ = type

import json
import sys
import syslog

from ansible.compat.tests import unittest
from ansible.compat.tests.mock import patch, MagicMock

from ansible.module_utils import basic
from ansible.module_utils.basic import heuristic_log_sanitize
from ansible.module_utils.basic import _return_values, _remove_values


class TestReturnValues(unittest.TestCase):
    dataset = (
            ('string', frozenset(['string'])),
            ('', frozenset()),
            (1, frozenset(['1'])),
            (1.0, frozenset(['1.0'])),
            (False, frozenset()),
            (['1', '2', '3'], frozenset(['1', '2', '3'])),
            (('1', '2', '3'), frozenset(['1', '2', '3'])),
            ({'one': 1, 'two': 'dos'}, frozenset(['1', 'dos'])),
            ({'one': 1, 'two': 'dos',
                'three': ['amigos', 'musketeers', None,
                    {'ping': 'pong', 'base': ('balls', 'raquets')}]},
                frozenset(['1', 'dos', 'amigos', 'musketeers', 'pong', 'balls', 'raquets'])),
        )

    def test_return_values(self):
        for data, expected in self.dataset:
            self.assertEquals(frozenset(_return_values(data)), expected)

    def test_unknown_type(self):
        self.assertRaises(TypeError, frozenset, _return_values(object()))


class TestRemoveValues(unittest.TestCase):
    OMIT = 'VALUE_SPECIFIED_IN_NO_LOG_PARAMETER'
    dataset_no_remove = (
            ('string', frozenset(['nope'])),
            (1234, frozenset(['4321'])),
            (False, frozenset(['4321'])),
            (1.0, frozenset(['4321'])),
            (['string', 'strang', 'strung'], frozenset(['nope'])),
            ({'one': 1, 'two': 'dos', 'secret': 'key'}, frozenset(['nope'])),
            ({'one': 1, 'two': 'dos',
                'three': ['amigos', 'musketeers', None,
                    {'ping': 'pong', 'base': ['balls', 'raquets']}]},
                frozenset(['nope'])),
            )
    dataset_remove = (
            ('string', frozenset(['string']), OMIT),
            (1234, frozenset(['1234']), OMIT),
            (1234, frozenset(['23']), OMIT),
            (1.0, frozenset(['1.0']), OMIT),
            (['string', 'strang', 'strung'], frozenset(['strang']), ['string', OMIT, 'strung']),
            (['string', 'strang', 'strung'], frozenset(['strang', 'string', 'strung']), [OMIT, OMIT, OMIT]),
            (('string', 'strang', 'strung'), frozenset(['string', 'strung']), [OMIT, 'strang', OMIT]),
            ((1234567890, 345678, 987654321), frozenset(['1234567890']), [OMIT, 345678, 987654321]),
            ((1234567890, 345678, 987654321), frozenset(['345678']), [OMIT, OMIT, 987654321]),
            ({'one': 1, 'two': 'dos', 'secret': 'key'}, frozenset(['key']),
                {'one': 1, 'two': 'dos', 'secret': OMIT}),
            ({'one': 1, 'two': 'dos', 'secret': 'key'}, frozenset(['key', 'dos', '1']),
                {'one': OMIT, 'two': OMIT, 'secret': OMIT}),
            ({'one': 1, 'two': 'dos', 'secret': 'key'}, frozenset(['key', 'dos', '1']),
                {'one': OMIT, 'two': OMIT, 'secret': OMIT}),
            ({'one': 1, 'two': 'dos', 'three': ['amigos', 'musketeers', None,
                {'ping': 'pong', 'base': ['balls', 'raquets']}]},
                frozenset(['balls', 'base', 'pong', 'amigos']),
                {'one': 1, 'two': 'dos', 'three': [OMIT, 'musketeers',
                    None, {'ping': OMIT, 'base': [OMIT, 'raquets']}]}),
            ('This sentence has an enigma wrapped in a mystery inside of a secret. - mr mystery',
                frozenset(['enigma', 'mystery', 'secret']),
                'This sentence has an ******** wrapped in a ******** inside of a ********. - mr ********'),
            )

    def test_no_removal(self):
        for value, no_log_strings in self.dataset_no_remove:
            self.assertEquals(_remove_values(value, no_log_strings), value)

    def test_strings_to_remove(self):
        for value, no_log_strings, expected in self.dataset_remove:
            self.assertEquals(_remove_values(value, no_log_strings), expected)

    def test_unknown_type(self):
        self.assertRaises(TypeError, _remove_values, object(), frozenset())


@unittest.skipIf(sys.version_info[0] >= 3, "Python 3 is not supported on targets (yet)")
class TestAnsibleModuleRemoveNoLogValues(unittest.TestCase):
    OMIT = 'VALUE_SPECIFIED_IN_NO_LOG_PARAMETER'
    dataset = (
            (dict(username='person', password='$ecret k3y'),
                dict(one=1, pwd='$ecret k3y', url='https://username:password12345@foo.com/login/',
                    not_secret='following the leader'),
                dict(one=1, pwd=OMIT, url='https://username:password12345@foo.com/login/',
                    not_secret='following the leader')
                ),
            (dict(username='person', password='password12345'),
                dict(one=1, pwd='$ecret k3y', url='https://username:password12345@foo.com/login/',
                    not_secret='following the leader'),
                dict(one=1, pwd='$ecret k3y', url='https://username:********@foo.com/login/',
                    not_secret='following the leader')
                ),
            (dict(username='person', password='$ecret k3y'),
                dict(one=1, pwd='$ecret k3y', url='https://username:$ecret k3y@foo.com/login/',
                    not_secret='following the leader'),
                dict(one=1, pwd=OMIT, url='https://username:********@foo.com/login/',
                    not_secret='following the leader')
                ),
            )

    def setUp(self):
        self.COMPLEX_ARGS = basic.MODULE_COMPLEX_ARGS

    def tearDown(self):
        basic.MODULE_COMPLEX_ARGS = self.COMPLEX_ARGS

    def test_remove_no_log_values(self):
        for args, return_val, expected in self.dataset:
            basic.MODULE_COMPLEX_ARGS = json.dumps(args)
            module = basic.AnsibleModule(
                argument_spec = dict(
                    username=dict(),
                    password=dict(no_log=True),
                    token=dict(no_log=True),
                    ),
                )
            self.assertEquals(module.remove_no_log_values(return_val), expected)
