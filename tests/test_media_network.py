import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def test_uploaded_playlist_cannot_make_network_requests(client, brand):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"not a valid segment")

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        playlist = f"#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:2\n#EXT-X-MEDIA-SEQUENCE:0\n#EXTINF:2.0,\nhttp://127.0.0.1:{server.server_port}/media.ts\n#EXT-X-ENDLIST\n"
        r = client.post(
            f"/api/v1/brands/{brand['id']}/assets",
            files={"file": ("fake-recording.mp4", playlist)},
            data={"source": "合成攻击夹具", "license_note": "仅安全测试", "verified": "true"},
        )
        assert r.status_code == 422
        assert requests == [], requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
