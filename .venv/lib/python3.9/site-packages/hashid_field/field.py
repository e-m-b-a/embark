from django import forms
from django.core import exceptions, checks
from django.core import validators as django_validators
from django.db import models
from django.db.models import Field
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.contrib.admin import widgets as admin_widgets
from hashids import Hashids

from .lookups import HashidExactLookup, HashidIterableLookup
from .lookups import HashidGreaterThan, HashidGreaterThanOrEqual, HashidLessThan, HashidLessThanOrEqual
from .descriptor import HashidDescriptor
from .hashid import Hashid
from .conf import settings
from .validators import HashidMaxValueValidator, HashidMinValueValidator


def _alphabet_unique_len(alphabet):
    return len([x for i, x in enumerate(alphabet) if alphabet.index(x) == i])


class HashidFieldMixin(object):
    default_error_messages = {
        'invalid': _("'%(value)s' value must be a positive integer or a valid Hashids string."),
        'invalid_hashid': _("'%(value)s' value must be a valid Hashids string."),
    }
    exact_lookups = ('exact', 'iexact', 'contains', 'icontains')
    iterable_lookups = ('in',)
    passthrough_lookups = ('isnull',)
    comparison_lookups = {
        'gt': HashidGreaterThan,
        'gte': HashidGreaterThanOrEqual,
        'lt': HashidLessThan,
        'lte': HashidLessThanOrEqual,
    }

    def __init__(self, salt=settings.HASHID_FIELD_SALT,
                 min_length=settings.HASHID_FIELD_MIN_LENGTH,
                 alphabet=settings.HASHID_FIELD_ALPHABET,
                 allow_int_lookup=settings.HASHID_FIELD_ALLOW_INT_LOOKUP,
                 enable_hashid_object=settings.HASHID_FIELD_ENABLE_HASHID_OBJECT,
                 enable_descriptor=settings.HASHID_FIELD_ENABLE_DESCRIPTOR,
                 prefix="", *args, **kwargs):
        self.salt = salt
        self.min_length = min_length
        self.alphabet = alphabet
        if _alphabet_unique_len(self.alphabet) < 16:
            raise exceptions.ImproperlyConfigured("'alphabet' must contain a minimum of 16 unique characters")
        self._hashids = Hashids(salt=self.salt, min_length=self.min_length, alphabet=self.alphabet)
        self.allow_int_lookup = allow_int_lookup
        self.enable_hashid_object = enable_hashid_object
        self.enable_descriptor = enable_descriptor
        self.prefix = prefix
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['min_length'] = self.min_length
        kwargs['alphabet'] = self.alphabet
        kwargs['prefix'] = self.prefix
        return name, path, args, kwargs

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(self._check_alphabet_min_length())
        errors.extend(self._check_salt_is_set())
        return errors

    def _check_alphabet_min_length(self):
        if _alphabet_unique_len(self.alphabet) < 16:
            return [
                checks.Error(
                    "'alphabet' must contain a minimum of 16 unique characters",
                    hint="Add more unique characters to custom 'alphabet'",
                    obj=self,
                    id='HashidField.E001',
                )
            ]
        return []

    def _check_salt_is_set(self):
        if self.salt is None or self.salt == "":
            return [
                checks.Warning(
                    "'salt' is not set",
                    hint="Pass a salt value in your field or set settings.HASHID_FIELD_SALT",
                    obj=self,
                    id="HashidField.W001",
                )
            ]
        return []

    @cached_property
    def validators(self):
        if self.enable_hashid_object:
            return super().validators
        else:
            # IntegerField will add min and max validators depending on the database we're connecting to, so we need
            # to override them with our own validator that knows how to `clean` the value before doing the check.
            validators_ = super().validators
            validators = []
            for validator_ in validators_:
                if isinstance(validator_, django_validators.MaxValueValidator):
                    validators.append(HashidMaxValueValidator(self, validator_.limit_value, validator_.message))
                elif isinstance(validator_, django_validators.MinValueValidator):
                    validators.append(HashidMinValueValidator(self, validator_.limit_value, validator_.message))
                else:
                    validators.append(validator_)
            return validators

    def encode_id(self, id):
        hashid = self.get_hashid(id)
        if self.enable_hashid_object:
            return hashid
        else:
            return str(hashid)

    def get_hashid(self, id):
        return Hashid(id, salt=self.salt, min_length=self.min_length, alphabet=self.alphabet,
                      prefix=self.prefix, hashids=self._hashids)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return self.encode_id(value)

    def get_lookup(self, lookup_name):
        if lookup_name in self.exact_lookups:
            return HashidExactLookup
        if lookup_name in self.iterable_lookups:
            return HashidIterableLookup
        if lookup_name in self.comparison_lookups:
            return self.comparison_lookups[lookup_name]
        if lookup_name in self.passthrough_lookups:
            return super().get_lookup(lookup_name)
        return None  # Otherwise, we don't allow lookups of this type

    def to_python(self, value):
        if isinstance(value, Hashid):
            return value
        if value is None:
            return value
        try:
            hashid = self.encode_id(value)
        except ValueError:
            raise exceptions.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )
        return hashid

    def get_prep_value(self, value):
        if value is None or value == '':
            return None
        if isinstance(value, Hashid):
            return value.id
        try:
            hashid = self.get_hashid(value)
        except ValueError:
            raise ValueError(self.error_messages['invalid'] % {'value': value})
        return hashid.id

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        # if callable(self.prefix):
        #     self.prefix = self.prefix(field_instance=self, model_class=cls, field_name=name, **kwargs)
        if self.enable_descriptor:
            descriptor = HashidDescriptor(field_name=self.attname, salt=self.salt, min_length=self.min_length,
                                          alphabet=self.alphabet, prefix=self.prefix, hashids=self._hashids,
                                          enable_hashid_object=self.enable_hashid_object)
            setattr(cls, self.attname, descriptor)


