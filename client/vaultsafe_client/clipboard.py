from __future__ import annotations

import shutil
import subprocess

_TOOLS = ("wl-copy", "xclip", "pbcopy")


def copy_to_clipboard(text: str) -> str | None:
    for tool in _TOOLS:
        if shutil.which(tool) is None:
            continue
        subprocess.run([tool], input=text.encode("utf-8"), check=True)
        return tool
    return None
