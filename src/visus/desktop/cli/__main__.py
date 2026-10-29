"""``python -m visus.desktop.cli`` -- the CLI when the console script is not on PATH."""

import sys

from . import main

sys.exit(main(sys.argv[1:]))
