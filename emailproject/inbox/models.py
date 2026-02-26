from django.db import models
from django_ckeditor_5.fields import CKEditor5Field


class CompanyInfo(models.Model):
    content = CKEditor5Field("Şirkət məlumatları", config_name="default")

    class Meta:
        verbose_name = "Şirkət məlumatı"
        verbose_name_plural = "Şirkət məlumatları"

    def __str__(self):
        return "Şirkət məlumatı"


class IncomingEmail(models.Model):
    sender = models.EmailField()
    subject = models.CharField(max_length=500)
    body = models.TextField()
    department = models.CharField(max_length=100, blank=True, default='')
    reply_text = models.TextField(blank=True, default='')
    is_replied = models.BooleanField(default=False)
    received_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        ordering = ['-received_at']

    def __str__(self):
        return self.subject
