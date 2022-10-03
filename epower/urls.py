from django.contrib import admin
from django.urls import include, path

import frontend.views


urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/v1/', include('api.urls')),

    path('', frontend.views.main, name='main')
]
