import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码
    plain_password: 前端已经做过 SHA256 的密码
    hashed_password: 数据库中存储的 bcrypt 哈希

    存储的哈希如果格式非法 (例如手动 seed 的明文 'x'),bcrypt 会抛 ValueError。
    捕获后返回 False — 防止脏数据让整个登录端点 500。
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except (ValueError, TypeError):
        return False

def get_password_hash(password: str) -> str:
    """对密码进行哈希
    password: 前端已经做过 SHA256 的密码
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8') 