from langfuse import Langfuse
import os

langfuse = Langfuse(
    public_key="pk-lf-5c649cb6-8bbf-4cd9-b551-775c4850f274",
    secret_key="sk-lf-5da22f63-5cd7-4e20-83de-38e166161da4",
    host="https://cloud.langfuse.com"
)

def track_call(model, prompt, response, tokens):
    langfuse.trace(
        name="nexus-execution",
        input=prompt,
        output=response,
        metadata={"model": model, "tokens": tokens}
    )