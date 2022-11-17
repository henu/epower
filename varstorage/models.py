from django.db import models


class VariableManager(models.Manager):

    def get_value(self, name):
        var = self.get_queryset().filter(name=name).first()
        if not var:
            return None
        return var.value


class Variable(models.Model):
    name = models.CharField(max_length=100, primary_key=True)
    value = models.JSONField()

    objects = VariableManager()

    def __str__(self):
        return self.name
