from retriva_eval.core.config import Settings

def test_settings_defaults():
    settings = Settings()
    assert settings.retriva_adapter == "gateway_http"
    assert settings.eval_knowledge_base == "eval-ragas-sample-markdown"
    assert isinstance(settings.parsed_eval_metadata, dict)
    assert settings.parsed_eval_metadata["retriva_eval"] == "true"
