"""프로그램 자체의 회원가입 / 로그인 (로컬 계정).

- 사용자 정보는 이 폴더의 `users.db`(SQLite)에 저장된다. 서버가 필요 없다.
- 비밀번호는 평문으로 저장하지 않고 PBKDF2-HMAC-SHA256(솔트 + 24만 회 반복) 해시로만 저장한다.
- '자동 로그인'을 켜면 임의 토큰을 만들어 `auth_session.json`에 두고,
  DB에는 그 토큰의 해시만 저장해 다음 실행 때 비교한다.

주의: 클래스카드 계정(ID/PW)과는 별개의, 이 프로그램에 들어오기 위한 계정이다.
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "users.db")
SESSION_PATH = os.path.join(BASE_DIR, "auth_session.json")
PROFILE_ROOT = os.path.join(BASE_DIR, "profiles")

ITERATIONS = 240_000
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{4,20}$")
MIN_PASSWORD_LEN = 6


class AuthError(Exception):
    """회원가입/로그인 실패를 사용자에게 보여줄 메시지와 함께 전달한다."""


@dataclass
class User:
    id: int
    username: str
    display_name: str
    created_at: str
    last_login_at: str

    @property
    def profile_dir(self):
        path = os.path.join(PROFILE_ROOT, self.username)
        os.makedirs(path, exist_ok=True)
        return path


# ────────────────────────────────────────────────────────────────────────────
# 비밀번호 해시
# ────────────────────────────────────────────────────────────────────────────
def hash_password(password, salt=None, iterations=ITERATIONS):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return salt.hex(), digest.hex(), iterations


def verify_password(password, salt_hex, hash_hex, iterations=ITERATIONS):
    try:
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(digest.hex(), hash_hex)


def _token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ────────────────────────────────────────────────────────────────────────────
# 입력값 검사
# ────────────────────────────────────────────────────────────────────────────
def validate_username(username):
    username = (username or "").strip()
    if not username:
        raise AuthError("아이디를 입력하세요.")
    if not USERNAME_RE.match(username):
        raise AuthError("아이디는 영문·숫자·밑줄(_) 4~20자여야 합니다.")
    return username


def validate_password(password, password2=None):
    password = password or ""
    if len(password) < MIN_PASSWORD_LEN:
        raise AuthError(f"비밀번호는 {MIN_PASSWORD_LEN}자 이상이어야 합니다.")
    if password.strip() != password:
        raise AuthError("비밀번호의 앞뒤에 공백을 쓸 수 없습니다.")
    if password2 is not None and password != password2:
        raise AuthError("비밀번호가 서로 다릅니다.")
    return password


# ────────────────────────────────────────────────────────────────────────────
# 사용자 저장소
# ────────────────────────────────────────────────────────────────────────────
class UserStore:
    def __init__(self, db_path=DB_PATH, session_path=SESSION_PATH):
        self.db_path = db_path
        self.session_path = session_path
        self._lock = threading.Lock()
        self._init_db()

    # -- DB -----------------------------------------------------------------
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with self._lock, self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                    display_name  TEXT    NOT NULL DEFAULT '',
                    salt          TEXT    NOT NULL,
                    password_hash TEXT    NOT NULL,
                    iterations    INTEGER NOT NULL,
                    auto_token    TEXT    DEFAULT '',
                    created_at    TEXT    NOT NULL,
                    last_login_at TEXT    NOT NULL DEFAULT ''
                )
            """)

    def _row_to_user(self, row):
        return User(id=row["id"], username=row["username"],
                    display_name=row["display_name"] or row["username"],
                    created_at=row["created_at"], last_login_at=row["last_login_at"] or "")

    # -- 조회 ---------------------------------------------------------------
    def count(self):
        with self._lock, self._connect() as conn:
            return conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]

    def exists(self, username):
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT 1 FROM users WHERE username = ?",
                               ((username or "").strip(),)).fetchone()
        return row is not None

    def usernames(self):
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT username FROM users ORDER BY username").fetchall()
        return [r["username"] for r in rows]

    # -- 회원가입 -----------------------------------------------------------
    def register(self, username, password, password2=None, display_name=""):
        username = validate_username(username)
        validate_password(password, password2)
        if self.exists(username):
            raise AuthError("이미 사용 중인 아이디입니다.")

        salt, digest, iterations = hash_password(password)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    "INSERT INTO users (username, display_name, salt, password_hash,"
                    " iterations, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (username, (display_name or "").strip(), salt, digest, iterations, now))
        except sqlite3.IntegrityError:
            raise AuthError("이미 사용 중인 아이디입니다.")
        return self.login(username, password)

    # -- 로그인 -------------------------------------------------------------
    def login(self, username, password, remember=False):
        username = (username or "").strip()
        if not username:
            raise AuthError("아이디를 입력하세요.")
        if not password:
            raise AuthError("비밀번호를 입력하세요.")

        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        # 아이디가 없어도 '아이디 또는 비밀번호'로만 알려준다(계정 존재 여부 노출 방지).
        if row is None or not verify_password(password, row["salt"], row["password_hash"],
                                              row["iterations"]):
            raise AuthError("아이디 또는 비밀번호가 올바르지 않습니다.")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._lock, self._connect() as conn:
            conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now, row["id"]))
            row = conn.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()

        user = self._row_to_user(row)
        if remember:
            self._remember(user)
        else:
            self.forget(user.username)
        return user

    # -- 비밀번호 변경 ------------------------------------------------------
    def change_password(self, username, current_password, new_password, new_password2=None):
        self.login(username, current_password)          # 현재 비밀번호 확인
        validate_password(new_password, new_password2)
        if new_password == current_password:
            raise AuthError("현재 비밀번호와 다른 비밀번호를 입력하세요.")
        salt, digest, iterations = hash_password(new_password)
        with self._lock, self._connect() as conn:
            conn.execute("UPDATE users SET salt = ?, password_hash = ?, iterations = ?,"
                         " auto_token = '' WHERE username = ?",
                         (salt, digest, iterations, username))
        self.forget(username)
        return True

    def delete_user(self, username, password):
        self.login(username, password)
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM users WHERE username = ?", (username,))
        self.forget(username)
        return True

    # -- 자동 로그인 --------------------------------------------------------
    def _remember(self, user):
        token = secrets.token_urlsafe(32)
        with self._lock, self._connect() as conn:
            conn.execute("UPDATE users SET auto_token = ? WHERE id = ?",
                         (_token_hash(token), user.id))
        try:
            with open(self.session_path, "w", encoding="utf-8") as f:
                json.dump({"username": user.username, "token": token}, f)
            if os.name == "posix":
                os.chmod(self.session_path, 0o600)
        except Exception:
            pass

    def forget(self, username=None):
        try:
            if os.path.exists(self.session_path):
                os.remove(self.session_path)
        except Exception:
            pass
        if username:
            with self._lock, self._connect() as conn:
                conn.execute("UPDATE users SET auto_token = '' WHERE username = ?", (username,))

    def auto_login(self):
        """저장된 토큰이 유효하면 User를 돌려주고, 아니면 None."""
        try:
            with open(self.session_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            username, token = data.get("username", ""), data.get("token", "")
        except Exception:
            return None
        if not username or not token:
            return None

        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if row is None or not row["auto_token"]:
            self.forget()
            return None
        if not hmac.compare_digest(row["auto_token"], _token_hash(token)):
            self.forget(username)
            return None

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._lock, self._connect() as conn:
            conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now, row["id"]))
        return self._row_to_user(row)
