from django import forms
from .models import RawMaterialLot


class LotForm(forms.ModelForm):
    class Meta:
        model = RawMaterialLot
        fields = ["supplier", "po_number", "grade", "heat_number", "quantity", "mtc_file", "requires_lab_test"]
