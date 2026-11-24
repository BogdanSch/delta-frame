from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CameraAngle, DefectAnalysis, InspectionSession, PhotoRecord, Tool, User

# Register your models here.
admin.site.register(User, UserAdmin)
admin.site.register(Tool)
admin.site.register(CameraAngle)
admin.site.register(InspectionSession)
admin.site.register(PhotoRecord)
admin.site.register(DefectAnalysis)