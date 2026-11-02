from typing import Annotated

from authx import TokenPayload
from fastapi import Depends, HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from shared.auth import auth
from shared.database.session import SessionDep
from users import services
from users.exceptions import UserNotFoundError
from users.models import UserModel


async def get_current_user(
    payload: Annotated[TokenPayload, Depends(auth.access_token_required)],
    session: SessionDep,
) -> UserModel:
    unauthorized = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED, detail="User not found"
    )
    try:
        user_id = int(payload.sub)
    except ValueError:
        # Token was signed by us but does not carry a numeric user id
        raise unauthorized from None
    try:
        return await services.get_user(user_id=user_id, session=session)
    except UserNotFoundError:
        raise unauthorized from None


CurrentUserDep = Annotated[UserModel, Depends(get_current_user)]


async def get_current_admin(current_user: CurrentUserDep) -> UserModel:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="User is not an admin"
        )
    return current_user


CurrentAdminDep = Annotated[UserModel, Depends(get_current_admin)]