class HashidCharFieldMixin:
    def formfield(self, **kwargs):
        defaults = {'form_class': forms.CharField}
        defaults.update(kwargs)
        if defaults.get('widget') == admin_widgets.AdminIntegerFieldWidget:
            defaults['widget'] = admin_widgets.AdminTextInputWidget
        if defaults.get('widget') == admin_widgets.AdminBigIntegerFieldWidget:
            defaults['widget'] = admin_widgets.AdminTextInputWidget
        # noinspection PyCallByClass,PyTypeChecker
        return Field.formfield(self, **defaults)


class HashidField(HashidFieldMixin, HashidCharFieldMixin, models.IntegerField):
    description = "A Hashids obscured IntegerField"


class BigHashidField(HashidFieldMixin, HashidCharFieldMixin, models.BigIntegerField):
    description = "A Hashids obscured BigIntegerField"

    def __init__(self, min_length=settings.HASHID_FIELD_BIG_MIN_LENGTH, *args, **kwargs):
        super().__init__(min_length=min_length, *args, **kwargs)


class HashidAutoField(HashidFieldMixin, models.AutoField):
    description = "A Hashids obscured AutoField"


class BigHashidAutoField(HashidFieldMixin, models.AutoField):
    # This inherits from AutoField instead of BigAutoField so that DEFAULT_AUTO_FIELD doesn't throw an error
    description = "A Hashids obscured BigAutoField"

    def get_internal_type(self):
        return 'BigAutoField'

    def rel_db_type(self, connection):
        return models.BigIntegerField().db_type(connection=connection)

    def __init__(self, min_length=settings.HASHID_FIELD_BIG_MIN_LENGTH, *args, **kwargs):
        super().__init__(min_length=min_length, *args, **kwargs)


# Monkey patch Django REST Framework, if it's installed, to throw exceptions if fields aren't explicitly defined in
# ModelSerializers. Not doing so can lead to hard-to-debug behavior.
try:
    from rest_framework.serializers import ModelSerializer
    from hashid_field.rest import UnconfiguredHashidSerialField

    ModelSerializer.serializer_field_mapping[HashidField] = UnconfiguredHashidSerialField
    ModelSerializer.serializer_field_mapping[BigHashidField] = UnconfiguredHashidSerialField
    ModelSerializer.serializer_field_mapping[HashidAutoField] = UnconfiguredHashidSerialField
    ModelSerializer.serializer_field_mapping[BigHashidAutoField] = UnconfiguredHashidSerialField
except ImportError:
    pass
