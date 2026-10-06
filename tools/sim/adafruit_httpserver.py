"""Stand-in for adafruit_httpserver, enough to import app/web.py in tests."""
GET, POST = "GET", "POST"
OK_200 = (200, "OK")
BAD_REQUEST_400 = (400, "Bad Request")


class Request:
    pass


class JSONResponse:
    def __init__(self, request, data, *, headers=None, status=OK_200):
        self.data = data
        self.status = status


class Response:
    def __init__(self, request, body="", *, content_type=None, status=OK_200):
        self.body = body
        self.content_type = content_type
