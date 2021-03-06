import os
import random

import aiofiles
from sanic.request import Request

from amyrose.core.models import Account, VerificationSession, AuthenticationSession
from amyrose.core.utils import random_str, request_ip

verification_cache_path = './resources/verification/'


async def verification_init():
    """
    Generates up to 100 verification code variations as string and image within their respective folders if empty.
    """
    if not os.path.exists(verification_cache_path):
        os.makedirs(verification_cache_path)
        async with aiofiles.open(verification_cache_path + 'codes.txt', mode="w") as f:
            for i in range(100):
                random_string = random_str(7)
                await f.write(random_string + '\n' if i < 99 else random_string)


async def request_verification(request: Request, account: Account = None):
    """
    Creates a verification session associated with an account. Renders account unverified.

    :param request: Sanic request parameter.

    :param account: The account that requires verification. If none, will retrieve account from verification or
    authentication session.

    :return: account, verification_session
    """
    if account is None:
        try:
            decoded_session = VerificationSession().decode_raw(request)
        except VerificationSession.DecodeError as e:
            decoded_session = AuthenticationSession().decode_raw(request)
        account = await Account.filter(uid=decoded_session.get('parent_uid')).first()
    account.verified = False
    await account.save(update_fields=['verified'])
    verification_session = await VerificationSession.create(code=await random_cached_code(),
                                                            parent_uid=account.uid, ip=request_ip(request))
    return account, verification_session


async def random_cached_code():
    """
    Retrieves a random verification code from the generated captcha list,

    :return: verification_code_str
    """
    async with aiofiles.open(verification_cache_path + 'codes.txt', mode="r") as f:
        return random.choice([line.strip() async for line in f])


async def verify_account(request: Request):
    """
    Verifies an account for use using a code sent via email or text.

    :param request: Sanic request parameter. All request bodies are sent as form-data with the following argument: code.

    :raises SessionError:

    :return: account, verification_session
    """

    verification_session = await VerificationSession().decode(request)
    account = await Account.filter(uid=verification_session.parent_uid).first()
    if verification_session.code != request.form.get('code'):
        raise VerificationSession.VerificationAttemptError()
    else:
        VerificationSession.ErrorFactory(verification_session)
    account.verified = True
    verification_session.valid = False
    await account.save(update_fields=['verified'])
    await verification_session.save(update_fields=['valid'])
    return account, verification_session
