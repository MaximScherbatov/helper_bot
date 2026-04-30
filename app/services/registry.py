from typing import Dict, List, Optional

from app.services.base import BaseService


class ServiceRegistry:
    def __init__(self):
        self._services: Dict[str, BaseService] = {}

    def register(self, service: BaseService) -> None:
        self._services[service.code] = service

    def get(self, code: str) -> Optional[BaseService]:
        return self._services.get(code)

    def all(self) -> List[BaseService]:
        return list(self._services.values())