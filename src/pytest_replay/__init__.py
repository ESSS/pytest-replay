import json
import re
from datetime import datetime
import os
from glob import glob


def pytest_addoption(parser):
    group = parser.getgroup("replay")
    group.addoption(
        "--replay-record-dir",
        action="store",
        dest="replay_record_dir",
        default=None,
        help="Directory to write record files to reproduce runs.",
    )
    group.addoption(
        "--replay",
        action="store",
        dest="replay_file",
        default=None,
        help="Use a replay file to run the tests from that file only",
    )
    group.addoption(
        "--replay-base-name",
        action="store",
        dest="base_name",
        default=".pytest-replay",
        help="Base name for the output file.",
    )


class ReplayPlugin:
    def __init__(self, config):
        self.dir = config.getoption("replay_record_dir")
        self.base_script_name = config.getoption("base_name")
        if self.dir:
            self.dir = os.path.abspath(self.dir)
        nprocs = config.getoption("numprocesses", 0)
        self.running_xdist = nprocs is not None and nprocs > 1
        self.xdist_worker_name = os.environ.get("PYTEST_XDIST_WORKER", "")
        self.ext = ".txt"
        self.written_nodeids = set()
        self.cleanup_scripts()
        self.test_start_time = dict()
        self._start_time = None

    @property
    def start_time(self):
        if self._start_time is None:
            self._start_time = datetime.now()
        return self._start_time

    def cleanup_scripts(self):
        if self.xdist_worker_name:
            # only cleanup scripts on the master node
            return
        if self.dir:
            if os.path.isdir(self.dir):
                if self.running_xdist:
                    mask = os.path.join(
                        self.dir, self.base_script_name + "-*" + self.ext
                    )
                else:
                    mask = os.path.join(self.dir, self.base_script_name + self.ext)
                for fn in glob(mask):
                    os.remove(fn)
            else:
                os.makedirs(self.dir)

    def pytest_runtest_logstart(self, nodeid):
        if self.running_xdist and not self.xdist_worker_name:
            # only workers report running tests when running in xdist
            return
        if self.dir:
            self.test_start_time[nodeid] = (
                datetime.now() - self.start_time
            ).total_seconds()
            json_content = json.dumps(
                {"nodeid": nodeid, "start": self.test_start_time[nodeid]}
            )
            self.append_test_to_script(json_content)

    def pytest_runtest_logfinish(self, nodeid):
        if self.running_xdist and not self.xdist_worker_name:
            # only workers report running tests when running in xdist
            return
        if self.dir:
            nodeid = json.dumps(
                {
                    "nodeid": nodeid,
                    "start": self.test_start_time[nodeid],
                    "finish": (
                        self.test_start_time[nodeid] - self.start_time
                    ).total_seconds(),
                    "outcome": "passed",
                }
            )
            self.append_test_to_script(nodeid)

    def pytest_collection_modifyitems(self, items, config):
        replay_file = config.getoption("replay_file")
        if not replay_file:
            return

        with open(replay_file, "r", encoding="UTF-8") as f:
            nodeids = {json.loads(x) for x in f.readlines()}

        remaining = []
        deselected = []
        for item in items:
            if item.nodeid in nodeids:
                remaining.append(item)
            else:
                deselected.append(item)

        if deselected:
            config.hook.pytest_deselected(items=deselected)
            items[:] = remaining

    def append_test_to_script(self, nodeid):
        suffix = "-" + self.xdist_worker_name if self.xdist_worker_name else ""
        fn = os.path.join(self.dir, self.base_script_name + suffix + self.ext)
        with open(fn, "a", encoding="UTF-8") as f:
            f.write(nodeid + "\n")
            self.written_nodeids.add(nodeid)


def pytest_configure(config):
    if config.getoption("replay_record_dir") or config.getoption("replay_file"):
        config.pluginmanager.register(ReplayPlugin(config), "replay-writer")


def pytest_report_header(config):
    if config.getoption("replay_record_dir"):
        return "replay dir: {}".format(config.getoption("replay_record_dir"))
