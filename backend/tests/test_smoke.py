import unittest

from fastapi import HTTPException

from app.api.routes.chat import chat
from app.db.models import Employee, EmployeeCreate
from app.main import app
from app.schemas.chat import ChatRequest
from app.services.agent_registry import has_agent, list_agents
from app.services.knowledge_base import load_handbook_documents, stable_document_id


class ApiContractTests(unittest.TestCase):
    def test_openapi_exposes_versioned_routes(self) -> None:
        paths = app.openapi()["paths"]
        self.assertIn("/health", paths)
        self.assertIn("/api/v1/agents", paths)
        self.assertIn("/api/v1/chat", paths)
        self.assertIn("/api/v1/employees", paths)

    def test_registry_contains_default_agents(self) -> None:
        agents = list_agents()
        self.assertGreaterEqual(len(agents), 2)
        self.assertTrue(has_agent("oa-assistant"))
        self.assertTrue(all(agent.name and agent.capabilities for agent in agents))

    def test_employee_create_does_not_require_id(self) -> None:
        self.assertNotIn("id", EmployeeCreate.model_fields)
        self.assertIsNone(Employee.model_fields["id"].default)


class ChatValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_agent_fails_before_streaming(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            await chat(ChatRequest(message="hello", agent_id="missing-agent"))
        self.assertEqual(raised.exception.status_code, 404)


class HandbookTests(unittest.TestCase):
    def test_handbook_is_structured_for_retrieval(self) -> None:
        documents = load_handbook_documents()
        self.assertGreaterEqual(len(documents), 30)
        self.assertTrue(all(document.metadata.get("policy") for document in documents))
        self.assertTrue(all(document.metadata.get("version") for document in documents))
        self.assertTrue(all(len(document.page_content) <= 700 for document in documents))

    def test_document_ids_are_stable_and_unique(self) -> None:
        documents = load_handbook_documents()
        identifiers = [stable_document_id(document) for document in documents]
        self.assertEqual(identifiers, [stable_document_id(document) for document in documents])
        self.assertEqual(len(identifiers), len(set(identifiers)))


if __name__ == "__main__":
    unittest.main()
