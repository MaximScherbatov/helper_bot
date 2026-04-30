# app/utils/requests_timeout.py
def patch_requests_default_timeout(connect_timeout: float = 5.0, read_timeout: float = 20.0) -> None:
    import requests

    old_request = requests.sessions.Session.request

    def new_request(self, method, url, **kwargs):
        if "timeout" not in kwargs or kwargs["timeout"] is None:
            kwargs["timeout"] = (connect_timeout, read_timeout)
        return old_request(self, method, url, **kwargs)

    requests.sessions.Session.request = new_request