import json
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app import ai
from app.main import app


QUESTION = {
    "question": "What is 2 + 2?", "options": ["3", "4", "5", "6"],
    "correct_index": 1, "explanation": "Two plus two is four.",
}


def gemini_response(questions=None, finish_reason="STOP"):
    return {
        "candidates": [{
            "finishReason": finish_reason,
            "content": {"parts": [{"text": json.dumps({"questions": questions if questions is not None else [QUESTION]})}]},
        }],
    }


class GeminiGenerationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(patch.object(ai.settings, "llm_provider", "gemini"))
        self.enterContext(patch.object(ai.settings, "gemini_api_key", "test-only-gemini-key"))
        self.enterContext(patch.object(ai.settings, "gemini_model", "gemini-3.5-flash-lite"))

    async def generate(self, payload, status=200, count=1):
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(status, json=payload)))
        with patch.object(ai, "get_gemini_client", return_value=client):
            return await ai.generate_questions("Private arithmetic notes", count)

    async def test_rest_request_uses_header_key_and_structured_quiz_schema(self):
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json=gemini_response())

        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        with patch.object(ai, "get_gemini_client", return_value=client), patch.object(ai, "get_client") as anthropic_client:
            quiz = await ai.generate_questions("Arithmetic notes", 1)
        self.assertTrue(client.is_closed)
        anthropic_client.assert_not_called()
        self.assertEqual(quiz[0].correct_index, 1)
        self.assertEqual(len(quiz[0].options), 4)
        request = requests[0]
        self.assertEqual(request.url.host, "generativelanguage.googleapis.com")
        self.assertEqual(request.url.path, "/v1beta/models/gemini-3.5-flash-lite:generateContent")
        self.assertEqual(request.url.query, b"")
        self.assertEqual(request.headers["x-goog-api-key"], "test-only-gemini-key")
        body = json.loads(request.content)
        self.assertEqual(body["generationConfig"]["responseMimeType"], "application/json")
        schema = body["generationConfig"]["responseJsonSchema"]
        self.assertEqual(schema["properties"]["questions"]["minItems"], 1)
        self.assertEqual(schema["properties"]["questions"]["maxItems"], 1)
        self.assertEqual(schema["$defs"]["Question"]["properties"]["options"]["minItems"], 4)
        self.assertIn("Arithmetic notes", body["contents"][0]["parts"][0]["text"])

    async def test_thought_parts_are_ignored_and_answer_parts_are_combined(self):
        text = json.dumps({"questions": [QUESTION]})
        response = gemini_response()
        response["candidates"][0]["content"]["parts"] = [
            {"text": "Private reasoning that is not JSON", "thought": True},
            {"text": text[:20]}, {"text": text[20:]},
        ]
        quiz = await self.generate(response)
        self.assertEqual(quiz[0].question, QUESTION["question"])

    async def test_exact_count_and_question_schema_are_validated(self):
        invalid_quizzes = [[], [QUESTION, QUESTION], [{**QUESTION, "correct_index": 9}], [{**QUESTION, "options": ["a", "b", "c"]}]]
        for questions in invalid_quizzes:
            with self.subTest(questions=questions):
                with self.assertRaises(ai.QuizGenerationError):
                    await self.generate(gemini_response(questions))

    async def test_incomplete_and_filtered_candidates_are_rejected_even_with_valid_json(self):
        for reason in ("MAX_TOKENS", "CONTINUATION", "SAFETY", "RECITATION", "OTHER", None):
            with self.subTest(reason=reason):
                with self.assertRaises(ai.QuizGenerationError) as error:
                    await self.generate(gemini_response(finish_reason=reason))
                if reason in ("MAX_TOKENS", "CONTINUATION"):
                    self.assertIn("incomplete", str(error.exception))

    async def test_prompt_blocks_and_missing_answers_are_rejected(self):
        blocked = {**gemini_response(), "promptFeedback": {"blockReason": "SAFETY"}}
        thought_only = gemini_response()
        thought_only["candidates"][0]["content"]["parts"] = [{"text": "thinking", "thought": True}]
        for response in (blocked, {}, {"candidates": []}, thought_only):
            with self.subTest(response=response):
                with self.assertRaises(ai.QuizGenerationError) as error:
                    await self.generate(response)
                if response is blocked:
                    self.assertIn("different study material", str(error.exception))

    async def test_malformed_json_and_response_shapes_are_rejected(self):
        malformed = gemini_response()
        malformed["candidates"][0]["content"]["parts"][0]["text"] = "not JSON"
        for response in (malformed, [], {"candidates": [None]}, {"candidates": [{"finishReason": "STOP", "content": None}]}):
            with self.subTest(response=response):
                with self.assertRaises(ai.QuizGenerationError):
                    await self.generate(response)
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, text="<html>error</html>")))
        with patch.object(ai, "get_gemini_client", return_value=client):
            with self.assertRaises(ai.QuizGenerationError):
                await ai.generate_questions("Notes", 1)

    async def test_http_errors_are_actionable_without_echoing_upstream_details_or_fallback(self):
        for status, expected_error, message in (
            (401, ai.ConfigurationError, "credentials"),
            (403, ai.ConfigurationError, "credentials"),
            (400, ai.ConfigurationError, "GEMINI_MODEL"),
            (404, ai.ConfigurationError, "GEMINI_MODEL"),
            (429, ai.QuizGenerationError, "usage limit"),
            (503, ai.QuizGenerationError, "unavailable"),
        ):
            with self.subTest(status=status), patch.object(ai, "get_client") as anthropic_client:
                with self.assertRaisesRegex(expected_error, message) as error:
                    await self.generate({"error": {"message": "test-only-gemini-key Private arithmetic notes"}}, status=status)
                self.assertNotIn("test-only-gemini-key", str(error.exception))
                self.assertNotIn("Private arithmetic notes", str(error.exception))
                anthropic_client.assert_not_called()

    async def test_network_errors_and_timeouts_are_safe_and_close_the_client(self):
        for error_type in (httpx.ReadTimeout, httpx.ConnectError):
            def fail(request):
                raise error_type("test-only-gemini-key Private arithmetic notes", request=request)

            client = httpx.AsyncClient(transport=httpx.MockTransport(fail))
            with self.subTest(error_type=error_type), patch.object(ai, "get_gemini_client", return_value=client):
                with self.assertRaises(ai.QuizGenerationError) as error:
                    await ai.generate_questions("Private arithmetic notes", 1)
                self.assertNotIn("test-only-gemini-key", str(error.exception))
                self.assertNotIn("Private arithmetic notes", str(error.exception))
                self.assertTrue(client.is_closed)

    async def test_configuration_and_input_errors_do_not_send_requests(self):
        with patch.object(ai, "get_gemini_client") as client:
            for count in (0, 21):
                with self.assertRaises(ValueError):
                    await ai.generate_questions("Notes", count)
            with patch.object(ai.settings, "gemini_api_key", ""):
                with self.assertRaisesRegex(ai.ConfigurationError, "GEMINI_API_KEY"):
                    await ai.generate_questions("Notes", 1)
            with patch.object(ai.settings, "gemini_model", "model?key=unexpected"):
                with self.assertRaisesRegex(ai.ConfigurationError, "GEMINI_MODEL"):
                    await ai.generate_questions("Notes", 1)
            with patch.object(ai.settings, "llm_provider", "unknown"):
                with self.assertRaisesRegex(ai.ConfigurationError, "LLM_PROVIDER"):
                    await ai.generate_questions("Notes", 1)
            client.assert_not_called()


class GeminiEndpointTests(unittest.TestCase):
    def test_provider_error_response_never_exposes_credentials_or_notes(self):
        for status, expected_status in ((403, 500), (429, 502)):
            transport = httpx.MockTransport(lambda _: httpx.Response(status, json={"error": {"message": "private-api-key private-notes"}}))
            provider_client = httpx.AsyncClient(transport=transport)
            with self.subTest(status=status), patch.object(ai.settings, "llm_provider", "gemini"), patch.object(ai.settings, "gemini_api_key", "private-api-key"), patch.object(ai, "get_gemini_client", return_value=provider_client), TestClient(app) as client:
                response = client.post("/api/generate-questions", data={"notes": "private-notes", "num_questions": "1"})
            self.assertEqual(response.status_code, expected_status)
            self.assertNotIn("private-api-key", response.text)
            self.assertNotIn("private-notes", response.text)


if __name__ == "__main__":
    unittest.main()
