import abc
import sys
import time
import uuid
import json
from typing import Any, Callable, Dict, Iterator, Mapping, MutableMapping, Optional, Union, cast

import psycopg2.extras
from aiohttp import web
from aiohttp.web_middlewares import _Handler, _Middleware

from build.lib.mining import session


if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


class Session(MutableMapping[str, Any]):

    """Session dict-like object."""

    def __init__(
        self,
        identity: Optional[Any],
        *,
        user_id: Optional[int] = None,
        data: Optional[Mapping[str, Any]] = {},
        new: bool = False,
        is_customer: bool = True,
        max_age: Optional[int] = None
    ) -> None:
        self._changed = False
        self._mapping: Dict[str, Any] = {}
        self._identity = identity
        self._new = new if data != {} else True
        self._is_customer = is_customer
        self._max_age = max_age
        self._user_id = user_id or (data.get('userId', None) if data else None)
        created = data.get('createdAt', None) if data else None
        expiredAt = data.get('expiredAt', None) if data else None
        session_data = data.get('session', None) if data else None
        now = int(time.time())
        if expiredAt is not None and expiredAt < now:
            raise web.HTTPUnauthorized(reason='登录失效，请重新登录')
        if self._new or created is None:
            self._created = now
        else:
            self._created = created
        if session_data is not None:
            self._mapping.update(session_data)

    def __repr__(self) -> str:
        return '<{} [new:{}, changed:{}, created:{}] {!r}>'.format(
            self.__class__.__name__, self.new, self._changed, self.created, self._mapping)

    @ property
    def new(self) -> bool:
        return self._new

    @ property
    def identity(self) -> Optional[Any]:
        return self._identity

    @ property
    def user_id(self) -> Optional[int]:
        return self._user_id

    @ property
    def created(self) -> int:
        return self._created

    @ property
    def is_customer(self) -> bool:
        return self._is_customer

    @ property
    def empty(self) -> bool:
        return not bool(self._mapping)

    def changed(self) -> None:
        self._changed = True

    @ property
    def max_age(self) -> Optional[int]:
        return self._max_age

    @ max_age.setter
    def max_age(self, value: Optional[int]) -> None:
        self._max_age = value

    def invalidate(self) -> None:
        self._changed = True
        self._mapping = {}

    def set_new_identity(self, identity: Optional[Any]) -> None:
        if not self._new:
            raise RuntimeError(
                "Can't change identity for a session which is not new")

        self._identity = identity

    def __len__(self) -> int:
        return len(self._mapping)

    def __iter__(self) -> Iterator[str]:
        return iter(self._mapping)

    def __contains__(self, key: object) -> bool:
        return key in self._mapping

    def __getitem__(self, key: str) -> Any:
        return self._mapping[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._mapping[key] = value
        self._changed = True

    def __delitem__(self, key: str) -> None:
        del self._mapping[key]
        self._changed = True


SESSION_KEY = 'aiohttp_session'
STORAGE_KEY = 'aiohttp_session_storage'


async def get_session(request: web.Request, is_customer: bool = True) -> Session:
    session = request.get(SESSION_KEY)
    if session is None:
        storage = request.get(STORAGE_KEY)
        if storage is None:
            raise RuntimeError(
                "Install aiohttp_session middleware "
                "in your aiohttp.web.Application")

        session = await storage.load_session(request, is_customer)
        if not isinstance(session, Session):
            raise RuntimeError(
                "Installed {!r} storage should return session instance "
                "on .load_session() call, got {!r}.".format(storage, session))
        request[SESSION_KEY] = session
    return session


async def new_session(request: web.Request, user_id: int, is_customer: bool = True) -> Session:
    storage = request.get(STORAGE_KEY)
    if storage is None:
        raise RuntimeError(
            "Install aiohttp_session middleware "
            "in your aiohttp.web.Application")

    session = await storage.new_session(user_id, is_customer)
    if not isinstance(session, Session):
        raise RuntimeError(
            "Installed {!r} storage should return session instance "
            "on .load_session() call, got {!r}.".format(storage, session))
    request[SESSION_KEY] = session
    return session


async def get_platform_session(request: web.Request) -> Session:
    return await get_session(request, False)


async def new_platform_session(request: web.Request, user_id: int) -> Session:
    return await new_session(request, user_id, False)


def session_middleware(storage: 'AbstractStorage') -> _Middleware:
    if not isinstance(storage, AbstractStorage):
        raise RuntimeError("Expected AbstractStorage got {}".format(storage))

    @ web.middleware
    async def factory(
        request: web.Request,
        handler: _Handler
    ) -> web.StreamResponse:
        request[STORAGE_KEY] = storage
        raise_response = False
        # TODO aiohttp 4: Remove Union from response, and drop the raise_response variable
        response: Union[web.StreamResponse, web.HTTPException]
        try:
            response = await handler(request)
        except web.HTTPException as exc:
            response = exc
            raise_response = True
        if not isinstance(response, (web.StreamResponse, web.HTTPException)):
            raise RuntimeError(
                "Expect response, not {!r}".format(type(response)))
        if not isinstance(response, (web.Response, web.HTTPException)):
            # likely got websocket or streaming
            return response
        if response.prepared:
            raise RuntimeError(
                "Cannot save session data into prepared response")
        session = request.get(SESSION_KEY)
        if session is not None:
            if session._changed:
                await storage.save_session(request, response, session)
        if raise_response:
            raise cast(web.HTTPException, response)
        return response

    return factory


def setup(app: web.Application, storage: 'AbstractStorage') -> None:
    """Setup the library in aiohttp fashion."""

    app.middlewares.append(session_middleware(storage))


class AbstractStorage(metaclass=abc.ABCMeta):

    def __init__(
        self,
        session_id_getter: Callable[[web.Request], str],
        *,
        max_age: Optional[int] = None,
        encoder: Callable[[object], str] = json.dumps,
        decoder: Callable[[str], Any] = json.loads
    ) -> None:
        self._session_id_getter = session_id_getter
        self._max_age = max_age
        self._encoder = encoder
        self._decoder = decoder

    @ property
    def max_age(self) -> Optional[int]:
        return self._max_age

    async def new_session(self, user_id: int, is_customer: bool = True) -> Session:
        return Session(uuid.uuid4().hex, user_id=user_id, new=True, is_customer=is_customer, max_age=self.max_age)

    @ abc.abstractmethod
    async def load_session(self, request: web.Request, is_customer: bool) -> Session:
        ...

    @ abc.abstractmethod
    async def save_session(self, request: web.Request, response: web.StreamResponse, session: Session) -> None:
        ...


class PgStorage(AbstractStorage):
    """PG storage"""

    def __init__(self, app: web.Application,
                 session_id_getter: Callable[[web.Request], str],
                 *,
                 max_age: Optional[int] = 60 * 60 * 24 * 30,
                 encoder: Callable[[object], str] = psycopg2.extras.Json,
                 decoder: Callable[[str], Any] = json.loads):
        super().__init__(session_id_getter, max_age=max_age, encoder=encoder, decoder=decoder)
        self.app = app

    async def load_session(self, request: web.Request, is_customer: bool) -> Session:
        session_id = self._session_id_getter(request)
        if session_id is None:
            return Session(None, new=True, is_customer=is_customer, max_age=self.max_age)
        else:
            session = await self.app['db'].load_session(session_id, is_customer)
            if not session:
                return Session(None, new=True, is_customer=is_customer, max_age=self.max_age)
            return Session(session_id, new=False, is_customer=is_customer, data=session, max_age=self.max_age)

    async def save_session(self, request: web.Request, response: web.StreamResponse, session: Session) -> None:
        key = session.identity
        if not key:
            key = uuid.uuid4().hex

        if not session.empty:
            await self.app['db'].save_session(key, session.user_id, self._encoder(session._mapping), self.max_age, session.is_customer)
