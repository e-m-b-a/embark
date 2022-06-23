from django.core.validators import MaxValueValidator, MinValueValidator


class HashidMaxValueValidator(MaxValueValidator):
    def __init__(self, hashid_field, limit_value, message=None):
        self.hashid_field = hashid_field
        super().__init__(limit_value, message)

    def clean(self, x):
        return self.hashid_field.get_prep_value(x)


class HashidMinValueValidator(MinValueValidator):
    def __init__(self, hashid_field, limit_value, message=None):
        self.hashid_field = hashid_field
        super().__init__(limit_value, message)

    def clean(self, x):
        return self.hashid_field.get_prep_value(x)
