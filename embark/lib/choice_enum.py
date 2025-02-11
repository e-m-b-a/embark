__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'Garima Chauhan'
__license__ = 'MIT'

import enum


class ChoiceIntEnum(enum.IntEnum):

    @classmethod
    def choices(cls):
        return [(x.value, x.name) for x in cls]

    @classmethod
    def has_value(cls, value):
        return any(value == item.value for item in cls)
