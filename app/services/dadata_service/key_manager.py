from app.repositories.dadata import DaDataRepository


class DaDataKeyManager:
    def __init__(self, repo: DaDataRepository):
        self.repo = repo

    def get_available_key(self):
        return self.repo.get_first_available_key()

    def mark_success_usage(self, key_id: int) -> None:
        self.repo.increment_key_usage(key_id)