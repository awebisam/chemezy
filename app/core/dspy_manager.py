import dspy
from app.core.config import settings


def setup_dspy():
    """
    Configures the global DSPy settings based on the application configuration.
    This function should be called once on application startup.
    """
    lm_provider = None
    if all([
        settings.azure_openai_key,
        settings.azure_openai_endpoint,
        settings.azure_openai_deployment_name
    ]):
        try:
            model_path = f"azure/{settings.azure_openai_deployment_name}"
            lm_provider = dspy.LM(
                model_path,
                api_key=settings.azure_openai_key,
                api_base=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version,
            )
            print(
                f"INFO: DSPy configured with dspy.LM for Azure model: {model_path}")
        except Exception as e:
            print(f"WARNING: Azure OpenAI configuration failed: {e}")
    else:
        print("INFO: No LLM provider credentials found. DSPy will not be configured with a language model.")

    if lm_provider:
        dspy.settings.configure(lm=lm_provider)
    else:
        # To make it clear that no LM is available, we can configure it with a dummy or leave it unconfigured.
        # Leaving it unconfigured is fine, as services will check `dspy.settings.lm`.
        print("CRITICAL: No LLM provider configured. Services requiring DSPy may not function.")


def is_dspy_configured() -> bool:
    """Checks if a language model is configured in DSPy settings."""
    return hasattr(dspy.settings, 'lm') and dspy.settings.lm is not None
