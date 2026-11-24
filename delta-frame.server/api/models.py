import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.constraints import UniqueConstraint

class User(AbstractUser):
    ROLE_CHOICES: list[tuple[str, str]] = [
        ('ADMIN', 'Admin'),
        ('INSPECTOR', 'Inspector'),
        ('WORKER', 'Worker'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='WORKER')

    def __str__(self):
        return f"{self.username} ({self.role})"

class Tool(models.Model):
    STATUS_CHOICES: list[tuple[str, str]] = [
        ('AVAILABLE', 'Available'),
        ('IN_USE', 'In Use'),
        ('MAINTENANCE', 'Maintenance'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    qr_code = models.CharField(max_length=100, unique=True, db_index=True, null=False, blank=True, editable=False)
    name = models.CharField(max_length=255, null=False)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs) -> None:
        self.qr_code = f"DF-{self.id.hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} [{self.qr_code}]"

class CameraAngle(models.Model):
    tool = models.ForeignKey(Tool, on_delete=models.CASCADE, related_name='camera_angles')
    name = models.CharField(max_length=100, null=False)
    target_distance_cm = models.FloatField(validators=[MinValueValidator(0.0)])
    target_lux = models.IntegerField(validators=[MinValueValidator(0)])
    tolerance_margin_cm = models.FloatField(validators=[MinValueValidator(0.0)], default=2.5)

    class Meta:
        unique_together = ('tool', 'name')

    def __str__(self):
        return f"{self.tool.name} - {self.name}"

class InspectionSession(models.Model):
    SESSION_TYPE_CHOICES: list[tuple[str, str]] = [
        ('ISSUANCE', 'Issuance'),
        ('RETURN', 'Return'),
    ]
    STATUS_CHOICES: list[tuple[str, str]] = [
        ('PENDING', 'Pending (Local)'),
        ('SYNCED', 'Synced'),
        ('COMPLETED', 'Completed'),
    ]
    CONCLUSION_CHOICES: list[tuple[str, str]] = [
        ('CLEAN', 'Clean'),
        ('MINOR_WEAR', 'Minor Wear'),
        ('DAMAGED', 'Damaged'),
        ('UNVERIFIED', 'Unverified'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tool = models.ForeignKey(Tool, on_delete=models.PROTECT, related_name='inspection_sessions')
    inspector = models.ForeignKey(User, on_delete=models.PROTECT, related_name='inspections_conducted')
    worker = models.ForeignKey(User, on_delete=models.PROTECT, related_name='tools_assigned', null=True, blank=True)
    
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    conclusion = models.CharField(max_length=20, choices=CONCLUSION_CHOICES, default='UNVERIFIED')
    created_at = models.DateTimeField() 

    def __str__(self):
        return f"{self.session_type} | {self.tool.name} ({self.created_at.strftime('%Y-%m-%d')})"

class PhotoRecord(models.Model):
    SOURCE_CHOICES: list[tuple[str, str]] = [
        ('IOT', 'IoT'),
        ('MOBILE', 'Mobile'),
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

    class Meta:
        constraints = [
            UniqueConstraint(fields=['session', 'angle'], name='unique_session_angle_photo'),
        ]

    def __str__(self):
        return f"{self.angle.name} for Session {self.session.id}"

class DefectAnalysis(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(InspectionSession, on_delete=models.CASCADE, related_name='defect_analyses')
    angle = models.ForeignKey(CameraAngle, on_delete=models.CASCADE, related_name='defect_analyses')
    
    before_photo = models.ForeignKey(PhotoRecord, on_delete=models.PROTECT, related_name='analyses_as_before')
    after_photo = models.OneToOneField(PhotoRecord, on_delete=models.PROTECT, related_name='analysis_as_after')
    
    difference_index = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    description = models.TextField(blank=True) 
    
    bounding_boxes = models.JSONField(default=list)
    is_approved_by_human = models.BooleanField(default=False)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['session', 'angle'], name='unique_session_angle_defect'),
        ]

    def __str__(self):
        return f"Analysis: {self.angle.name} (Diff: {self.difference_index:.2f})"