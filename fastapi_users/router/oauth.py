from typing import Callable, Dict, List, Optional, Type, cast
from fastapi.responses import JSONResponse

import jwt
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
    Form,
)
from httpx_oauth.integrations.fastapi import OAuth2AuthorizeCallback
from httpx_oauth.oauth2 import BaseOAuth2

from fastapi_users import models
from fastapi_users.authentication import Authenticator
from fastapi_users.db import BaseUserDatabase
from fastapi_users.password import generate_password, get_password_hash
from fastapi_users.router.common import ErrorCode, run_handler
from fastapi_users.utils import JWT_ALGORITHM, generate_jwt
from pydantic import BaseModel

STATE_TOKEN_AUDIENCE = "fastapi-users:oauth-state"


class Code(BaseModel):
    code: str


def generate_state_token(
    data: Dict[str, str], secret: str, lifetime_seconds: int = 3600
) -> str:
    data["aud"] = STATE_TOKEN_AUDIENCE
    return generate_jwt(data, secret, lifetime_seconds, JWT_ALGORITHM)


def decode_state_token(token: str, secret: str) -> Dict[str, str]:
    return jwt.decode(
        token,
        secret,
        audience=STATE_TOKEN_AUDIENCE,
        algorithms=[JWT_ALGORITHM],
    )


def get_oauth_router(
    oauth_client: BaseOAuth2,
    user_db: BaseUserDatabase[models.BaseUserDB],
    user_db_model: Type[models.BaseUserDB],
    authenticator: Authenticator,
    state_secret: str,
    redirect_url: str = None,
    after_register: Optional[Callable[[models.UD, Request], None]] = None,
) -> APIRouter:
    """Generate a router with the OAuth routes."""
    router = APIRouter()
    callback_route_name = f"{oauth_client.name}-callback"

    if redirect_url is not None:
        oauth2_authorize_callback = OAuth2AuthorizeCallback(
            oauth_client,
            redirect_url=redirect_url,
        )
    else:
        oauth2_authorize_callback = OAuth2AuthorizeCallback(
            oauth_client,
            route_name=callback_route_name,
        )

    @router.get("/authorize")
    async def authorize(
        request: Request,
        authentication_backend: str = "jwt",
        scopes: List[str] = Query(None),
    ):
        # Check that authentication_backend exists
        backend_exists = False
        for backend in authenticator.backends:
            if backend.name == authentication_backend:
                backend_exists = True
                break
        if not backend_exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

        if redirect_url is not None:
            authorize_redirect_url = redirect_url
        else:
            authorize_redirect_url = request.url_for(callback_route_name)

        state_data = {
            "authentication_backend": authentication_backend,
        }
        state = generate_state_token(state_data, state_secret)
        authorization_url = await oauth_client.get_authorization_url(
            authorize_redirect_url,
            state,
            scopes,
        )

        return {"authorization_url": authorization_url}

    # Apple's dispatchs a POST request to the callback by default
    if oauth_client.name.startswith("apple"):

        @router.post("/callback", name=callback_route_name)
        async def callback_post(
            request: Request,
            response: Response,
            state: str = Form(...),
            code: str = Form(...),
        ):
            # TODO: get redirect_url from request if not provided
            # if redirect_url is None:
            #     redirect_url = request.url_for(callback_route_name)

            token = await oauth_client.get_access_token(code, redirect_url)
            return await _callback_handler(
                request,
                response,
                token,
                state,
            )

    else:

        @router.get("/callback", name=callback_route_name)
        async def callback(
            request: Request,
            response: Response,
            access_token_state=Depends(oauth2_authorize_callback),
        ):
            token, state = access_token_state
            return await _callback_handler(request, response, token, state)

    @router.post("/authorize-code", name=f"{oauth_client.name}-code")
    async def oauth_by_code(
        request: Request,
        response: Response,
        code: str = Form(...),
        authentication_backend: str = "jwt",
    ):
        # https://developers.google.com/identity/protocols/oauth2/openid-connect#exchangecode  # noqa
        state_data = {
            "authentication_backend": authentication_backend,
        }
        state = generate_state_token(state_data, state_secret)

        # TODO: get redirect_url from request if not provided
        # if redirect_url is None:
        #     redirect_url = request.url_for(callback_route_name)

        oauth_client_payload = await oauth_client.get_access_token(
            redirect_uri=redirect_url,
            code=code,
        )

        return await _callback_handler(request, response, oauth_client_payload, state)

    async def _callback_handler(
        request: Request,
        response: Response,
        token: dict,
        state: str,
    ):
        account_id, account_email = await oauth_client.get_id_email(token)

        try:
            state_data = decode_state_token(state, state_secret)
        except jwt.DecodeError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

        user = await user_db.get_by_oauth_account(oauth_client.name, account_id)

        new_oauth_account = models.BaseOAuthAccount(
            oauth_name=oauth_client.name,
            access_token=token["access_token"],
            expires_at=token.get("expires_at"),
            refresh_token=token.get("refresh_token"),
            account_id=account_id,
            account_email=account_email,
            state_data=jwt.decode(
                token.get("id_token"), options={"verify_signature": False}
            ),
        )

        if not user:
            user = await user_db.get_by_email(account_email)
            if user:
                # Link account
                user.oauth_accounts.append(new_oauth_account)  # type: ignore
                await user_db.update(user)
            else:
                # Create account
                password = generate_password()
                user = user_db_model(
                    email=account_email,
                    hashed_password=get_password_hash(password),
                    oauth_accounts=[new_oauth_account],
                )
                await user_db.create(user)
                if after_register:
                    await run_handler(after_register, user, request)
        else:
            # Update oauth
            updated_oauth_accounts = []
            for oauth_account in user.oauth_accounts:  # type: ignore
                if oauth_account.account_id == account_id:
                    updated_oauth_accounts.append(new_oauth_account)
                else:
                    updated_oauth_accounts.append(oauth_account)
            user.oauth_accounts = updated_oauth_accounts  # type: ignore
            await user_db.update(user)

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorCode.LOGIN_BAD_CREDENTIALS,
            )

        # Authenticate
        for backend in authenticator.backends:
            if backend.name == state_data["authentication_backend"]:
                return await backend.get_login_response(
                    cast(models.BaseUserDB, user), response
                )

    return router
