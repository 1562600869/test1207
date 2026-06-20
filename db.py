import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chess.db")

RANKS = ["初段", "二段", "三段", "四段", "五段"]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            phone TEXT NOT NULL,
            rank TEXT NOT NULL DEFAULT '初段',
            score INTEGER NOT NULL DEFAULT 0,
            wins INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            black_id INTEGER NOT NULL,
            red_id INTEGER NOT NULL,
            game_date TEXT NOT NULL,
            result TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (black_id) REFERENCES players(id),
            FOREIGN KEY (red_id) REFERENCES players(id)
        )
    """)
    conn.commit()
    conn.close()


def list_players():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM players ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_player(nickname, phone, rank="初段"):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO players (nickname, phone, rank) VALUES (?, ?, ?)",
        (nickname, phone, rank),
    )
    conn.commit()
    player_id = c.lastrowid
    player = dict(conn.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone())
    conn.close()
    return player


def update_player(player_id, nickname=None, phone=None):
    conn = get_conn()
    fields = []
    vals = []
    if nickname is not None:
        fields.append("nickname=?")
        vals.append(nickname)
    if phone is not None:
        fields.append("phone=?")
        vals.append(phone)
    if not fields:
        conn.close()
        return None
    vals.append(player_id)
    c = conn.cursor()
    c.execute(f"UPDATE players SET {', '.join(fields)} WHERE id=?", vals)
    conn.commit()
    row = conn.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_player(player_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM games WHERE black_id=? OR red_id=?", (player_id, player_id))
    c.execute("DELETE FROM players WHERE id=?", (player_id,))
    conn.commit()
    conn.close()
    return c.rowcount > 0


def promote_player(player_id, new_rank):
    conn = get_conn()
    row = conn.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone()
    if not row:
        conn.close()
        return None, "棋手不存在"
    current_rank = row["rank"]
    if new_rank not in RANKS:
        conn.close()
        return None, "无效段位"
    if RANKS.index(new_rank) <= RANKS.index(current_rank):
        conn.close()
        return None, "只能向更高段位晋升"
    c = conn.cursor()
    c.execute("UPDATE players SET rank=? WHERE id=?", (new_rank, player_id))
    conn.commit()
    player = dict(conn.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone())
    conn.close()
    return player, None


def create_game(black_id, red_id, game_date, result):
    if black_id == red_id:
        return None, "双方不能是同一人"
    if result not in ("黑胜", "红胜", "和棋"):
        return None, "无效结果"
    conn = get_conn()
    black = conn.execute("SELECT * FROM players WHERE id=?", (black_id,)).fetchone()
    red = conn.execute("SELECT * FROM players WHERE id=?", (red_id,)).fetchone()
    if not black or not red:
        conn.close()
        return None, "棋手不存在"
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO games (black_id, red_id, game_date, result) VALUES (?, ?, ?, ?)",
            (black_id, red_id, game_date, result),
        )
        game_id = c.lastrowid
        if result == "黑胜":
            c.execute("UPDATE players SET score=score+3, wins=wins+1 WHERE id=?", (black_id,))
        elif result == "红胜":
            c.execute("UPDATE players SET score=score+3, wins=wins+1 WHERE id=?", (red_id,))
        else:
            c.execute("UPDATE players SET score=score+1 WHERE id=?", (black_id,))
            c.execute("UPDATE players SET score=score+1 WHERE id=?", (red_id,))
        conn.commit()
        game = dict(conn.execute("SELECT * FROM games WHERE id=?", (game_id,)).fetchone())
        game["black_nickname"] = black["nickname"]
        game["red_nickname"] = red["nickname"]
        conn.close()
        return game, None
    except Exception as e:
        conn.rollback()
        conn.close()
        return None, str(e)


def list_games():
    conn = get_conn()
    rows = conn.execute("""
        SELECT g.*, b.nickname AS black_nickname, r.nickname AS red_nickname
        FROM games g
        JOIN players b ON g.black_id = b.id
        JOIN players r ON g.red_id = r.id
        ORDER BY g.id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_leaderboard():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM players ORDER BY score DESC, wins DESC, id ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_monthly_stats():
    conn = get_conn()
    rows = conn.execute("""
        SELECT p.rank, COUNT(*) AS game_count
        FROM games g
        JOIN players p ON (p.id = g.black_id OR p.id = g.red_id)
        WHERE strftime('%%Y-%%m', g.game_date) = strftime('%%Y-%%m', 'now', 'localtime')
        GROUP BY p.rank
        ORDER BY p.rank
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]
