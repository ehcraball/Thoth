from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .forms import MyUserCreationForm

# Register your models here.

from .models import Room, Topic, Message, User

# admin.site.register(User)
admin.site.register(Room)
admin.site.register(Topic)
admin.site.register(Message)

class CustomUserAdmin(UserAdmin):
    add_form = MyUserCreationForm
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role',)}),
    )

admin.site.register(User, CustomUserAdmin)