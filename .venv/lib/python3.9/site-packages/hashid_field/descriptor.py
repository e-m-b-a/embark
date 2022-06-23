from hashids import Hashids

from .hashid import Hashid


class HashidDescriptor(object):
    def __init__(self, field_name, salt, min_length, alphabet, prefix="", hashids=None, enable_hashid_object=True):
        self.field_name = field_name
        self.salt = salt
        self.min_length = min_length
        self.alphabet = alphabet
        self.prefix = prefix
        self.hashids = hashids or Hashids(salt=self.salt, min_length=self.min_length, alphabet=self.alphabet)
        self.enable_hashid_object = enable_hashid_object

    def __get__(self, instance, owner=None):
        if instance is not None and self.field_name in instance.__dict__:
            return instance.__dict__[self.field_name]
        else:
            return None

    def __set__(self, instance, value):
        self._set_value(instance, self.field_name, value, enable_hashid_object=self.enable_hashid_object)
        if not self.enable_hashid_object:
            self._set_value(instance, self.field_name + "_hashid", value, enable_hashid_object=True)

    def _set_value(self, instance, name, value, enable_hashid_object):
        if value is None:
            instance.__dict__[name] = value
        if isinstance(value, Hashid):
            if enable_hashid_object:
                instance.__dict__[name] = value
            else:
                instance.__dict__[name] = str(value)
        else:
            try:
                h = Hashid(value, salt=self.salt, min_length=self.min_length, alphabet=self.alphabet,
                           prefix=self.prefix, hashids=self.hashids)
                if enable_hashid_object:
                    instance.__dict__[name] = h
                else:
                    instance.__dict__[name] = str(h)
            except ValueError:
                instance.__dict__[name] = value
