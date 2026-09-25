"""Backend policy and job-scoped routing; never starts services or changes the environment."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import os
import re
from urllib.parse import urlsplit

_active = ContextVar('genesis_backend', default=None)


@dataclass(frozen=True)
class Route:
    destination: str
    url: str
    allow_start: bool = False


def remote_url():
    route = _active.get()
    if route is not None:
        return route.url if route.destination == 'RUNPOD' else ''
    return os.environ.get('GENESIS_COMFY_URL', '').strip()


def local_start_allowed():
    route = _active.get()
    return route is None or route.allow_start


@contextmanager
def use_route(route):
    token = _active.set(route)
    try:
        yield
    finally:
        _active.reset(token)


def normalize_endpoint(value):
    value = value.strip().rstrip('/')
    if not value:
        return ''
    if re.fullmatch(r'[a-z0-9]{10,32}', value):
        value = f'https://{value}-3000.proxy.runpod.net'
    parsed = urlsplit(value)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Use a ComfyUI endpoint without credentials, query parameters or fragments.')
    if not parsed.hostname or (parsed.scheme != 'https' and not (
        parsed.scheme == 'http' and parsed.hostname in {'localhost', '127.0.0.1', '::1'}
    )):
        raise ValueError('Enter an HTTPS ComfyUI URL, a pod ID, or a local tunnel URL.')
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError('The endpoint port is invalid.') from exc
    return value


def choose_route(mode, model, local_models, remote_models, local_ready, remote_ready,
                 endpoint, local_safe=True):
    """AUTO uses an already-running safe local backend, then the configured remote."""
    if mode not in {'AUTO', 'LOCAL', 'RUNPOD'}:
        raise ValueError('Choose AUTO, LOCAL or RUNPOD.')
    if mode != 'RUNPOD' and model in local_models and local_safe:
        if local_ready or mode == 'LOCAL':
            return Route('LOCAL', '', mode == 'LOCAL')
    if mode != 'LOCAL' and endpoint and remote_ready and model in remote_models:
        return Route('RUNPOD', endpoint)
    if mode == 'LOCAL' and not local_safe:
        raise ValueError('This model is blocked locally by the GPU safety policy. Choose RunPod.')
    raise ValueError(f'{mode}: no ready backend with this model. Check the backend and model catalog.')
