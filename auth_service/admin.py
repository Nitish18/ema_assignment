from django.contrib import admin

# Register your models here.


from auth_service.models import UserCredentials


class UserCredentialsAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'refresh_token', 'token_uri', 'client_id', 'client_secret', 'scopes')

admin.site.register(UserCredentials, UserCredentialsAdmin)
