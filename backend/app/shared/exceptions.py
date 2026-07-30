"""Application exceptions."""


class PragyaAIException(Exception):
    """Base exception for PragyaAI."""
    pass


class LLMException(PragyaAIException):
    """Exception raised for LLM-related errors."""
    pass


class ValidationException(PragyaAIException):
    """Exception raised for validation errors."""
    pass


class ConfigurationException(PragyaAIException):
    """Exception raised for configuration errors."""
    pass
