from django.db import models

class Naukri(models.Model):
    title = models.CharField(max_length=255)
    url = models.URLField(unique=True)
    company = models.CharField(max_length=255)
    experience = models.CharField(max_length=255)
    salary = models.CharField(max_length=255, null=True, blank=True)
    location = models.CharField(max_length=255)
    posted_date = models.CharField(max_length=10)

    def __str__(self):
        return self.title
