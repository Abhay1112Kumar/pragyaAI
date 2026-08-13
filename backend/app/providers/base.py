from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate(self, system_prompt: str, user_message: str) -> str:
        raise NotImplementedError
