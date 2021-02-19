from typing import TypeVar, Generic, Type

import bcrypt
from sanic.request import Request
from amyrose.core.models import Account, VerificationSession, AuthenticationSession, Role, Permission, Session, \
    CaptchaSession
from amyrose.core.utils import request_ip

T = TypeVar('T')


class DTO(Generic[T]):

    def __init__(self, t: Type[T]):
        self.t = t

    async def get_all(self):
        """
        Returns a list of models.

        :return: List[T]
        """
        return await self.t().filter(deleted=False).all()

    async def get_all_by_parent(self, parent_uid: str):
        """
        Retrieves a list of models via parent uid.

        :param parent_uid: Parent uid of model.

        :return: T
        """
        return await self.t().filter(parent_uid=parent_uid, deleted=False).all()

    async def get(self, uid: str):
        """
        Retrieves a model via uid.

        :param uid: Uid of model.

        :return: T
        """
        return await self.t().filter(uid=uid, deleted=False).first()

    async def get_by_parent(self, parent_uid: str):
        """
        Retrieves a model via parent uid.

        :param parent_uid: Parent uid of model.

        :return: T
        """
        return await self.t().filter(parent_uid=parent_uid, deleted=False).first()

    def check_for_empty(self, **kwargs):
        for key, value in kwargs.items():
            if value is not None:
                if not isinstance(value, bool) and not value:
                    raise self.t.EmptyEntryError(key.title() + ' is empty!')

    async def create(self, **kwargs):
        """
        Initializes a model and creates in database.

        :param kwargs: Model parameters.

        :return: T
        """
        self.check_for_empty(**kwargs)
        return await self.t().create(**kwargs)

    async def update(self, uid: str, **kwargs):
        """
        Updates a model in the database.

        :param uid: Uid of model being updated in database.

        :param kwargs: Model parameters to be updated.

        :return: T
        """
        self.check_for_empty(**kwargs)
        return await self.t().filter(uid=uid).update(**kwargs)

    async def delete(self, uid: str):
        """
        Renders a model inoperable while remaining in the database.

        :param uid: Uid of model being deleted.

        :return: T
        """
        return await self.update(uid, deleted=True)


class CaptchaSessionDTO(DTO):
    def __init__(self):
        super().__init__(CaptchaSession)

    async def get_client_img(self, request):
        """
        Retrieves image path of client captcha.

        :return: captcha_img_path
        """
        captcha_session = await CaptchaSession().decode(request)
        return './resources/captcha/img/' + captcha_session.captcha + '.png'


class AccountDTO(DTO):
    def __init__(self):
        super().__init__(Account)

    async def disable(self, account: Account):
        """
        Renders an account inoperable while remaining retrievable.

        :param account: account  being disabled

        :return: account
        """
        return await self.update(account.uid, disabled=True)

    async def enable(self, account: Account):
        """
        Enabled an account after being disabled.

        :param account: account being enabled

        :return: account
        """
        return await self.update(account.uid, disabled=False)

    async def get_by_email(self, email: str):
        """
        Retrieves account via email.

        :param email: Email of account being retrieved.

        :return: T
        """
        return await self.t().filter(email=email).first()

    async def get_client(self, request: Request):
        """
        Retrieves account information from an authentication session found within cookie.
        :param request: Sanic request parameter.
        :return: account
        """
        try:
            authentication_session = await AuthenticationSession().decode(request, raw=True)
            account = await self.get(authentication_session.get('parent_uid'))
        except AuthenticationSession.SessionError:
            account = None
        return account

    async def change_password(self, uid: str, new_password):
        """
        Changes account password.
        :param uid: Uid of account.
        :param new_password: Password to replace current account password with.
        :return: account
        """
        return await self.update(uid, password=self.hash_password(new_password))

    def hash_password(self, password):
        """
        Turns passed text into hashed password
        :param password: Password to be hashed.
        :return: hashed
        """
        if password:
            return bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
        else:
            raise self.t.EmptyEntryError('password is empty!')


class VerificationSessionDTO(DTO):
    def __init__(self):
        super().__init__(VerificationSession)


class AuthenticationSessionDTO(DTO):
    def __init__(self):
        super().__init__(AuthenticationSession)

    async def in_known_location(self, request: Request):
        """
        Checks if client using session is in a known location (ip address). Prevents cookie jacking.

        :param request: Sanic request parameter.

        :raises UnknownLocationError:
        """
        authentication_session = await AuthenticationSession().decode(request, True)
        if not await AuthenticationSession.filter(ip=request_ip(request),
                                                  parent_uid=authentication_session.get('parent_uid')).exists():
            raise Session.UnknownLocationError('AuthenticationSession')


class RoleDTO(DTO):
    def __init__(self):
        super().__init__(Role)

    async def has_role(self, account: Account, role: str):
        """
        Checks if the account has the required role being requested.

        :param account: Account being checked.

        :param role: The role that is required for validation.

        :return: has_role
        """
        return await self.t().filter(parent_uid=account.uid, name=role).exists()

    async def assign_role(self, account: Account, role: str):
        """
        Creates a role associated with an account

        :param account: Account associated with role.

        :param role: role to be associated with account.

        :return: role
        """

        return await self.create(parent_uid=account.uid, name=role)


class PermissionDTO(DTO):

    def __init__(self):
        super().__init__(Permission)

    async def assign_permission(self, account: Account, permission: str):
        """
        Creates a permission associated with an account

        :param account: Account associated with role.

        :param permission: permission to be associated with account.

        :return: permission
        """
        return await self.create(parent_uid=account.uid, name=permission)

    async def get_permissions(self, account: Account):
        """
        Retrieves all permissions associated with an account.

        :param account: Account associated with permissions

        :return: permissions
        """
        return await self.t().filter(parent_uid=account.uid).all()
