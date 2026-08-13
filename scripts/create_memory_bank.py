import os
import google.auth
import vertexai
from google.adk.memory import VertexAiMemoryBankService

_, project_id = google.auth.default()
location = os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_LOCATION") or os.environ.get("GOOGLE_CLOUD_LOCATION") or "us-central1"
if location == "global":
    location = "us-central1"

print(f"Initializing Vertex AI client for project={project_id}, location={location}")
client = vertexai.Client(project=project_id, location=location)

print("Creating Memory Bank instance (Agent Engine)...")
memory_bank = client.agent_engines.create()

resource_name = memory_bank.api_resource.name
memory_bank_id = resource_name.split("/")[-1]

print(f"Created Memory Bank successfully!")
print(f"Resource Name: {resource_name}")
print(f"MEMORY_BANK_ID: {memory_bank_id}")
