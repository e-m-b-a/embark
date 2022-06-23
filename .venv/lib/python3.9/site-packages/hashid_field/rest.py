from django.apps import apps
from django.core import exceptions
from django.utils.translation import gettext_lazy as _

from hashids import Hashids
from rest_framework import fields

from hashid_field.conf import settings
from hashid_field.hashid import Hashid
from hashid_field.lookups import _is_int_representation


class UnconfiguredHashidSerialField(fields.Field):
    def bind(self, field_name, parent):
        super().bind(field_name, parent)
        raise exceptions.ImproperlyConfigured(
            "The field '{field_name}' on {parent} must be explicitly declared when used with a ModelSerializer".format(
                field_name=field_name, parent=parent.__class__.__name__))


class HashidSerializerMixin(object):
    usage_text = "Must pass a HashidField, HashidAutoField or 'app_label.model.field'"
    default_error_messages = {
        'invalid': _("'%(value)s' value must be a positive integer or a valid Hashids string."),
        'invalid_hashid': _("'%(value)s' value must be a valid Hashids string."),
    }

    def __init__(self, **kwargs):
        self.hashid_salt = kwargs.pop('salt', settings.HASHID_FIELD_SALT)
        self.hashid_min_length = kwargs.pop('min_length', settings.HASHID_FIELD_MIN_LENGTH)
        self.hashid_alphabet = kwargs.pop('alphabet', settings.HASHID_FIELD_ALPHABET)
        self.allow_int_lookup = kwargs.pop('allow_int_lookup', settings.HASHID_FIELD_ALLOW_INT_LOOKUP)
        self.prefix = kwargs.pop('prefix', "")
        self._hashids = kwargs.pop('hashids', None)

        source_field = kwargs.pop('source_field', None)
        if source_field:
            from hashid_field import HashidField, BigHashidField, HashidAutoField, BigHashidAutoField
            if isinstance(source_field, str):
                try:
                    app_label, model_name, field_name = source_field.split(".")
                except ValueError:
                    raise ValueError(self.usage_text)
                model = apps.get_model(app_label, model_name)
                source_field = model._meta.get_field(field_name)
            elif not isinstance(source_field, (HashidField, BigHashidField, HashidAutoField, BigHashidAutoField)):
                raise TypeError(self.usage_text)
            self.hashid_salt = source_field.salt
            self.hashid_min_length = source_field.min_length
            self.hashid_alphabet = source_field.alphabet
            self.allow_int_lookup = source_field.allow_int_lookup
            self.prefix = source_field.prefix
            self._hashids =source_field._hashids
        if not self._hashids:
            self._hashids = Hashids(salt=self.hashid_salt, min_length=self.hashid_min_length,
                                    alphabet=self.hashid_alphabet)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        try:
            return Hashid(value, salt=self.hashid_salt, min_length=self.hashid_min_length,
                          alphabet=self.hashid_alphabet, prefix=self.prefix, hashids=self._hashids)
        except ValueError:
            self.fail('invalid', value=data)


class HashidSerializerCharField(HashidSerializerMixin, fields.CharField):
    def to_representation(self, value):
        return str(value)

    def to_internal_value(self, data):
        hashid = super().to_internal_value(data)
        if isinstance(data, int) and not self.allow_int_lookup:
            self.fail('invalid_hashid', value=data)
        if isinstance(data, str) and not self.allow_int_lookup:
            # Make sure int lookups are not allowed, even if prefixed, unless the
            # given value is actually a hashid made up entirely of numbers.
            without_prefix = data[len(self.prefix):]
            if _is_int_representation(without_prefix) and without_prefix != hashid.hashid:
                self.fail('invalid_hashid', value=data)
        return hashid


class HashidSerializerIntegerField(HashidSerializerMixin, fields.IntegerField):
    def to_representation(self, value):
        return int(value)

