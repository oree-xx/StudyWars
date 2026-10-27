import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import anthropic
import httpx
from fastapi.testclient import TestClient

from app import ai
from app.main import app
from app.models import Question


QUESTION = {
    "question": "What is 2 + 2?", "options": ["3", "4", "5", "6"],
    "correct_index": 1, "explanation": "Two plus two is four.",
}


def response_for(payload, stop_reason="tool_use"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="tool_use", name="create_quiz", input=payload)],
    )


class GenerationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(patch.object(ai.settings, "llm_provider", "anthropic"))

    async def test_pinned_sdk_can_generate_using_forced_tool(self):
        requests = []

        def respond(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={
                "id": "msg_test", "type": "message", "role": "assistant",
                "model": "claude-sonnet-4-6", "stop_reason": "tool_use", "stop_sequence": None,
                "content": [{"type": "tool_use", "id": "tool_test", "name": "create_quiz", "input": {"questions": [QUESTION]}}],
                "usage": {"input_tokens": 10, "output_tokens": 20},
            })

        async with anthropic.AsyncAnthropic(
            api_key="test-only-key", http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
        ) as client:
            with patch.object(ai, "get_client", return_value=client):
                quiz = await ai.generate_questions("Arithmetic notes", 1)
        self.assertEqual(quiz[0].correct_index, 1)
        self.assertEqual(requests[0]["tool_choice"], {"type": "tool", "name": "create_quiz"})
        self.assertEqual(requests[0]["model"], ai.settings.anthropic_model)
        self.assertIn("properties", requests[0]["tools"][0]["input_schema"])

    async def test_invalid_tool_data_is_rejected(self):
        invalid = {**QUESTION, "correct_index": 8}
        create = AsyncMock(return_value=response_for({"questions": [invalid]}))
        with patch.object(ai, "get_client", return_value=SimpleNamespace(messages=SimpleNamespace(create=create))):
            with self.assertRaises(ai.QuizGenerationError):
                await ai.generate_questions("Notes", 1)

    async def test_missing_quiz_tool_is_rejected(self):
        response = SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="No quiz")])
        create = AsyncMock(return_value=response)
        with patch.object(ai, "get_client", return_value=SimpleNamespace(messages=SimpleNamespace(create=create))):
            with self.assertRaises(ai.QuizGenerationError):
                await ai.generate_questions("Notes", 1)

    async def test_truncated_and_wrong_count_responses_are_rejected(self):
        for response in [response_for({"questions": [QUESTION]}, "max_tokens"), response_for({"questions": []})]:
            create = AsyncMock(return_value=response)
            with patch.object(ai, "get_client", return_value=SimpleNamespace(messages=SimpleNamespace(create=create))):
                with self.assertRaises(ai.QuizGenerationError):
                    await ai.generate_questions("Notes", 1)

    async def test_missing_api_key_has_useful_configuration_error(self):
        with patch.object(ai, "_client", None), patch.object(ai.settings, "anthropic_api_key", ""):
            with self.assertRaisesRegex(ai.ConfigurationError, "ANTHROPIC_API_KEY"):
                ai.get_client()


class GenerationEndpointTests(unittest.TestCase):
    def test_endpoint_awaits_generation_and_returns_quiz(self):
        generate = AsyncMock(return_value=[Question.model_validate(QUESTION)])
        with patch("app.routers.questions.generate_questions", generate), TestClient(app) as client:
            response = client.post("/api/generate-questions", data={"notes": "  My notes  ", "num_questions": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["questions"][0]["correct_index"], 1)
        generate.assert_awaited_once_with("My notes", 1)

    def test_provider_failure_does_not_expose_credentials_or_notes(self):
        generate = AsyncMock(side_effect=RuntimeError("secret-key-private-notes"))
        with patch("app.routers.questions.generate_questions", generate), TestClient(app) as client:
            response = client.post("/api/generate-questions", data={"notes": "Notes"})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("secret-key-private-notes", response.text)

    def test_invalid_pdf_returns_actionable_bad_request(self):
        with patch("app.routers.questions.extract_text_from_pdf", side_effect=ValueError("bad pdf")), TestClient(app) as client:
            response = client.post("/api/generate-questions", files={"file": ("broken.pdf", b"bad", "application/pdf")})
        self.assertEqual(response.status_code, 400)
        self.assertIn("PDF could not be read", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
