from django import forms


class SubmissionForm(forms.Form):
    title = forms.CharField(max_length=300, required=False)
    genre = forms.ChoiceField(
        choices=[("", "---"), ("karnatic", "Karnatic"), ("hindustani", "Hindustani")],
        required=False,
    )
    event_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    event_time = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type": "time"}))
    venue_text = forms.CharField(max_length=300, required=False)
    artists_text = forms.CharField(widget=forms.Textarea, required=False)
    ticket_url = forms.URLField(required=False, assume_scheme="https")
    description = forms.CharField(widget=forms.Textarea, required=False)
    poster = forms.FileField(required=False, help_text="Upload a poster image (JPG/PNG)")
    submitter_contact = forms.CharField(
        max_length=200, required=False, help_text="Optional: your email for follow-up"
    )
    honeypot = forms.CharField(required=False, widget=forms.HiddenInput(), label="")

    def clean_honeypot(self):
        value = self.cleaned_data.get("honeypot", "")
        if value:
            raise forms.ValidationError("Spam detected.")
        return value

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("poster") and not cleaned.get("title"):
            raise forms.ValidationError(
                "Please provide either a poster image or event details (at least a title)."
            )
        return cleaned
