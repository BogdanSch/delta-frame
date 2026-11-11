import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator

class User(AbstractUser):
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('INSPECTOR', 'Inspector'),
        ('WORKER', 'Worker'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='WORKER')
    telegram_handle = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"


class Tool(models.Model):
    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('IN_USE', 'In Use'),
        ('MAINTENANCE', 'Maintenance'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    qr_code = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} [{self.qr_code}]"


class CameraAngle(models.Model):
    tool = models.ForeignKey(Tool, on_delete=models.CASCADE, related_name='camera_angles')
    name = models.CharField(max_length=100)
    target_distance_cm = models.FloatField(validators=[MinValueValidator(0.0)])
    target_lux = models.IntegerField(validators=[MinValueValidator(0)])
    tolerance_margin_cm = models.FloatField(validators=[MinValueValidator(0.0)], default=2.0)

    class Meta:
        # Ensures you don't create two "Front" angles for the same tool
        unique_together = ('tool', 'name')

    def __str__(self):
        return f"{self.tool.name} - {self.name}"


class InspectionSession(models.Model):
    SESSION_TYPE_CHOICES = [
        ('ISSUANCE', 'Issuance'),
        ('RETURN', 'Return'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending (Local)'),
        ('SYNCED', 'Synced to Cloud'),
        ('COMPLETED', 'Completed & Signed'),
    ]
    CONCLUSION_CHOICES = [
        ('CLEAN', 'Clean / No New Damage'),
        ('MINOR_WEAR', 'Minor Wear & Tear'),
        ('DAMAGED', 'Significant Damage Detected'),
        ('UNVERIFIED', 'Unverified / Pending AI Review'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tool = models.ForeignKey(Tool, on_delete=models.PROTECT, related_name='sessions')
    inspector = models.ForeignKey(User, on_delete=models.PROTECT, related_name='inspections_conducted')
    worker = models.ForeignKey(User, on_delete=models.PROTECT, related_name='tools_assigned', null=True, blank=True)
    
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    conclusion = models.CharField(max_length=20, choices=CONCLUSION_CHOICES, default='UNVERIFIED')
    
    # Not using auto_now_add so mobile/IoT clients can provide their offline timestamps
    created_at = models.DateTimeField() 

    def __str__(self):
        return f"{self.session_type} | {self.tool.name} ({self.created_at.strftime('%Y-%m-%d')})"


class PhotoRecord(models.Model):
    SOURCE_CHOICES = [
        ('IOT_STATION', 'IoT Station'),
        ('MOBILE_APP', 'Mobile App'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(InspectionSession, on_delete=models.CASCADE, related_name='photos')
    angle = models.ForeignKey(CameraAngle, on_delete=models.PROTECT, related_name='photos')
    image_file = models.ImageField(upload_to='inspection_photos/%Y/%m/')
    
    source_device = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    measured_distance_cm = models.FloatField(validators=[MinValueValidator(0.0)])
    measured_lux = models.IntegerField(validators=[MinValueValidator(0)])
    is_geometry_valid = models.BooleanField()
    timestamp = models.DateTimeField()

    def __str__(self):
        return f"{self.angle.name} for Session {self.session.id}"


class DefectAnalysis(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(InspectionSession, on_delete=models.CASCADE, related_name='defect_analyses')
    angle = models.ForeignKey(CameraAngle, on_delete=models.CASCADE, related_name='defect_analyses')
    
    before_photo = models.OneToOneField(PhotoRecord, on_delete=models.PROTECT, related_name='analysis_as_before')
    after_photo = models.OneToOneField(PhotoRecord, on_delete=models.PROTECT, related_name='analysis_as_after')
    
    difference_index = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    description = models.TextField(blank=True) 
    
    bounding_boxes = models.JSONField(default=list)
    is_approved_by_human = models.BooleanField(default=False)

    def __str__(self):
        return f"Analysis: {self.angle.name} (Diff: {self.difference_index:.2f})"