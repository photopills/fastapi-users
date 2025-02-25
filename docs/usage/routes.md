# Routes

You'll find here the routes exposed by **FastAPI Users**. Note that you can also review them through the [interactive API docs](https://fastapi.tiangolo.com/tutorial/first-steps/#interactive-api-docs).

## Auth router

Each [authentication backend](../configuration/authentication/index.md) you [generate a router for](../configuration/routers/auth.md) will produce the following routes. Take care about the prefix you gave it, especially if you have several backends.

### `POST /login`

Login a user against the method named `name`. Check the corresponding [authentication method](../configuration/authentication/index.md) to view the success response.

!!! abstract "Payload (`application/x-www-form-urlencoded`)"
    ```
    username=king.arthur@camelot.bt&password=guinevere
    ```

!!! fail "`422 Validation Error`"

!!! fail "`400 Bad Request`"
    Bad credentials or the user is inactive.

    ```json
    {
        "detail": "LOGIN_BAD_CREDENTIALS"
    }
    ```

!!! fail "`400 Bad Request`"
    The user is not verified.

    ```json
    {
        "detail": "LOGIN_USER_NOT_VERIFIED"
    }
    ```

### `POST /logout`

Logout the authenticated user against the method named `name`. Check the corresponding [authentication method](../configuration/authentication/index.md) to view the success response.

!!! fail "`401 Unauthorized`"
    Missing token or inactive user.

!!! success "`200 OK`"
    The logout process was successful.


!!! tip
    Some backend (like JWT) won't produce this route.

## Register router

### `POST /register`

