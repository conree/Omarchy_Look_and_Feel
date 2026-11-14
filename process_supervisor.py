"""Bound a panel command's total runtime and combined output before QML sees it.

Each command owns a process group. Clean that group even when the direct child
exits first; inherited pipes must not leave the shell waiting indefinitely.
Authenticated boot helpers have their own protected recovery protocol and run
across a privilege boundary; this user-level supervisor cannot signal root.
"""
import os
import ctypes
import selectors
import signal
import subprocess
import sys
import time


class CommandCancelled(Exception):
    """Must not inherit InterruptedError, which selectors swallows on EINTR."""


def bind_owner():
    parent = os.getppid()
    if ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGTERM, 0, 0, 0):
        raise OSError("Could not establish command owner lifetime.")
    if parent == 1 or os.getppid() != parent:
        raise CommandCancelled("Command owner exited.")


def run(command, seconds, budget):
    child = None
    output = [bytearray(), bytearray()]
    failure = ""
    deadline = time.monotonic() + seconds

    def cancelled(signum, frame):
        raise CommandCancelled("Command cancelled.")

    signal.signal(signal.SIGTERM, cancelled)
    signal.signal(signal.SIGINT, cancelled)
    try:
        # Linux delivers TERM if the owning shell disappears, including SIGKILL.
        # Check the parent again to close the prctl setup race.
        bind_owner()
        previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
        try:
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     start_new_session=True,
                                     preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask))
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        with selectors.DefaultSelector() as selector:
            for index, stream in enumerate((child.stdout, child.stderr)):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, index)
            while selector.get_map() or child.poll() is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Command exceeded its total time limit.")
                for key, _ in selector.select(min(remaining, .1)):
                    chunk = os.read(key.fd, min(65536, budget + 1))
                    if not chunk:
                        selector.unregister(key.fileobj)
                    elif sum(map(len, output)) + len(chunk) > budget:
                        raise ValueError("Command exceeded its output limit.")
                    else:
                        output[key.data].extend(chunk)
                # A direct child can exit while its descendants retain pipes.
                # Do not wait for such descendants to choose to close them.
                if child.poll() is not None:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        code = child.wait()
    except (OSError, ValueError, TimeoutError, CommandCancelled) as exc:
        failure = str(exc)
        code = 125
    finally:
        # Ignore repeated cancellation during mandatory group cleanup.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        if child is not None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()
            child.stdout.close()
            child.stderr.close()
    if failure:
        # Never pass a partial successful JSON result on a resource failure.
        sys.stderr.write(failure + "\n")
    else:
        sys.stdout.buffer.write(output[0])
        sys.stderr.buffer.write(output[1])
    return code if code >= 0 else 128 - code


if __name__ == "__main__":
    # Quickshell uses Unix signal integration; never inherit a blocked or
    # ignored termination signal into the relay/guardian lifetime protocol.
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})
    if sys.argv[1] == "--guard":
        sys.exit(run(sys.argv[4:], float(sys.argv[2]), int(sys.argv[3])))
    # Quickshell can SIGKILL its native Process during component destruction.
    # Keep the group owner in a separate session: parent-death TERM reaches
    # this guardian even if the small native-owned relay cannot run a handler.
    bind_owner()
    guardian = subprocess.Popen([sys.executable, "-B", __file__, "--guard", *sys.argv[1:]],
                                stdin=subprocess.DEVNULL, start_new_session=True)
    sys.exit(guardian.wait())
