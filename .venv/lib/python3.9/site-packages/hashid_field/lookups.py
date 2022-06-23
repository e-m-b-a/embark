import itertools

from django.db.models.lookups import Lookup, GreaterThan, GreaterThanOrEqual, LessThan, LessThanOrEqual
from django.utils.datastructures import OrderedSet
from django.core.exceptions import EmptyResultSet

from .hashid import Hashid
from .conf import settings


def _is_int_representation(number):
    """Returns whether a value is an integer or a string representation of an integer."""
    try:
        int(number)
    except ValueError:
        return False
    else:
        return True


def get_id_for_hashid_field(field, value):
    if isinstance(value, Hashid):
        return value.id
    try:
        hashid = field.get_hashid(value)
    except ValueError:
        raise ValueError(field.error_messages['invalid'] % {'value': value})
    if isinstance(value, int) and not field.allow_int_lookup:
        raise ValueError(field.error_messages['invalid_hashid'] % {'value': value})
    if isinstance(value, str) and not field.allow_int_lookup:
        # Make sure int lookups are not allowed, even if prefixed, unless the
        # given value is actually a hashid made up entirely of numbers.
        without_prefix = value[len(field.prefix):]
        if _is_int_representation(without_prefix) and without_prefix != hashid.hashid:
            raise ValueError(field.error_messages['invalid_hashid'] % {'value': value})
    return hashid.id


# Most of this code is derived or copied from Django. (django/db/models/lookups.py)
# It has been included here to increase compatibility of this module with Django versions 1.11, 2.2 and 3.0.
# Django is Copyright (c) Django Software Foundation and individual contributors.
# Please see https://github.com/django/django/blob/master/LICENSE

class HashidFieldGetDbPrepValueMixin:
    get_db_prep_lookup_value_is_iterable = False

    def get_db_prep_lookup(self, value, connection):
        # There are two modes this method can be called in... a single value or an iterable of values (usually a set)
        # For a single value, just try to process it, then return the value, or else throw EmptyResultSet
        # For multiple values, process each one in turn. If any of them are invalid, throw it away. If all are invalid,
        # throw EmptyResultSet
        # For relational fields, use the 'field' attribute of the output_field
        field = getattr(self.lhs.output_field, 'field', self.lhs.output_field)
        if self.get_db_prep_lookup_value_is_iterable:
            lookup_ids = []
            for val in value:
                try:
                    lookup_id = get_id_for_hashid_field(field, val)
                except ValueError:
                    if settings.HASHID_FIELD_LOOKUP_EXCEPTION:
                        raise
                    # Ignore this value
                    pass
                else:
                    lookup_ids.append(lookup_id)
            if len(lookup_ids) == 0:
                raise EmptyResultSet
            return '%s', lookup_ids
        else:
            try:
                lookup_id = get_id_for_hashid_field(field, value)
            except ValueError:
                if settings.HASHID_FIELD_LOOKUP_EXCEPTION:
                    raise
                raise EmptyResultSet
            return '%s', [lookup_id]


class HashidExactLookup(HashidFieldGetDbPrepValueMixin, Lookup):
    prepare_rhs = False

    def as_sql(self, compiler, connection):
        lhs_sql, params = self.process_lhs(compiler, connection)
        rhs_sql, rhs_params = self.process_rhs(compiler, connection)
        params.extend(rhs_params)
        rhs_sql = self.get_rhs_op(connection, rhs_sql)
        return '%s %s' % (lhs_sql, rhs_sql), params

    def get_rhs_op(self, connection, rhs):
        return "= %s" % rhs


class HashidIterableLookup(HashidExactLookup):
    # This is an amalgamation of Django's FieldGetDbPrepValueIterableMixin and In lookup to allow support of both
    # iterables (lists, tuples) and subqueries.
    get_db_prep_lookup_value_is_iterable = True

    def get_prep_lookup(self):
        if hasattr(self.rhs, 'resolve_expression'):
            return self.rhs
        prepared_values = []
        if hasattr(self.rhs, '_prepare'):
            # A subquery is like an iterable but its items shouldn't be
            # prepared independently.
            return self.rhs._prepare(self.lhs.output_field)
        for rhs_value in self.rhs:
            if hasattr(rhs_value, 'resolve_expression'):
                # An expression will be handled by the database but can coexist
                # alongside real values.
                pass
            prepared_values.append(rhs_value)
        return prepared_values

    def process_rhs(self, compiler, connection):
        db_rhs = getattr(self.rhs, '_db', None)
        if db_rhs is not None and db_rhs != connection.alias:
            raise ValueError(
                "Subqueries aren't allowed across different databases. Force "
                "the inner query to be evaluated using `list(inner_query)`."
            )

        if self.rhs_is_direct_value():
            try:
                rhs = OrderedSet(self.rhs)
            except TypeError:  # Unhashable items in self.rhs
                rhs = self.rhs

            if not rhs:
                raise EmptyResultSet

            # rhs should be an iterable; use batch_process_rhs() to
            # prepare/transform those values.
            sqls, sqls_params = self.batch_process_rhs(compiler, connection, rhs)
            placeholder = '(' + ', '.join(sqls) + ')'
            return (placeholder, sqls_params)
        else:
            return super().process_rhs(compiler, connection)

    def resolve_expression_parameter(self, compiler, connection, sql, param):
        params = [param]
        if hasattr(param, 'resolve_expression'):
            param = param.resolve_expression(compiler.query)
        if hasattr(param, 'as_sql'):
            sql, params = param.as_sql(compiler, connection)
        return sql, params

    def batch_process_rhs(self, compiler, connection, rhs=None):
        pre_processed = super().batch_process_rhs(compiler, connection, rhs)
        # The params list may contain expressions which compile to a
        # sql/param pair. Zip them to get sql and param pairs that refer to the
        # same argument and attempt to replace them with the result of
        # compiling the param step.
        sql, params = zip(*(
            self.resolve_expression_parameter(compiler, connection, sql, param)
            for sql, param in zip(*pre_processed)
        ))
        params = itertools.chain.from_iterable(params)
        return sql, tuple(params)

    def get_rhs_op(self, connection, rhs):
        return 'IN %s' % rhs


class HashidGreaterThan(HashidFieldGetDbPrepValueMixin, GreaterThan):
    prepare_rhs = False


class HashidGreaterThanOrEqual(HashidFieldGetDbPrepValueMixin, GreaterThanOrEqual):
    prepare_rhs = False


class HashidLessThan(HashidFieldGetDbPrepValueMixin, LessThan):
    prepare_rhs = False


class HashidLessThanOrEqual(HashidFieldGetDbPrepValueMixin, LessThanOrEqual):
    prepare_rhs = False
