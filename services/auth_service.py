"""
Authentication Service — registration, login, session management
"""

import secrets
from datetime import datetime
from typing import Optional, Tuple
from models import get_session, User, UserSettings

_current_user: Optional[User] = None


def register(username: str, email: str, password: str, full_name: str = "") -> Tuple[bool, str]:
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if "@" not in email:
        return False, "Invalid email address."

    session = get_session()
    try:
        if session.query(User).filter_by(username=username).first():
            return False, "Username already taken."
        if session.query(User).filter_by(email=email).first():
            return False, "Email already registered."

        user = User(username=username, email=email, full_name=full_name)
        user.set_password(password)
        session.add(user)
        session.flush()

        settings = UserSettings(user_id=user.id)
        session.add(settings)
        session.commit()
        return True, "Account created successfully."
    except Exception as e:
        session.rollback()
        return False, f"Registration error: {e}"
    finally:
        session.close()


def login(username: str, password: str, remember: bool = False) -> Tuple[bool, str, Optional[int]]:
    global _current_user
    session = get_session()
    try:
        user = session.query(User).filter_by(username=username, is_active=True).first()
        if not user:
            return False, "User not found.", None
        if not user.check_password(password):
            return False, "Incorrect password.", None

        user.last_login = datetime.utcnow()
        if remember:
            user.remember_token = secrets.token_hex(32)
        session.commit()

        _current_user = User(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
        )
        return True, "Login successful.", user.id
    except Exception as e:
        session.rollback()
        return False, f"Login error: {e}", None
    finally:
        session.close()


def logout():
    global _current_user
    _current_user = None


def get_current_user() -> Optional[User]:
    return _current_user


def get_current_user_id() -> Optional[int]:
    return _current_user.id if _current_user else None