Register a new user. Will call the `on_after_register` [handler](../configuration/user-manager.md#on_after_register) on successful registration.

!!! abstract "Payload"
    ```json
    {
        "email": "king.arthur@camelot.bt",
        "password": "guinevere"
    }
    ```

!!! success "`201 Created`"
    ```json
    {
        "id": "57cbb51a-ab71-4009-8802-3f54b4f2e23",
        "email": "king.arthur@camelot.bt",
        "is_active": true,
        "is_superuser": false
    }
    ```

!!! fail "`422 Validation Error`"

!!! fail "`400 Bad Request`"
    A user already exists with this email.

    ```json
    {
        "detail": "REGISTER_USER_ALREADY_EXISTS"
    }
    ```

!!! fail "`400 Bad Request`"
    [Password validation](../configuration/user-manager.md#validate_password) failed.

    ```json
    {
        "detail": {
            "code": "REGISTER_INVALID_PASSWORD",
            "reason": "Password should be at least 3 characters"
        }
    }
    ```

## Reset password router

### `POST /forgot-password`

Request a reset password procedure. Will generate a temporary token and call the `on_after_forgot_password` [handler](../configuration/user-manager.md#on_after_forgot_password) if the user exists.

To prevent malicious users from guessing existing users in your database, the route will always return a `202 Accepted` response, even if the user requested does not exist.

!!! abstract "Payload"
    ```json
    {
        "email": "king.arthur@camelot.bt"
    }
    ```

!!! success "`202 Accepted`"

### `POST /reset-password`

Reset a password. Requires the token generated by the `/forgot-password` route.

!!! abstract "Payload"
    ```json
    {
        "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiOTIyMWZmYzktNjQwZi00MzcyLTg2ZDMtY2U2NDJjYmE1NjAzIiwiYXVkIjoiZmFzdGFwaS11c2VyczphdXRoIiwiZXhwIjoxNTcxNTA0MTkzfQ.M10bjOe45I5Ncu_uXvOmVV8QxnL-nZfcH96U90JaocI",
        "password": "merlin"
    }
    ```

!!! success "`200 OK`"

!!! fail "`422 Validation Error`"

!!! fail "`400 Bad Request`"
    Bad or expired token.

    ```json
    {
        "detail": "RESET_PASSWORD_BAD_TOKEN"
    }
    ```

!!! fail "`400 Bad Request`"
    [Password validation](../configuration/user-manager.md#validate_password) failed.

    ```json
    {
        "detail": {
            "code": "REGISTER_INVALID_PASSWORD",
            "reason": "Password should be at least 3 characters"
        }
    }
    ```

## Verify router

### `POST /request-verify-token`

Request a user to verify their e-mail. Will generate a temporary token and call the `on_after_request_verify` [handler](../configuration/user-manager.md#on_after_request_verify) if the user **exists**, **active** and **not already verified**.

To prevent malicious users from guessing existing users in your database, the route will always return a `202 Accepted` response, even if the user requested does not exist, not active or already verified.

!!! abstract "Payload"
    ```json
    {
        "email": "king.arthur@camelot.bt"
    }
    ```

!!! success "`202 Accepted`"

### `POST /verify`

Verify a user. Requires the token generated by the `/request-verify-token` route. Will call the call the `on_after_verify` [handler](../configuration/user-manager.md#on_after_verify) on success.

!!! abstract "Payload"
    ```json
    {
        "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiOTIyMWZmYzktNjQwZi00MzcyLTg2ZDMtY2U2NDJjYmE1NjAzIiwiYXVkIjoiZmFzdGFwaS11c2VyczphdXRoIiwiZXhwIjoxNTcxNTA0MTkzfQ.M10bjOe45I5Ncu_uXvOmVV8QxnL-nZfcH96U90JaocI"
    }
    ```

!!! success "`200 OK`"

!!! fail "`422 Validation Error`"

!!! fail "`400 Bad Request`"
    Bad token, not existing user or not the e-mail currently set for the user.

    ```json
    {
        "detail": "VERIFY_USER_BAD_TOKEN"
    }
    ```

!!! fail "`400 Bad Request`"
    The user is already verified.

    ```json
    {
        "detail": "VERIFY_USER_ALREADY_VERIFIED"
    }
    ```

## OAuth router

Each OAuth router you define will expose the two following routes.

### `GET /authorize`

Return the authorization URL for the OAuth service where you should redirect your user.

!!! abstract "Query parameters"
    * `authentication_backend`: `name` property of a defined [authentication method](../configuration/authentication/index.md) to use to authenticate the user on successful callback. Usually `jwt` or `cookie`.
    * `scopes`: Optional list of scopes to ask for. Expected format: `scopes=a&scopes=b`.

!!! success "`200 OK`"
    ```json
    {
        "authorization_url": "https://www.tintagel.bt/oauth/authorize?client_id=CLIENT_ID&scopes=a+b&redirect_uri=https://www.camelot.bt/oauth/callback"
    }
    ```

!!! fail "`422 Validation Error`"
    Invalid parameters - e.g. unknown authentication backend.

### `GET /callback`

Handle the OAuth callback.

!!! abstract "Query parameters"
    * `code`: OAuth callback code.
    * `state`: State token.
    * `error`: OAuth error.

Depending on the situation, several things can happen:

* The OAuth account exists in database and is linked to a user:
    * OAuth account is updated in database with fresh access token.
    * The user is authenticated following the chosen [authentication method](../configuration/authentication/index.md).
* The OAuth account doesn't exist in database but a user with the same email address exists:
    * OAuth account is linked to the user.
    * The user is authenticated following the chosen [authentication method](../configuration/authentication/index.md).
* The OAuth account doesn't exist in database and no user with the email address exists:
    * A new user is created and linked to the OAuth account.
    * The user is authenticated following the chosen [authentication method](../configuration/authentication/index.md).

!!! fail "`400 Bad Request`"
    Invalid token.

!!! fail "`400 Bad Request`"
    User is inactive.

    ```json
    {
        "detail": "LOGIN_BAD_CREDENTIALS"
    }
    ```

## Users router

### `GET /me`

Return the current authenticated active user.

!!! success "`200 OK`"
    ```json
    {
        "id": "57cbb51a-ab71-4009-8802-3f54b4f2e23",
        "email": "king.arthur@camelot.bt",
        "is_active": true,
        "is_superuser": false
    }
    ```

!!! fail "`401 Unauthorized`"
    Missing token or inactive user.

### `PATCH /me`

Update the current authenticated active user.

!!! abstract "Payload"
    ```json
    {
        "email": "king.arthur@tintagel.bt",
        "password": "merlin"
    }
    ```

!!! success "`200 OK`"
    ```json
    {
        "id": "57cbb51a-ab71-4009-8802-3f54b4f2e23",
        "email": "king.arthur@tintagel.bt",
        "is_active": true,
        "is_superuser": false
    }
    ```

!!! fail "`401 Unauthorized`"
    Missing token or inactive user.


!!! fail "`400 Bad Request`"
    [Password validation](../configuration/user-manager.md#validate_password) failed.

    ```json
    {
        "detail": {
            "code": "UPDATE_USER_INVALID_PASSWORD",
            "reason": "Password should be at least 3 characters"
        }
    }
    ```

!!! fail "`400 Bad Request`"
    A user with this email already exists.
    ```json
    {
        "detail": "UPDATE_USER_EMAIL_ALREADY_EXISTS"
    }
    ```

!!! fail "`422 Validation Error`"

### `GET /{user_id}`

Return the user with id `user_id`.

!!! success "`200 OK`"
    ```json
    {
        "id": "57cbb51a-ab71-4009-8802-3f54b4f2e23",
        "email": "king.arthur@camelot.bt",
        "is_active": true,
        "is_superuser": false
    }
    ```

!!! fail "`401 Unauthorized`"
    Missing token or inactive user.

!!! fail "`403 Forbidden`"
    Not a superuser.

!!! fail "`404 Not found`"
    The user does not exist.

### `PATCH /{user_id}`

Update the user with id `user_id`.

!!! abstract "Payload"
    ```json
    {
        "email": "king.arthur@tintagel.bt",
        "password": "merlin",
        "is_active": false,
        "is_superuser": true
    }
    ```

!!! success "`200 OK`"
    ```json
    {
        "id": "57cbb51a-ab71-4009-8802-3f54b4f2e23",
        "email": "king.arthur@camelot.bt",
        "is_active": false,
        "is_superuser": true
    }
    ```

!!! fail "`401 Unauthorized`"
    Missing token or inactive user.

!!! fail "`403 Forbidden`"
    Not a superuser.

!!! fail "`404 Not found`"
    The user does not exist.

!!! fail "`400 Bad Request`"
    [Password validation](../configuration/user-manager.md#validate_password) failed.

    ```json
    {
        "detail": {
            "code": "UPDATE_USER_INVALID_PASSWORD",
            "reason": "Password should be at least 3 characters"
        }
    }
    ```

!!! fail "`400 Bad Request`"
    A user with this email already exists.
    ```json
    {
        "detail": "UPDATE_USER_EMAIL_ALREADY_EXISTS"
    }
    ```

### `DELETE /{user_id}`

Delete the user with id `user_id`.

!!! success "`204 No content`"

!!! fail "`401 Unauthorized`"
    Missing token or inactive user.

!!! fail "`403 Forbidden`"
    Not a superuser.

!!! fail "`404 Not found`"
    The user does not exist.
