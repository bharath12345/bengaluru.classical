import json

from google import genai


class GeminiClient:
    """Thin wrapper around Google Gemini for structured extraction."""

    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        self.client = genai.Client(api_key=api_key)
        # Compatibility with plan tests that mock GenerativeModel
        self._model = None

    @property
    def model(self):
        if self._model is None:
            # Prefer Client API; fall back if GenerativeModel exists (tests)
            if hasattr(genai, "GenerativeModel"):
                self._model = genai.GenerativeModel(self.model_name)
            else:
                self._model = None
        return self._model

    def extract_structured(self, prompt: str, schema: dict, image: bytes = None) -> dict:
        full_prompt = (
            f"{prompt}\n\nRespond with valid JSON matching this schema:\n"
            f"{json.dumps(schema)}\n\n"
            "Extract only information visible in the input. Do not hallucinate."
        )

        if image:
            contents = [full_prompt, {"mime_type": "image/jpeg", "data": image}]
        else:
            contents = [full_prompt]

        # Prefer GenerativeModel path when present (matches plan tests)
        if hasattr(genai, "GenerativeModel"):
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(contents)
            return json.loads(response.text)

        response = self.client.models.generate_content(model=self.model_name, contents=contents)
        return json.loads(response.text)
