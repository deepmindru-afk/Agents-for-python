# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import asyncio
import logging
import jwt
from datetime import datetime, timezone

from jwt import PyJWKClient, PyJWK, decode, get_unverified_header

from .agent_auth_configuration import AgentAuthConfiguration
from .claims_identity import ClaimsIdentity

logger = logging.getLogger(__name__)


class JwtTokenValidator:

    lock: asyncio.Lock = asyncio.Lock()
    key_cache: dict = {}
    last_refresh_time: float = 0.0

    def __init__(self, configuration: AgentAuthConfiguration):
        self.configuration = configuration

    async def validate_token(self, token: str) -> ClaimsIdentity:

        logger.debug("Validating JWT token.")
        key = await self._get_public_key_or_secret(token)
        decoded_token = jwt.decode(
            token,
            key=key,
            algorithms=["RS256"],
            leeway=300.0,
            options={"verify_aud": False},
        )
        if decoded_token["aud"] != self.configuration.CLIENT_ID:
            logger.error(f"Invalid audience: {decoded_token['aud']}", stack_info=True)
            raise ValueError("Invalid audience.")

        # This probably should return a ClaimsIdentity
        logger.debug("JWT token validated successfully.")
        return ClaimsIdentity(decoded_token, True)

    def get_anonymous_claims(self) -> ClaimsIdentity:
        logger.debug("Returning anonymous claims identity.")
        return ClaimsIdentity({}, False, authentication_type="Anonymous")

    async def _get_public_key_or_secret(self, token: str) -> PyJWK:
        header = get_unverified_header(token)
        unverified_payload: dict = decode(token, options={"verify_signature": False})

        jwksUri = (
            "https://login.botframework.com/v1/.well-known/keys"
            if unverified_payload.get("iss") == "https://api.botframework.com"
            else f"https://login.microsoftonline.com/{self.configuration.TENANT_ID}/discovery/v2.0/keys"
        )
        jwks_client = PyJWKClient(jwksUri)

        key = await JwtTokenValidator.get_key(jwks_client, header["kid"])

        return key

    @classmethod
    async def get_key(cls, jwks_client: PyJWKClient, kid: str) -> PyJWK:
        now = datetime.now(timezone.utc).timestamp()
        if kid in cls.key_cache and cls.last_refresh_time + 3600 > now:
            return cls.key_cache[kid]
        else:
            async with cls.lock:
                if kid in cls.key_cache:
                    return cls.key_cache[kid]
                key = await asyncio.to_thread(jwks_client.get_signing_key, kid)
                cls.key_cache[kid] = key
                return key