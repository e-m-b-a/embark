from functools import total_ordering

from hashids import Hashids


def _is_uint(candidate):
    """Returns whether a value is an unsigned integer."""
    return isinstance(candidate, int) and candidate >= 0


def _is_str(candidate):
    """Returns whether a value is a string."""
    return isinstance(candidate, str)


@total_ordering
class Hashid(object):
    def __init__(self, value, salt="", min_length=0, alphabet=Hashids.ALPHABET, prefix="", hashids=None):
        self._salt = salt
        self._min_length = min_length
        self._alphabet = alphabet
        self._prefix = str(prefix)

        # If hashids is provided, it's for optimization only, and should be initialized with the same salt, min_length
        # and alphabet, or else we will run into problems
        self._hashids = hashids or Hashids(salt=self._salt, min_length=self._min_length, alphabet=self._alphabet)
        if not self._valid_hashids_object():
            raise Exception("Invalid hashids.Hashids object")

        if value is None:
            raise ValueError("id must be a positive integer or a valid Hashid string")

        # Check if `value` is an integer and encode it.
        # This presumes hashids will only ever be strings, even if they are made up entirely of numbers
        if _is_uint(value):
            self._id = value
            self._hashid = self.encode(value)
        elif _is_str(value):
            # Verify that it begins with the prefix, which could be the default ""
            if value.startswith(self._prefix):
                value = value[len(self._prefix):]
            else:
                # Check if the given string is all numbers, and encode without requiring the prefix.
                # This is to maintain backwards compatibility, specifically being able to enter numbers in an admin.
                # If a hashid is typed in that happens to be all numbers, without the prefix, then it will be
                # interpreted as an integer and encoded (again).
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    raise ValueError("value must begin with prefix {}".format(self._prefix))

            # Check if this string is a valid hashid, even if it's made up entirely of numbers
            _id = self.decode(value)
            if _id is None:
                # The given value is not a hashids string, so see if it's a valid string representation of an integer
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    raise ValueError("value must be a positive integer or a valid Hashid string")

                # Make sure it's positive
                if not _is_uint(value):
                    raise ValueError("value must be a positive integer")

                # We can use it as-is
                self._id = value
                self._hashid = self.encode(value)
            else:
                # This is a valid hashid
                self._id = _id
                self._hashid = value
        elif isinstance(value, int) and value < 0:
            raise ValueError("value must be a positive integer")
        else:
            raise ValueError("value must be a positive integer or a valid Hashid string")

    @property
    def id(self):
        return self._id

    @property
    def hashid(self):
        return self._hashid

    @property
    def prefix(self):
        return self._prefix

    @property
    def hashids(self):
        return self._hashids

    def encode(self, id):
        return self._hashids.encode(id)

    def decode(self, hashid):
        ret = self._hashids.decode(hashid)
        if len(ret) == 1:
            return ret[0]
        else:
            return None

    def _valid_hashids_object(self):
        # The hashids.Hashids class randomizes the alphabet and pulls out separators and guards, thus not being
        # reversible. So all we can test is that the length of the alphabet, separators and guards are equal to the
        # original alphabet we gave it. We could also check that all of the characters we gave it are present, but that
        # seems excessive... this test will catch most errors.
        return self._salt == self._hashids._salt \
            and self._min_length == self._hashids._min_length \
            and len(self._alphabet) == len(self._hashids._alphabet + self._hashids._separators + self._hashids._guards)

    def __repr__(self):
        return "Hashid({}): {}".format(self._id, str(self))

    def __str__(self):
        return self._prefix + self._hashid

    def __int__(self):
        return self._id

    def __long__(self):
        return int(self._id)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (
                self._id == other._id and
                self._hashid == other._hashid and
                self._prefix == other._prefix
            )
        if isinstance(other, str):
            return str(self) == other
        if isinstance(other, int):
            return int(self) == other
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, self.__class__):
            return self._id < other._id
        if isinstance(other, type(self._id)):
            return self._id < other
        return NotImplemented

    def __len__(self):
        return len(str(self))

    def __hash__(self):
        return hash(str(self))

    def __reduce__(self):
        return (self.__class__, (self._id, self._salt, self._min_length, self._alphabet, self._prefix, None))
