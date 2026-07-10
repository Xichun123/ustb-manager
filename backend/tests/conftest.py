import os
import tempfile


_TEST_HOME = tempfile.TemporaryDirectory(prefix="ustb-manager-tests-")
os.environ["HOME"] = _TEST_HOME.name
