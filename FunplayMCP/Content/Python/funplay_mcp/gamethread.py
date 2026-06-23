"""Game-thread marshalling.

Every ``unreal.*`` call must happen on the game (main) thread; touching a
UObject from the HTTP worker thread can hard-crash the editor. We register a
Slate post-tick callback -- which the editor fires once per frame on the game
thread -- and drain a job queue from it. Worker threads submit work via
``run_on_game_thread`` and block only themselves until the next tick runs it."""

import queue
import threading
import traceback

import unreal

_jobs = queue.Queue()
_tick_handle = None
_game_thread_ident = None


def _pump(_delta_seconds):
    """Runs on the GAME THREAD once per editor frame."""
    global _game_thread_ident
    _game_thread_ident = threading.get_ident()
    while True:
        try:
            fn, args, kwargs, box, done = _jobs.get_nowait()
        except queue.Empty:
            break
        try:
            box["value"] = fn(*args, **kwargs)
        except BaseException as exc:  # noqa: BLE001 -- report everything to the caller
            box["error"] = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )
        finally:
            done.set()


def install_pump():
    global _tick_handle
    if _tick_handle is None:
        _tick_handle = unreal.register_slate_post_tick_callback(_pump)


def remove_pump():
    global _tick_handle
    if _tick_handle is not None:
        try:
            unreal.unregister_slate_post_tick_callback(_tick_handle)
        except Exception:  # noqa: BLE001
            pass
        _tick_handle = None


def is_on_game_thread():
    return _game_thread_ident is not None and threading.get_ident() == _game_thread_ident


def run_on_game_thread(fn, *args, timeout=30.0, **kwargs):
    """Run ``fn`` on the game thread and return its result.

    If already on the game thread (e.g. a tool handler calling back in) the
    function runs inline to avoid a self-deadlock."""
    if is_on_game_thread():
        return fn(*args, **kwargs)
    box = {}
    done = threading.Event()
    _jobs.put((fn, args, kwargs, box, done))
    if not done.wait(timeout):
        raise TimeoutError("game-thread job timed out after %.1fs" % timeout)
    if "error" in box:
        raise RuntimeError(box["error"])
    return box.get("value")
