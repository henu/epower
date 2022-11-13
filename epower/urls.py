from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

import frontend.views


urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/v1/', include('api.urls')),

    path('login', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('', frontend.views.main, name='main'),
]
