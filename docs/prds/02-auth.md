# PRD-02: Auth & User Management

## Domain
User registration, login, session management, JWT tokens.

## Dependencies
- PRD-01 (database, project structure)

## Goal
Secure, simple auth system. Users can sign up, log in, and maintain sessions. No OAuth social login for MVP — just email/password + JWT.

---

## 1. API Endpoints

### Auth Routes (`/api/auth`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/auth/register` | Create new account | Public |
| POST | `/api/auth/login` | Get JWT token | Public |
| POST | `/api/auth/refresh` | Refresh JWT token | Token |
| POST | `/api/auth/logout` | Invalidate token | Token |
| GET | `/api/auth/me` | Get current user | Token |

### User Routes (`/api/users`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/users/me` | Get profile | Token |
| PATCH | `/api/users/me` | Update profile | Token |
| DELETE | `/api/users/me` | Delete account | Token |

## 2. Request/Response Schemas

### POST /api/auth/register
```json
// Request
{
  "email": "creator@example.com",
  "password": "securePassword123",
  "name": "Creator Name"
}

// Response 201
{
  "id": "uuid",
  "email": "creator@example.com",
  "name": "Creator Name",
  "created_at": "2026-03-28T00:00:00Z"
}
```

### POST /api/auth/login
```json
// Request
{
  "email": "creator@example.com",
  "password": "securePassword123"
}

// Response 200
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### GET /api/auth/me
```json
// Response 200
{
  "id": "uuid",
  "email": "creator@example.com",
  "name": "Creator Name",
  "created_at": "2026-03-28T00:00:00Z",
  "accounts": [
    {
      "id": "uuid",
      "platform": "instagram",
      "username": "creator_ig",
      "status": "active"
    }
  ]
}
```

## 3. Implementation Details

### Password Handling
- Hash with **bcrypt** (via `passlib`)
- Minimum 8 characters
- No password stored in plaintext ever

### JWT Tokens
- **Access token:** 24h expiry, contains `user_id` and `email`
- **Refresh token:** 7 days expiry, stored in DB for revocation
- Algorithm: HS256
- Secret from `JWT_SECRET` env var

### Token Flow
1. User logs in → gets access + refresh tokens
2. Access token sent in `Authorization: Bearer <token>` header
3. When access token expires → call `/refresh` with refresh token
4. On logout → refresh token blacklisted in Redis

### FastAPI Dependency
```python
# app/api/deps.py
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Decode JWT, fetch user from DB, return User model."""
    ...
```

## 4. Security Considerations

- Rate limit login endpoint: 5 attempts per minute per IP
- Rate limit register endpoint: 3 per hour per IP
- Passwords never logged or returned in responses
- Tokens never stored in localStorage on frontend (use httpOnly cookies or secure memory)
- CORS configured to only allow frontend origin

## 5. Frontend Integration

### Pages
- `/login` — Email + password form
- `/register` — Registration form
- `/` — Redirect to dashboard if authenticated, login if not

### Auth Context
```typescript
// Frontend auth state management
interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
}
```

### Route Protection
- Middleware in Next.js to check auth on protected routes
- Redirect to `/login` if not authenticated
- Redirect to `/dashboard` if authenticated and on `/login`

## 6. Acceptance Criteria

- [ ] User can register with email/password
- [ ] User can login and receive JWT tokens
- [ ] Protected endpoints reject requests without valid token
- [ ] Refresh token flow works
- [ ] Logout invalidates the session
- [ ] Passwords are hashed with bcrypt
- [ ] Rate limiting on auth endpoints
- [ ] Frontend login/register pages functional
- [ ] Auth state persists across page refreshes
- [ ] Account deletion cascades to connected accounts

## 7. Out of Scope (MVP)
- OAuth social login (Google, GitHub)
- Email verification
- Password reset flow
- 2FA
- Role-based access control
