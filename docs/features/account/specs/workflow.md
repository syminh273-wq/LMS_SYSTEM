# Account Module — Workflows

---

## 1. Space Registration

### Actors
- **Teacher** (prospective Space account holder)
- **Platform**

### Preconditions
- No existing Space account with the same email.

### Steps
1. Teacher submits registration form with email and password.
2. Platform validates input (email format, password strength, email uniqueness).
3. Platform creates a `Space` record with `is_active = True` and `is_verified = False`.
4. Platform generates a JWT access token and refresh token.
5. Tokens are returned to the teacher.
6. Teacher is now authenticated and can create classrooms.

### Edge Cases
- **Duplicate email**: Registration is rejected with a validation error on the `email` field.
- **Weak password**: Registration is rejected with a password policy error.

---

## 2. Space Login

### Actors
- **Teacher**
- **Platform**

### Preconditions
- Space account exists and `is_active = True`.

### Steps
1. Teacher submits email and password.
2. Platform looks up the Space by email.
3. Platform verifies the password hash.
4. Platform issues a new JWT access token and refresh token.
5. Tokens are returned.

### Edge Cases
- **Account not found**: Returns a generic authentication error (does not reveal whether email exists).
- **Wrong password**: Returns a generic authentication error.
- **Account inactive**: Returns a 401 with an account status error.

---

## 3. Consumer Registration

### Actors
- **Student** (prospective Consumer account)
- **Platform**

### Preconditions
- No existing Consumer account with the same email.

### Steps
1. Student submits registration form with email and password.
2. Platform validates input.
3. Platform creates a `Consumer` record with `role = student`, `is_active = True`, `is_verified = False`.
4. Platform generates JWT tokens.
5. Tokens are returned.

### Edge Cases
- **Duplicate email or username**: Registration rejected with a field-level validation error.

---

## 4. Consumer Login

### Actors
- **Student**
- **Platform**

### Preconditions
- Consumer account exists and `is_active = True`.

### Steps
1. Student submits email and password.
2. Platform looks up the Consumer by email.
3. Platform verifies the password hash.
4. Platform issues JWT tokens.
5. Tokens are returned.

### Edge Cases
- Same as Space Login edge cases.

---

## 5. Profile Update

### Actors
- **Teacher or Student**
- **Platform**

### Preconditions
- User is authenticated (valid JWT token).

### Steps
1. User submits a PUT request to the profile endpoint with updated fields.
2. Platform validates the token and resolves the account.
3. Platform validates the updated fields.
4. Platform persists changes to the Cassandra table.
5. Updated profile is returned.

### Edge Cases
- **Slug conflict (Space only)**: If the new slug is already taken, the update is rejected.
- **Partial update**: Only provided fields are updated; others remain unchanged.

---

## 6. Token Refresh

### Actors
- **Teacher or Student**
- **Platform**

### Steps
1. Client submits the refresh token to the token refresh endpoint.
2. Platform validates the refresh token (not expired, valid signature).
3. Platform issues a new access token.
4. New access token is returned.

### Edge Cases
- **Expired refresh token**: Returns 401; user must log in again.
- **Tampered token**: Returns 401.

---

## 7. Account Soft Delete

### Actors
- **Platform (admin action or automated process)**

### Steps
1. Delete action is triggered for a Space or Consumer account.
2. Platform sets `is_deleted = True` and `deleted_at` to current timestamp.
3. Account no longer appears in active queries.
4. JWT tokens issued before deletion will fail to resolve the user and return 401.

### Edge Cases
- **Reactivation**: `is_deleted` can be set back to `False` if account is to be restored.
