# OWASP Top 10 — Code Review Reference

## A01: Broken Access Control
**What it is:** Users can act outside their intended permissions.
**Code patterns to detect:**
- Missing authorization checks before sensitive operations
- IDOR: using user-supplied IDs without ownership verification (`GET /users/{id}` without checking `id == current_user.id`)
- JWT tokens accepted without signature verification
- Admin endpoints accessible without role check

**Example vulnerable:**
```python
@app.get("/users/{user_id}/data")
def get_data(user_id: int):
    return db.query(User).filter(User.id == user_id).first()  # No auth check
```
**Fix:** Always verify `current_user.id == user_id` or require admin role.

---

## A02: Cryptographic Failures
**What it is:** Sensitive data exposed due to weak or absent encryption.
**Code patterns to detect:**
- Passwords stored as plain text or MD5/SHA1
- Sensitive data in logs
- HTTP instead of HTTPS for sensitive endpoints
- Hardcoded encryption keys in source code
- `secrets.token_hex` replaced with `random.random()`

**Example vulnerable:**
```python
user.password = hashlib.md5(password.encode()).hexdigest()  # MD5 is broken
```
**Fix:** Use `bcrypt` or `argon2`.

---

## A03: Injection
**What it is:** Untrusted data sent to an interpreter as part of a command or query.
**Code patterns to detect:**
- SQL string interpolation: `f"SELECT * FROM users WHERE name='{name}'"` → CWE-89
- Command injection: `os.system(f"ping {host}")` → CWE-78
- LDAP injection, XPath injection
- NoSQL injection in MongoDB `$where` clauses

**Example vulnerable:**
```python
query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
cursor.execute(query)
```
**Fix:** Use parameterized queries: `cursor.execute("SELECT ... WHERE username=?", (username,))`

---

## A04: Insecure Design
**What it is:** Missing or ineffective security controls at the design level.
**Patterns:** No rate limiting on auth endpoints, no account lockout, no CAPTCHA on registration, business logic flaws (e.g., negative quantities in cart).

---

## A05: Security Misconfiguration
**What it is:** Default configs, unnecessary features enabled, verbose errors.
**Code patterns:**
- `DEBUG=True` in production
- Stack traces returned in API responses
- CORS `allow_origins=["*"]` on sensitive endpoints
- Default admin credentials not changed

**Example vulnerable:**
```python
app = FastAPI(debug=True)  # Exposes internals in prod
```

---

## A06: Vulnerable and Outdated Components
**What it is:** Using libraries with known CVEs.
**Detection:** Check `requirements.txt` / `package.json` for packages with known vulnerabilities. Use `safety check` or `npm audit`.

---

## A07: Identification and Authentication Failures
**What it is:** Weak authentication implementations.
**Code patterns:**
- JWT `alg: none` accepted
- No token expiry check
- Session IDs in URLs
- Weak password policy (no minimum length)

```python
jwt.decode(token, options={"verify_signature": False})  # Never do this
```

---

## A08: Software and Data Integrity Failures
**What it is:** Code and infrastructure not protected from integrity violations.
**Patterns:** Deserializing untrusted data with `pickle`, no integrity check on downloaded packages.

```python
import pickle
data = pickle.loads(user_input)  # Remote code execution
```

---

## A09: Security Logging and Monitoring Failures
**What it is:** Insufficient logging of security events.
**What to check:** No logging of failed login attempts, no audit trail for admin actions, logs containing passwords or tokens.

---

## A10: Server-Side Request Forgery (SSRF)
**What it is:** Server fetches a URL supplied by the user, allowing access to internal services.
**Example vulnerable:**
```python
@app.get("/fetch")
def fetch(url: str):
    return requests.get(url).text  # Attacker passes http://169.254.169.254/metadata
```
**Fix:** Validate/whitelist allowed URL schemes and hosts.
