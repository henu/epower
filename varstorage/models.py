from django.db import models


class Variable(models.Model):
    name = models.CharField(max_length=100, primary_key=True)
    value = models.JSONField()

    def __str__(self):
        return self.name
