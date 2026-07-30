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

## 4a. Google OAuth Login (Consumer / Space)

### Actors
- **Teacher or Student**
- **Google**
- **Platform**

### Preconditions
- None (works for both first-time and returning users).

### Steps
1. User authenticates with Google; platform receives a verified Google `sub` (id) and email.
2. Platform looks up `SocialAccount` by `provider='google'` + `provider_id=sub`.
3. **If linked**: resolve the account directly by the linked `user_uid`.
4. **If not linked but email matches an existing account**: create a `SocialAccount` link to that existing account. The account's password is left untouched.
5. **If no match at all**: create a new account with `password=make_password(None)` (an unusable password hash) and create the `SocialAccount` link.
6. Platform issues JWT tokens for the resolved account.

### Notes
- A Google-only account (never set a real password) is identified indirectly via `is_password_usable(password)` — there is no explicit `auth_provider` field.
- Step 4 auto-links Google to an existing email/password account without additional confirmation.

---

## 4b. Change Password

### Actors
- **Teacher or Student** (authenticated)
- **Platform**

### Preconditions
- User is authenticated (valid JWT).

### Steps
1. User submits `current_password`, `new_password`, `confirm_password`.
2. Platform checks whether the account currently has a usable password (`is_password_usable`).
3. **If usable** (normal account): `current_password` must match, and `new_password` must differ from it.
4. **If not usable** (Google-only account that never set a real password): `current_password` is not required — this call sets the account's first real password.
5. Platform hashes and saves `new_password`.

### Edge Cases
- **Google-only account**: can now set a password directly while logged in, without needing `current_password`. Once set, subsequent calls require `current_password` like a normal account.
- **Wrong current_password** (normal account): rejected with a field error.
- **Same as current password**: rejected (normal account only).

---

## 4c. Forgot / Reset Password via OTP

### Actors
- **Teacher or Student**
- **Platform**

### Steps
1. User requests an OTP for their email (`request_otp`). Platform responds with a generic message regardless of whether the email exists, to avoid enumeration.
2. User submits the OTP (`verify_otp`); platform issues a short-lived `reset_token` on success.
3. User submits `reset_token` + `new_password` (`reset_password`); platform sets the new password unconditionally — no `current_password` or password-usability check.

### Notes
- Works identically for Google-only accounts and normal accounts: this is the intended account-recovery path when a user has lost access to both their password and their Google account.
- This flow does not check `is_password_usable`, by design — it is the "recovery" path, so no prior credential is required.

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
