from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from materials.models import RawMaterialLot
from plant.models import Gauge, Machine, MachinePMCheck, Part, Site
from production.models import JobTraveler, Operation
from quality.models import InspectionTemplate, TemplateField
from quality.services import release_template


class Command(BaseCommand):
    help = "Create demo users, machine, gauge, material, template and a job traveler"

    def handle(self, *a, **k):
        U = get_user_model()
        users = {}
        for username, role in [("plantmgr", "PM"), ("qeng", "QE"), ("qmgr", "QM"), ("super", "SUP"),
                               ("inspector", "INS"), ("operator", "OPR"), ("dock", "DOCK"), ("ware", "WH")]:
            u, new = U.objects.get_or_create(username=username, defaults={"role": role, "email": f"{username}@zapuza.local"})
            if new:
                u.set_password("demo12345"); u.save()
            users[role] = u
        site, _ = Site.objects.get_or_create(name="Main Machining Shop")
        m, _ = Machine.objects.get_or_create(code="CNC-04", defaults={"site": site, "name": "CNC Lathe #04"})
        MachinePMCheck.objects.update_or_create(machine=m, date=timezone.localdate(), defaults={"completed": True})
        part, _ = Part.objects.get_or_create(part_number="SH-100", defaults={"name": "Drive Shaft"})
        Gauge.objects.get_or_create(serial="VC-104", defaults={"description": "Vernier Caliper", "calibration_expiry": timezone.localdate() + timedelta(days=90)})
        Gauge.objects.get_or_create(serial="VC-OLD", defaults={"description": "Expired caliper", "calibration_expiry": timezone.localdate() - timedelta(days=5)})
        lot, _ = RawMaterialLot.objects.get_or_create(heat_number="H-8042", defaults={
            "supplier": "Steel Co", "po_number": "PO-1", "grade": "EN8", "quantity": 100, "mtc_file": "mtc/demo.pdf"})
        tpl, created = InspectionTemplate.objects.get_or_create(part=part, revision="A")
        if created:
            for pin, label, kind, nom, up, lo, ctq in [
                (1, "Shaft diameter", "TOL", 25, "0.05", "-0.02", True),
                (2, "Length", "TOL", 120, "0.10", "-0.10", False),
                (3, "Surface roughness Ra", "MAX", "0.8", None, None, False),
                (4, "Free of burrs", "PF", None, None, None, False)]:
                TemplateField.objects.create(template=tpl, pin_number=pin, label=label, kind=kind, nominal=nom,
                                             upper_tol=up, lower_tol=lo, is_ctq=ctq)
            release_template(tpl, users["QM"])
        if not JobTraveler.objects.filter(work_order="WO-001").exists():
            t = JobTraveler.objects.create(work_order="WO-001", part=part, raw_lot=lot, quantity=10)
            for seq, name, hold, fp in [(10, "Sawing", 0, False), (20, "CNC Rough Turning", 0, True),
                                        (30, "Heat Treatment", 60, False), (40, "Precision Grinding", 0, False),
                                        (50, "Final PDI & Wash", 0, False), (60, "Packing", 0, False)]:
                Operation.objects.create(traveler=t, seq=seq, name=name, hold_minutes=hold, requires_first_piece=fp)
        t = JobTraveler.objects.get(work_order="WO-001")
        self.stdout.write("Demo users (password demo12345): plantmgr qeng qmgr super inspector operator dock ware")
        self.stdout.write(f"MACHINE QR PAYLOAD: {m.qr_payload}")
        self.stdout.write(f"JOB QR PAYLOAD:     {t.qr_payload}")
