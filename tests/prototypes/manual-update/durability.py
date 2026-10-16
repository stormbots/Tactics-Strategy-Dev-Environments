"""Synthetic crash filesystem. Models a chosen persistence contract, not NTFS/ext4."""
from pathlib import Path
import tempfile


class Store:
    def __init__(self):
        self.names = {}
        self.inodes = {}
        self.flushed = {}
        self.persisted_names = {}
        self.next_inode = 0

    def write(self, name, data):
        self.next_inode += 1
        self.names[name] = self.next_inode
        self.inodes[self.next_inode] = data

    def flush(self, name):
        inode = self.names[name]
        self.flushed[inode] = self.inodes[inode]

    def rename(self, old, new):
        self.names[new] = self.names.pop(old)

    def unlink(self, name):
        self.names.pop(name, None)

    def sync_directory(self):
        self.persisted_names = self.names.copy()

    def recovered(self):
        return {name: self.flushed.get(inode) for name, inode in self.persisted_names.items()}

    def crash(self):
        self.names = self.persisted_names.copy()
        self.inodes = {inode: self.flushed.get(inode) for inode in self.names.values()}


def installation_decision(store):
    recovered = store.recovered()
    if "intent" in recovered:
        return "recovery_required"
    if recovered.get("receipt") == b"complete":
        return "updated"
    return "no_install_evidence"


def timeline(skip_intent_directory_flush=False):
    """Yield each injected power-loss boundary, with independent mutation assertion."""
    store = Store()
    mutated = False
    actions = [
        ("intent.write", lambda: store.write("intent.tmp", b"installing")),
        ("intent.flush_file", lambda: store.flush("intent.tmp")),
        ("intent.rename", lambda: store.rename("intent.tmp", "intent")),
    ]
    if not skip_intent_directory_flush:
        actions.append(("intent.flush_directory", store.sync_directory))
    actions += [
        ("native.mutate", None),
        ("receipt.write", lambda: store.write("receipt.tmp", b"complete")),
        ("receipt.flush_file", lambda: store.flush("receipt.tmp")),
        ("receipt.rename", lambda: store.rename("receipt.tmp", "receipt")),
        ("receipt.flush_directory", store.sync_directory),
        ("intent.unlink", lambda: store.unlink("intent")),
        ("intent.unlink_flush_directory", store.sync_directory),
    ]
    for label, action in actions:
        if action is None:
            mutated = True
        else:
            action()
        durable = store.recovered().copy()
        yield label, durable, mutated, installation_decision(store)


class SentinelChild:
    """In-process fake child, not a subprocess. Writes exactly one fixed temp sentinel."""
    def __init__(self):
        self._temporary = tempfile.TemporaryDirectory(prefix="SDE-W1-PROTOTYPE-")
        self.root = Path(self._temporary.name)
        self.started = False
        self.finished = False

    def start(self):
        if self.started:
            raise ValueError("duplicate fake child")
        self.started = True
        (self.root / "PROTOTYPE-NATIVE-SENTINEL").write_text("started\n")

    def finish(self):
        if not self.started:
            raise ValueError("child not started")
        self.finished = True
        (self.root / "PROTOTYPE-NATIVE-SENTINEL").write_text("finished\n")

    def close(self):
        self._temporary.cleanup()
