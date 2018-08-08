#  Copyright 2008-2015 Nokia Networks
#  Copyright 2016-     Robot Framework Foundation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from ast import literal_eval
from datetime import datetime, date, timedelta
from decimal import InvalidOperation, Decimal
from enum import EnumMeta

from robot.libraries.DateTime import convert_date, convert_time
from robot.utils import FALSE_STRINGS, is_unicode


class TypeConverter(object):

    def __init__(self, argspec):
        self._argspec = argspec
        self._converters = {int: self._convert_int,
                            float: self._convert_float,
                            Decimal: self._convert_decimal,
                            bool: self._convert_bool,
                            list: self._convert_list,
                            tuple: self._convert_tuple,
                            dict: self._convert_dict,
                            set: self._convert_set,
                            bytes: self._convert_bytes,
                            datetime: self._convert_datetime,
                            date: self._convert_date,
                            timedelta: self._convert_timedelta}

    def convert(self, positional, named):
        positional = zip(self._argspec.positional, positional)
        positional = [self._convert(name, value) for name, value in positional]
        named = {name: self._convert(name, value) for name, value in named}
        return positional, named

    def _convert(self, name, value):
        if name not in self._argspec.types or not is_unicode(value):
            return value
        type_ = self._argspec.types[name]
        if isinstance(type_, EnumMeta):
            converter = self._enum_converter_for(type_)
        else:
            converter = self._converters.get(type_)
        if not converter:
            return value
        if value.upper() == 'NONE':
            return None
        return converter(name, value)

    def _convert_int(self, name, value):
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                self._raise_convert_failed(name, 'integer', value)

    def _convert_float(self, name, value):
        try:
            return float(value)
        except ValueError:
            self._raise_convert_failed(name, 'float', value)

    def _convert_decimal(self, name, value):
        try:
            return Decimal(value)
        except InvalidOperation:
            self._raise_convert_failed(name, 'decimal', value)

    def _convert_bool(self, name, value):
        upper = value.upper()
        if upper == 'TRUE':
            return True
        if value and upper in FALSE_STRINGS:
            return False
        return value

    def _convert_list(self, name, value):
        return self._literal_eval(name, value, list, 'list')

    def _convert_tuple(self, name, value):
        return self._literal_eval(name, value, tuple, 'tuple')

    def _convert_dict(self, name, value):
        return self._literal_eval(name, value, dict, 'dictionary')

    def _convert_set(self, name, value):
        if value == 'set()':
            return set()
        return self._literal_eval(name, value, set, 'set')

    def _convert_bytes(self, name, value):
        try:
            return value.encode('latin-1')
        except UnicodeEncodeError:
            self._raise_convert_failed(name, 'bytes', value)

    def _convert_datetime(self, name, value):
        try:
            return convert_date(value, result_format='datetime')
        except ValueError:
            self._raise_convert_failed(name, 'datetime', value)

    def _convert_date(self, name, value):
        try:
            dt = convert_date(value, result_format='datetime')
            if dt.hour or dt.minute or dt.second or dt.microsecond:
                raise ValueError
            return dt.date()
        except ValueError:
            self._raise_convert_failed(name, 'date', value)

    def _convert_timedelta(self, name, value):
        try:
            return convert_time(value, result_format='timedelta')
        except ValueError:
            self._raise_convert_failed(name, 'timedelta', value)

    def _enum_converter_for(self, enum_):
        def _convert_enum(name, value):
            try:
                return enum_[value]
            except KeyError:
                self._raise_convert_failed(name, enum_.__name__, value)
        return _convert_enum

    def _literal_eval(self, name, value, expected, expected_name):
        try:
            value = literal_eval(value)
            if not isinstance(value, expected):
                raise ValueError
        except ValueError:
            self._raise_convert_failed(name, expected_name, value)
        return value

    def _raise_convert_failed(self, name, expected, value):
        raise ValueError("Argument '%s' cannot be converted to %s, got '%s'."
                         % (name, expected, value))

