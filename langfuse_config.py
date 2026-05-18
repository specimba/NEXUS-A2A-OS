from langfuse import Langfuse
import os

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY", "")
)

def track_call(model, prompt, response, tokens):
    langfuse.trace(
        name="nexus-execution",
        input=prompt,
        output=response,
        metadata={"model": model, "tokens": tokens}
    )