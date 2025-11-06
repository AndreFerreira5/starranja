from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .exceptions import InvalidTokenError, TokenExpiredError
from .services.token import TokenService

TOKEN_SERVICE = TokenService()


security_scheme = HTTPBearer(scheme_name="PASETO Token", auto_error=False)


class AuthDependency:
    """
    Dependência FastAPI para verificar e decodificar o PASETO Token.
    Se o token for válido, retorna o payload decodificado.
    """

    async def __call__(
        self,
        auth: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
    ) -> dict:
        if auth is None or auth.scheme.lower() != "bearer" or not auth.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de autenticação ausente ou inválido."
            )

        token = auth.credentials

        try:
            payload = TOKEN_SERVICE.verify_token(token)
            return payload

        except TokenExpiredError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de acesso expirado.")

        except InvalidTokenError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token inválido: {e}")

        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha interna na validação do token."
            )


auth_required = AuthDependency()
