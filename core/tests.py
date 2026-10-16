from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone
from core.audit import log
from core.models import AuditLog
from dispatch.services import shipping_clearance
from materials.models import RawMaterialLot
from materials.services import reject_lot
from plant.models import Gauge, Machine, MachinePMCheck, Part, Site
from production.models import JobTraveler, Operation
from production.services import approve_first_piece, finish_operation, start_operation, increment_counter
from quality import services as q
from quality.models import DefectPhoto, Inspection, InspectionTemplate, TemplateField

U = get_user_model()


class Base(TestCase):
    def setUp(self):
        mk = lambda n, r: U.objects.create_user(n, password="x", role=r, email=f"{n}@x.com")
        self.ins, self.sup, self.qm, self.opr, self.pm = mk("ins", "INS"), mk("sup", "SUP"), mk("qm", "QM"), mk("opr", "OPR"), mk("pm", "PM")
        site = Site.objects.create(name="Main")
        self.machine = Machine.objects.create(site=site, code="CNC-04")
        MachinePMCheck.objects.create(machine=self.machine, date=timezone.localdate(), completed=True)
        self.part = Part.objects.create(part_number="SH-1", name="Shaft")
        self.gauge = Gauge.objects.create(serial="VC-104", calibration_expiry=timezone.localdate() + timedelta(days=30))
        self.lot = RawMaterialLot.objects.create(supplier="S", po_number="P", grade="EN8", heat_number="H-8042", quantity=10, mtc_file="mtc/x.pdf")
        self.tpl = InspectionTemplate.objects.create(part=self.part, revision="A")
        mkf = lambda pin, kind, nom, up, lo, ctq: TemplateField.objects.create(
            template=self.tpl, pin_number=pin, label=f"F{pin}", kind=kind, nominal=nom, upper_tol=up, lower_tol=lo, is_ctq=ctq)
        self.f1 = mkf(1, "TOL", 25, "0.05", "-0.02", True)
        self.f2 = mkf(2, "TOL", 10, "0.1", "-0.1", False)
        self.f3 = mkf(3, "PF", None, None, None, False)
        q.release_template(self.tpl, self.qm)
        self.job = JobTraveler.objects.create(work_order="WO1", part=self.part, raw_lot=self.lot)
        for seq, name, hold in [(10, "Cut", 0), (20, "Turn", 60), (30, "Grind", 0)]:
            Operation.objects.create(traveler=self.job, seq=seq, name=name, hold_minutes=hold)

    def new_inspection(self):
        return q.start_inspection(self.ins, self.machine.qr_payload, self.job.qr_payload)


class QualityRules(Base):
    def test_requires_valid_signed_qr(self):
        with self.assertRaises(ValidationError):
            q.start_inspection(self.ins, "fake", self.job.qr_payload)

    def test_green_red_and_locked_order(self):
        i = self.new_inspection()
        with self.assertRaises(ValidationError):                  # cannot skip F1
            q.record_measurement(i, self.f2, "10", "VC-104", self.ins)
        self.assertTrue(q.record_measurement(i, self.f1, "25.04", "VC-104", self.ins).passed)
        self.assertFalse(q.record_measurement(i, self.f2, "10.5", "VC-104", self.ins).passed)

    def test_expired_gauge_blocked(self):
        Gauge.objects.create(serial="OLD", calibration_expiry=timezone.localdate() - timedelta(days=1))
        i = self.new_inspection()
        with self.assertRaisesMessage(ValidationError, "Expired Tool Calibration"):
            q.record_measurement(i, self.f1, "25", "OLD", self.ins)

    def test_failed_entry_needs_two_photos(self):
        i = self.new_inspection()
        q.record_measurement(i, self.f1, "25.01", "VC-104", self.ins)
        m = q.record_measurement(i, self.f2, "10.5", "VC-104", self.ins)
        q.record_measurement(i, self.f3, "yes", "", self.ins)
        with self.assertRaises(ValidationError):
            q.complete_inspection(i, self.ins)
        for _ in range(2):
            DefectPhoto.objects.create(measurement=m, image="defects/a.jpg")
        q.complete_inspection(i, self.ins)
        self.assertEqual(i.status, "AWAITING_APPROVAL")

    def test_ctq_failure_freezes_and_blocks_concession(self):
        i = self.new_inspection()
        q.record_measurement(i, self.f1, "26", "VC-104", self.ins)
        i.refresh_from_db()
        self.assertEqual(i.status, "FROZEN")
        with self.assertRaises(ValidationError):
            q.record_measurement(i, self.f2, "10", "VC-104", self.ins)
        Inspection.objects.filter(pk=i.pk).update(status="AWAITING_APPROVAL")
        i.refresh_from_db()
        with self.assertRaisesMessage(ValidationError, "CTQ"):
            q.grant_concession(i, self.qm, "X", "because")

    def test_non_ctq_concession_and_quarantine_blocks_job(self):
        i = self.new_inspection()
        q.record_measurement(i, self.f1, "25", "VC-104", self.ins)
        m = q.record_measurement(i, self.f2, "10.5", "VC-104", self.ins)
        q.record_measurement(i, self.f3, "yes", "", self.ins)
        for _ in range(2):
            DefectPhoto.objects.create(measurement=m, image="defects/a.jpg")
        q.complete_inspection(i, self.ins)
        with self.assertRaises(ValidationError):
            q.grant_concession(i, self.sup, "R1", "")             # justification mandatory
        q.quarantine_inspection(i, self.sup)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "QUARANTINED")
        with self.assertRaises(ValidationError):
            start_operation(self.job.ops.first(), self.opr, self.machine)
        q.mrb_decide(i, "RW", self.qm, "rework")                  # rework re-opens job
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "ACTIVE")

    def test_released_template_is_read_only(self):
        self.tpl.refresh_from_db()
        with self.assertRaises(ValidationError):
            self.tpl.revision = "B"; self.tpl.save()
        with self.assertRaises(ValidationError):
            self.f1.label = "x"; self.f1.save()

    def test_submitted_measurement_immutable(self):
        i = self.new_inspection()
        m = q.record_measurement(i, self.f1, "25", "VC-104", self.ins)
        m.value = 1
        with self.assertRaises(PermissionDenied):
            m.save()


