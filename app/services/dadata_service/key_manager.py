from app.repositories.dadata import DaDataRepository


class DaDataKeyManager:
    def __init__(self, repo: DaDataRepository):
        self.repo = repo

    def get_available_key(self):
        return self.repo.get_best_available_key()

    def mark_attempt_usage(self, key_id: int) -> None:
        # считаем по факту попытки запроса к DaData
        self.repo.increment_key_usage(key_id)

    def mark_exhausted(self, key_id: int) -> None:
        self.repo.mark_key_exhausted(key_id)

    def mark_success_usage(self, key_id: int) -> None:
        # оставляем для совместимости старых вызовов
        self.mark_attempt_usage(key_id)