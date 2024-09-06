from django.contrib import admin

from file_processor_service.models import DriveFile


class DriveFileAdmin(admin.ModelAdmin):
    list_display = ('file_id', 'name', 'status', 'access', 'mime_type', 'progress', 'file_size')

admin.site.register(DriveFile, DriveFileAdmin)
