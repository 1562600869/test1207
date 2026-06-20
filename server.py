import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import db

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _serve_static(self, path):
        if path == "/" or path == "":
            path = "/index.html"
        filepath = os.path.join(STATIC_DIR, path.lstrip("/"))
        if not os.path.isfile(filepath):
            self.send_error(404)
            return
        ext = os.path.splitext(filepath)[1]
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".png": "image/png",
            ".ico": "image/x-icon",
        }
        ct = content_types.get(ext, "application/octet-stream")
        with open(filepath, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/"):
            self._handle_api_get(path, parsed)
        else:
            self._serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            self._handle_api_post(path)
        else:
            self.send_error(404)

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            self._handle_api_put(path)
        else:
            self.send_error(404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            self._handle_api_delete(path)
        else:
            self.send_error(404)

    def _handle_api_get(self, path, parsed):
        if path == "/api/players":
            self._send_json(db.list_players())
        elif path == "/api/games":
            self._send_json(db.list_games())
        elif path == "/api/leaderboard":
            self._send_json(db.get_leaderboard())
        elif path == "/api/stats/monthly":
            self._send_json(db.get_monthly_stats())
        else:
            self.send_error(404)

    def _handle_api_post(self, path):
        body = self._read_body()
        if path == "/api/players":
            nickname = body.get("nickname", "").strip()
            phone = body.get("phone", "").strip()
            rank = body.get("rank", "初段")
            if not nickname or not phone:
                self._send_json({"error": "昵称和手机不能为空"}, 400)
                return
            if rank not in db.RANKS:
                self._send_json({"error": "无效段位"}, 400)
                return
            player, err = db.create_player(nickname, phone, rank)
            if err:
                self._send_json({"error": err}, 400)
                return
            self._send_json(player, 201)
        elif path == "/api/games":
            black_id = body.get("black_id")
            red_id = body.get("red_id")
            game_date = body.get("game_date", "").strip()
            result = body.get("result", "").strip()
            if not all([black_id, red_id, game_date, result]):
                self._send_json({"error": "所有字段不能为空"}, 400)
                return
            if int(black_id) == int(red_id):
                self._send_json({"error": "双方不能是同一人"}, 400)
                return
            game, err = db.create_game(int(black_id), int(red_id), game_date, result)
            if err:
                self._send_json({"error": err}, 400)
                return
            self._send_json(game, 201)
        else:
            self.send_error(404)

    def _handle_api_put(self, path):
        body = self._read_body()
        if path.startswith("/api/players/") and path.endswith("/promote"):
            try:
                pid = int(path.split("/")[3])
            except (ValueError, IndexError):
                self._send_json({"error": "无效ID"}, 400)
                return
            new_rank = body.get("rank", "").strip()
            if new_rank not in db.RANKS:
                self._send_json({"error": "无效段位"}, 400)
                return
            player, err = db.promote_player(pid, new_rank)
            if err:
                self._send_json({"error": err}, 400)
                return
            self._send_json(player)
        elif path.startswith("/api/players/"):
            try:
                pid = int(path.split("/")[3])
            except (ValueError, IndexError):
                self._send_json({"error": "无效ID"}, 400)
                return
            player = db.update_player(
                pid,
                nickname=body.get("nickname"),
                phone=body.get("phone"),
            )
            if not player:
                self._send_json({"error": "棋手不存在"}, 404)
                return
            self._send_json(player)
        else:
            self.send_error(404)

    def _handle_api_delete(self, path):
        if path.startswith("/api/players/"):
            try:
                pid = int(path.split("/")[3])
            except (ValueError, IndexError):
                self._send_json({"error": "无效ID"}, 400)
                return
            ok = db.delete_player(pid)
            if not ok:
                self._send_json({"error": "棋手不存在"}, 404)
                return
            self._send_json({"ok": True})
        else:
            self.send_error(404)


def main():
    db.init_db()
    server = HTTPServer(("127.0.0.1", 7384), Handler)
    print("服务已启动: http://localhost:7384")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print("服务已停止")


if __name__ == "__main__":
    main()
