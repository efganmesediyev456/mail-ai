from django.urls import path
from . import views

urlpatterns = [
    path("", views.email_list, name="email_list"),
    path("<int:pk>/", views.email_detail, name="email_detail"),
    path("fetch/", views.fetch_emails, name="fetch_emails"),
    path("<int:pk>/reply/", views.reply_email, name="reply_email"),
]