class ProductionRules(Base):
    def test_sequence_hold_and_pm(self):
        o10, o20, o30 = self.job.ops.all()
        with self.assertRaises(ValidationError):
            start_operation(o20, self.opr, self.machine)          # skip Op 10
        start_operation(o10, self.opr, self.machine); finish_operation(o10, self.opr)
        start_operation(o20, self.opr, self.machine); finish_operation(o20, self.opr)
        with self.assertRaisesMessage(ValidationError, "Mandatory Cooling Hold Active"):
            start_operation(o30, self.opr, self.machine)
        Operation.objects.filter(pk=o20.pk).update(finished_at=timezone.now() - timedelta(minutes=61))
        o30.refresh_from_db()
        MachinePMCheck.objects.all().delete()
        with self.assertRaisesMessage(ValidationError, "PM check"):
            start_operation(o30, self.opr, self.machine)

    def test_quarantined_lot_cannot_be_issued(self):
        lot = RawMaterialLot.objects.create(supplier="S", po_number="P", grade="EN8", heat_number="H-2", quantity=1, mtc_file="mtc/y.pdf")
        reject_lot(lot, self.pm, "bad chemistry")
        with self.assertRaises(ValidationError):
            JobTraveler.objects.create(work_order="WO2", part=self.part, raw_lot=lot)

    def test_first_piece_locks_counter(self):
        o10 = self.job.ops.first()
        o10.requires_first_piece = True; o10.save()
        start_operation(o10, self.opr, self.machine)
        run = o10.run
        with self.assertRaises(ValidationError):
            increment_counter(run, self.opr)
        approve_first_piece(run, self.ins)
        increment_counter(run, self.opr)
        self.assertEqual(run.parts_count, 1)


class ShippingAndAudit(Base):
    def test_shipping_interlock(self):
        self.assertTrue(shipping_clearance(self.job))
        Operation.objects.filter(traveler=self.job).update(finished_at=timezone.now() - timedelta(hours=3))
        self.assertIn("Final PDI checklist is not signed and approved by Quality", shipping_clearance(self.job))
        Inspection.objects.create(template=self.tpl, machine=self.machine, job=self.job, inspector=self.ins,
                                  status="APPROVED", is_final_pdi=True)
        self.assertEqual(shipping_clearance(self.job), [])

    def test_audit_log_immutable(self):
        log(self.pm, "TEST", "obj", "a", "b")
        entry = AuditLog.objects.first()
        entry.new_value = "hacked"
        with self.assertRaises(PermissionDenied): entry.save()
        with self.assertRaises(PermissionDenied): entry.delete()
        with self.assertRaises(PermissionDenied): AuditLog.objects.all().delete()
        with self.assertRaises(PermissionDenied): AuditLog.objects.all().update(action="x")
