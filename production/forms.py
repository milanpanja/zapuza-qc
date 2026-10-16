from django import forms
from .models import ShiftHandover


class HandoverForm(forms.ModelForm):
    class Meta:
        model = ShiftHandover
        fields = ["machine", "shift", "active_job_status", "parts_produced", "scrap_count",
                  "open_quality_alerts", "pending_pdi_reviews", "tool_wear", "machine_health"]
