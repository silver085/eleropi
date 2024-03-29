import asyncio
import logging
import socket
_LOGGER = logging.getLogger(__name__)
import aiohttp

LOGGER = logging.getLogger(__name__)


class NoDeviceAvailable(BaseException):
    pass


class UrlConstants:
    URL_PING = "/device/ping"
    URL_LOGIN = "/users/token"
    URL_GETBLINDS = "/blinds/getblinds"
    TOGGLE_DISCOVERY = "/blinds/indiscovery"
    COMMAND = "/blinds/action/__blindid__/__command__"


class EleroRequestError(BaseException):
    pass


class EleroApiError(ConnectionError):
    pass


class EleroAPI:
    username: str
    password: str
    host: str
    baseUrl: str
    isAuthenticated: bool
    token: str

    def __init__(self, username: str, password: str, host: str = None, autodiscovery: bool = True,
                 isLocal: bool = False):
        self.username = username
        self.password = password
        if autodiscovery:
            try:
                self.host = self._device_available()
            except RuntimeError:
                raise NoDeviceAvailable("Can't find any device over the network")
        else:
            self.host = host
        if not isLocal:
            self.baseUrl = f"http://{self.host}:8000"
        else:
            self.baseUrl = f"http://localhost:8000"

        self.isAuthenticated = False
        self.device_id = None

    async def get_blinds(self):
        url = f"{self.baseUrl}{UrlConstants.URL_GETBLINDS}"
        r = await self._do_request(url=url, method="GET")
        return r["blinds"]

    async def get_blind(self, blindId):
        url = f"{self.baseUrl}{UrlConstants.URL_GETBLINDS}/{blindId}"
        r = await self._do_request(url=url, method="GET")
        return r["blind"]

    @staticmethod
    def _device_available():
        if socket.gethostbyname("raspberrypi.local") is not None: return "raspberrypi.local"
        if socket.gethostbyname("eleropi.local") is not None: return "eleropi.local"
        return None

    async def login(self):
        url = f"{self.baseUrl}{UrlConstants.URL_LOGIN}"
        data = {
            "username": self.username,
            "password": self.password
        }
        r = await self._do_request(url=url, method="POST", data=data, is_json=False)
        LOGGER.debug(f"Got login response: {r}")
        self.isAuthenticated = True
        self.token = r["access_token"]

    async def ping(self):
        url = f"{self.baseUrl}{UrlConstants.URL_PING}"
        r = await self._do_request(url=url, method="GET")
        LOGGER.debug(f"Got ping response: {r}")
        self.device_id = r["device_unique_id"]

    async def start_discovery(self):
        url = f"{self.baseUrl}{UrlConstants.TOGGLE_DISCOVERY}"
        r = await self._do_request(url=url, method="GET")
        if r["discovery_active"]: return
        r = await self._do_request(url=url, method="PUT")
        if not r["discovery_active"]: raise EleroRequestError("Cannot put device in discovery")

    async def stop_discovery(self):
        url = f"{self.baseUrl}{UrlConstants.TOGGLE_DISCOVERY}"
        r = await self._do_request(url=url, method="GET")
        if not r["discovery_active"]: return
        r = await self._do_request(url=url, method="PUT")
        if r["discovery_active"]: raise EleroRequestError("Failed putting device in stop discovery")

    async def send_command(self, blind_id, command):

        url =  f"{self.baseUrl}{UrlConstants.COMMAND}".replace("__blindid__", blind_id).replace("__command__", command)
        _LOGGER.debug(f"Url: {url}")
        r = await self._do_request(url=url, method="PUT")
        return r

    async def _do_request(self, url, method, data=None, is_json: bool = True):
        async with aiohttp.ClientSession() as session:
            if self.isAuthenticated:
                session.headers.update({"WWW-Authenticate": self.token})
            if is_json:
                response = await session.request(url=url, method=method, json=data)
            else:
                response = await session.request(url=url, method=method, data=data)

            if response.status != 200:
                raise EleroRequestError(f"Response: {response.json()}")
            else:
                return await response.json()


class EleroClient:
    api: EleroAPI
    device_id: str
    blinds: None

    def __init__(self, username: str, password: str):
        self.api = EleroAPI(username=username, password=password, isLocal=False)

    async def update(self):
        if not self.api.isAuthenticated:
            await self.api.ping()
            await self.api.login()
            self.device_id = self.api.device_id

        self.blinds = await self.api.get_blinds()

    async def start_discovery(self):
        await self.api.start_discovery()

    async def stop_discovery(self):
        await self.api.stop_discovery()

    async def get_blind(self, blind_id):
        return await self.api.get_blind(blindId=blind_id)

    async def get_blinds(self):
        return await self.api.get_blinds()

    async def send_command(self, blind_id, command):
        return await self.api.send_command(blind_id=blind_id, command=command)

async def test_tasks():
    client = EleroClient("ha_user@local.dns", "ha_user")
    await client.update()
    print(f"Device id {client.device_id}")
    print(f"Blinds: {client.blinds}")
    first_blind = client.blinds[0]
    b_id0 = first_blind["blind_id"]
    blind = await client.get_blind(blind_id=b_id0)
    print(f"Blind update {b_id0}: {blind}")


#loop = asyncio.get_event_loop()
#loop.run_until_complete(test_tasks())
