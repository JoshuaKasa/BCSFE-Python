from __future__ import annotations

from .core import app
from .core import core
from .core import load_mygamatoto_index
from .core import load_transfer_records
from . import routes  # noqa: F401


def main() -> None:
    """Run the web UI Flask app."""
    core.core_data.init_data()
    load_mygamatoto_index()
    load_transfer_records()
    app.run(host="127.0.0.1", port=5050, debug=False)


if __name__ == "__main__":
    main()
