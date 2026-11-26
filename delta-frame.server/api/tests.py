import shutil
import tempfile

from datetime import timedelta
from uuid import uuid4
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from api.models import CameraAngle, DefectAnalysis, InspectionSession, PhotoRecord, Tool, User
from api.services import camera_angles, defects, photos, sessions, tools, users

class UserServiceTests(TestCase):
    def test_create_list_update_and_deactivate_user(self):
        inspector = users.create_user(
            username="InspectorOne",
            password="secret",
            email="insp@example.com",
            role="INSPECTOR",
            first_name="Alex",
        )
        worker = users.create_user(
            username="worker_one",
            password="secret",
            role="WORKER",
        )

        self.assertTrue(inspector.check_password("secret"))
        self.assertEqual(list(users.list_users(role="INSPECTOR")), [inspector])
        self.assertEqual(
            list(users.list_users()),
            [inspector, worker],
        )
        self.assertEqual(users.get_user_by_id(inspector.id), inspector)

        with self.assertRaises(ValidationError) as ctx:
            users.create_user(username="inspectorone", password="x", role="WORKER")
        self.assertEqual(ctx.exception.code, "duplicate_username")

        with self.assertRaises(ValidationError) as ctx:
            users.create_user(username="badrole", password="x", role="SUPER")
        self.assertEqual(ctx.exception.code, "invalid_role")

        updated = users.update_user(
            worker,
            email="worker@example.com",
            password="newpassword",
            role="INSPECTOR",
        )
        self.assertEqual(updated.email, "worker@example.com")
        self.assertEqual(updated.role, "INSPECTOR")
        self.assertTrue(updated.check_password("newpassword"))

        deactivated = users.deactivate_user(worker)
        self.assertFalse(deactivated.is_active)
        self.assertEqual(list(users.list_users(is_active=True)), [inspector])
        self.assertEqual(list(users.list_users(is_active=False)), [worker])

class ToolAndCameraAngleServiceTests(TestCase):
    def setUp(self):
        self.inspector = users.create_user(
            username="insp1", password="pw", role="INSPECTOR"
        )

    def test_tool_crud_and_qr_lookup(self):
        tool = tools.create_tool(name="  Torque Wrench  ", description="1/2 inch")
        self.assertEqual(tool.name, "Torque Wrench")
        self.assertTrue(tool.qr_code.startswith("DF-"))

        fetched = tools.get_tool_by_qr(f"  {tool.qr_code.lower()}  ")
        self.assertEqual(fetched.id, tool.id)
        self.assertEqual(tools.get_tool_by_id(tool.id).id, tool.id)
        self.assertEqual(list(tools.list_tools(status="AVAILABLE")), [tool])

        original_qr = tool.qr_code
        updated = tools.update_tool(
            tool, qr_code="HACKED", name="  Calibrated Wrench ", status="IN_USE"
        )
        self.assertEqual(updated.qr_code, original_qr)
        self.assertEqual(updated.name, "Calibrated Wrench")
        self.assertEqual(updated.status, "IN_USE")

        with self.assertRaises(ValidationError) as ctx:
            tools.delete_tool(updated)
        self.assertEqual(ctx.exception.code, "tool_in_use")

        tools.update_tool(updated, status="AVAILABLE")
        InspectionSession.objects.create(
            tool=updated,
            inspector=self.inspector,
            session_type="ISSUANCE",
            created_at=timezone.now(),
        )
        with self.assertRaises(ValidationError) as ctx:
            tools.delete_tool(updated)
        self.assertEqual(ctx.exception.code, "tool_has_history")

        deletable = tools.create_tool(name="Temp Tool")
        tools.delete_tool(deletable)
        self.assertFalse(Tool.objects.filter(id=deletable.id).exists())

    def test_camera_angle_crud_and_uniqueness(self):
        tool = tools.create_tool(name="Drill")
        front = camera_angles.create_camera_angle(
            tool=tool,
            name=" Front ",
            target_distance_cm=25.0,
            target_lux=400,
        )
        back = camera_angles.create_camera_angle(
            tool=tool,
            name="Back",
            target_distance_cm=25.0,
            target_lux=400,
        )

        self.assertEqual(
            list(camera_angles.list_angles_for_tool(tool.id)),
            [back, front],
        )
        self.assertEqual(camera_angles.get_angle_by_id(front.id).tool_id, tool.id)

        with self.assertRaises(ValidationError) as ctx:
            camera_angles.create_camera_angle(
                tool=tool, name="front", target_distance_cm=20.0, target_lux=300
            )
        self.assertEqual(ctx.exception.code, "duplicate_angle")

        with self.assertRaises(ValidationError) as ctx:
            camera_angles.update_camera_angle(front, name="BACK")
        self.assertEqual(ctx.exception.code, "duplicate_angle")

        updated = camera_angles.update_camera_angle(front, target_lux=500)
        self.assertEqual(updated.target_lux, 500)

        camera_angles.delete_camera_angle(back)
        self.assertFalse(CameraAngle.objects.filter(id=back.id).exists())

class SessionPhotoAndDefectServiceTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_dir)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(shutil.rmtree, self.media_dir, True)

        self.inspector = users.create_user(
            username="insp", password="pw", role="INSPECTOR"
        )
        self.worker = users.create_user(
            username="work", password="pw", role="WORKER"
        )
        self.tool = tools.create_tool(name="Hammer Drill")
        self.angle = camera_angles.create_camera_angle(
            tool=self.tool,
            name="Front",
            target_distance_cm=25.0,
            target_lux=400,
            tolerance_margin_cm=2.5,
        )
        self.other_tool = tools.create_tool(name="Other Tool")
        self.other_angle = camera_angles.create_camera_angle(
            tool=self.other_tool,
            name="Front",
            target_distance_cm=25.0,
            target_lux=400,
        )

    def _dummy_image(self, name="frame.jpg"):
        return SimpleUploadedFile(name, b"fake-jpeg-bytes", content_type="image/jpeg")

    def test_session_sync_complete_and_delete_guards(self):
        with self.assertRaises(ValidationError) as ctx:
            sessions.create_or_sync_session(
                tool=self.tool,
                inspector=self.worker,
                session_type="ISSUANCE",
            )
        self.assertEqual(ctx.exception.code, "invalid_inspector_role")

        client_id = uuid4()
        client_ts = timezone.now() - timedelta(minutes=10)
        issuance, created = sessions.create_or_sync_session(
            session_id=client_id,
            tool=self.tool,
            inspector=self.inspector,
            worker=self.worker,
            session_type="ISSUANCE",
            created_at=client_ts,
        )
        self.assertTrue(created)
        self.assertEqual(issuance.status, "SYNCED")
        self.assertEqual(issuance.created_at, client_ts)

        # Idempotent re-sync of the same session_id
        issuance_again, created_again = sessions.create_or_sync_session(
            session_id=client_id,
            tool=self.tool,
            inspector=self.inspector,
            worker=self.worker,
            session_type="ISSUANCE",
            created_at=client_ts,
        )
        self.assertFalse(created_again)
        self.assertEqual(issuance_again.id, client_id)

        with self.assertRaises(ValidationError) as ctx:
            sessions.delete_session(issuance)
        self.assertEqual(ctx.exception.code, "session_locked")

        completed_issuance = sessions.complete_session(issuance, conclusion="CLEAN")
        self.tool.refresh_from_db()
        self.assertEqual(completed_issuance.status, "COMPLETED")
        self.assertEqual(self.tool.status, "IN_USE")

        with self.assertRaises(ValidationError) as ctx:
            sessions.update_session(completed_issuance, conclusion="DAMAGED")
        self.assertEqual(ctx.exception.code, "session_locked")

        # Cannot start a new ISSUANCE while tool is IN_USE
        with self.assertRaises(ValidationError) as ctx:
            sessions.create_or_sync_session(
                tool=self.tool,
                inspector=self.inspector,
                session_type="ISSUANCE",
            )
        self.assertEqual(ctx.exception.code, "tool_unavailable")

        # RETURN -> DAMAGED -> MAINTENANCE
        ret_session, _ = sessions.create_or_sync_session(
            tool=self.tool,
            inspector=self.inspector,
            worker=self.worker,
            session_type="RETURN",
        )
        sessions.complete_session(ret_session, conclusion="DAMAGED")
        self.tool.refresh_from_db()
        self.assertEqual(self.tool.status, "MAINTENANCE")

        # PENDING session can be deleted
        pending = InspectionSession.objects.create(
            tool=self.other_tool,
            inspector=self.inspector,
            session_type="ISSUANCE",
            status="PENDING",
            created_at=timezone.now(),
        )
        sessions.delete_session(pending)
        self.assertFalse(InspectionSession.objects.filter(id=pending.id).exists())

    def test_photo_recording_pairing_and_defect_lifecycle(self):
        issuance, _ = sessions.create_or_sync_session(
            tool=self.tool,
            inspector=self.inspector,
            worker=self.worker,
            session_type="ISSUANCE",
        )

        with self.assertRaises(ValidationError) as ctx:
            photos.record_photo(
                session=issuance,
                angle=self.other_angle,
                image_file=self._dummy_image(),
                source_device="IOT",
                measured_distance_cm=25.0,
                measured_lux=400,
            )
        self.assertEqual(ctx.exception.code, "angle_tool_mismatch")

        before_photo = photos.record_photo(
            session=issuance,
            angle=self.angle,
            image_file=self._dummy_image("before.jpg"),
            source_device="IOT",
            measured_distance_cm=26.5,
            measured_lux=410,
        )
        self.assertTrue(before_photo.is_geometry_valid)

        # Re-upload replaces cleanly without violating unique_session_angle_photo
        before_photo_2 = photos.record_photo(
            session=issuance,
            angle=self.angle,
            image_file=self._dummy_image("before2.jpg"),
            source_device="IOT",
            measured_distance_cm=25.0,
            measured_lux=400,
        )
        self.assertEqual(before_photo_2.id, before_photo.id)
        self.assertEqual(
            list(photos.list_photos_for_session(issuance.id)), [before_photo_2]
        )

        sessions.complete_session(issuance, conclusion="CLEAN")

        ret_session, _ = sessions.create_or_sync_session(
            tool=self.tool,
            inspector=self.inspector,
            worker=self.worker,
            session_type="RETURN",
        )
        after_photo = photos.record_photo(
            session=ret_session,
            angle=self.angle,
            image_file=self._dummy_image("after.jpg"),
            source_device="MOBILE",
            measured_distance_cm=32.0,
            measured_lux=390,
        )
        self.assertFalse(after_photo.is_geometry_valid)

        # RETURN photo automatically paired with issuance baseline
        analysis = defects.list_defects(session_id=ret_session.id).get()
        self.assertEqual(analysis.before_photo_id, before_photo_2.id)
        self.assertEqual(analysis.after_photo_id, after_photo.id)

        # Referenced photo/angle cannot be deleted
        with self.assertRaises(ValidationError) as ctx:
            photos.delete_photo(before_photo_2)
        self.assertEqual(ctx.exception.code, "photo_in_use")

        with self.assertRaises(ValidationError) as ctx:
            camera_angles.delete_camera_angle(self.angle)
        self.assertEqual(ctx.exception.code, "angle_in_use")

        # Update CV/LLM results and approve
        updated = defects.update_analysis_results(
            analysis,
            difference_index=0.42,
            description="Scratch on housing",
            bounding_boxes=[{"x": 10, "y": 20, "w": 30, "h": 40}],
        )
        self.assertEqual(updated.difference_index, 0.42)

        approved = defects.approve_defect_analysis(
            updated, description="Confirmed scratch on housing"
        )
        self.assertTrue(approved.is_approved_by_human)
        self.assertEqual(approved.description, "Confirmed scratch on housing")

        with self.assertRaises(ValidationError) as ctx:
            defects.delete_defect_analysis(approved)
        self.assertEqual(ctx.exception.code, "analysis_approved")