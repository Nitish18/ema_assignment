from django.contrib import admin

# Register your models here.

from .models import DriveWatch

class DriveWatchAdmin(admin.ModelAdmin):
    list_display = ('user', 'channel_id', 'file_id', 'resource_id')


admin.site.register(DriveWatch, DriveWatchAdmin)
