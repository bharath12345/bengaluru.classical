from unittest.mock import MagicMock, patch

from apps.pipeline.extractors.gemini_client import GeminiClient


def test_gemini_client_constructs_prompt_and_calls_model():
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "date": {"type": "string"},
        },
    }

    with patch("apps.pipeline.extractors.gemini_client.genai") as mock_genai:
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"title": "Concert", "date": "2026-08-10"}'
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.Client.return_value = MagicMock()

        client = GeminiClient(api_key="test-key", model_name="gemini-test")
        result = client.extract_structured("Extract event details", schema)

        assert result["title"] == "Concert"
        mock_model.generate_content.assert_called_once()


def test_gemini_client_handles_vision_input():
    schema = {"type": "object", "properties": {"text": {"type": "string"}}}

    with patch("apps.pipeline.extractors.gemini_client.genai") as mock_genai:
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"text": "Poster content"}'
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.Client.return_value = MagicMock()

        client = GeminiClient(api_key="test-key", model_name="gemini-test")
        result = client.extract_structured("Extract text", schema, image=b"fake-image")

        assert result["text"] == "Poster content"
        call_args = mock_model.generate_content.call_args[0][0]
        assert len(call_args) == 2
