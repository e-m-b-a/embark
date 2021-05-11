import enum


class ChoiceIntEnum(enum.IntEnum):

    @classmethod
    def choices(cls):
        return [(x.value, x.name) for x in cls]

    @classmethod
    def has_value(cls, value):
        return any(value == item.value for item in cls)