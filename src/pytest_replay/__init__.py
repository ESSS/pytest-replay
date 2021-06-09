import json
import time
import os
from glob import glob

import pytest


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
    group.addoption(
        "--replay-skip-cleanup",
        action="store_true",
        dest="skip_cleanup",
        default=False,
        help="Skips cleanup scripts before running (does not remove previously "
        "generated replay files).",
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
        skip_cleanup = config.getoption("skip_cleanup", False)
        if not skip_cleanup:
            self.cleanup_scripts()
        self.node_start_time = dict()
        self.session_start_time = config.replay_start_time

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
            self.node_start_time[nodeid] = time.perf_counter() - self.session_start_time
            json_content = json.dumps(
                {"nodeid": nodeid, "start": self.node_start_time[nodeid]}
            )
            self.append_test_to_script(nodeid, json_content)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item):
        report = yield
        result = report.get_result()
        if self.dir and result.when == "teardown":
            json_content = json.dumps(
                {
                    "nodeid": item.nodeid,
                    "start": self.node_start_time[item.nodeid],
                    "finish": time.perf_counter() - self.session_start_time,
                    "outcome": result.outcome,
                }
            )
            self.append_test_to_script(item.nodeid, json_content)

    def pytest_collection_modifyitems(self, items, config):
        replay_file = config.getoption("replay_file")
        if not replay_file:
            return

        with open(replay_file, "r", encoding="UTF-8") as f:
            all_lines = f.readlines()
            nodeids = {
                json.loads(line)["nodeid"]
                for line in all_lines
                if not line.strip().startswith(("#", "//"))
            }
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

    def append_test_to_script(self, nodeid, line):
        suffix = "-" + self.xdist_worker_name if self.xdist_worker_name else ""
        fn = os.path.join(self.dir, self.base_script_name + suffix + self.ext)
        with open(fn, "a", encoding="UTF-8") as f:
            f.write(line + "\n")
            f.flush()
            self.written_nodeids.add(nodeid)


class DeferPlugin:
    def pytest_configure_node(self, node):
        node.workerinput["replay_start_time"] = node.config.replay_start_time


def pytest_configure(config):
    if config.getoption("replay_record_dir") or config.getoption("replay_file"):
        if hasattr(config, "workerinput"):
            config.replay_start_time = config.workerinput["replay_start_time"]
        else:
            config.replay_start_time = time.perf_counter()
        # check for xdist and xdist.plugin: the former is the name of the plugin in normal
        # circumstances, the latter happens when xdist is loaded explicitly using '-p' in
        # a frozen executable
        if config.pluginmanager.has_plugin("xdist") or config.pluginmanager.has_plugin(
            "xdist.plugin"
        ):
            config.pluginmanager.register(DeferPlugin())
        config.pluginmanager.register(ReplayPlugin(config), "replay-writer")


def pytest_report_header(config):
    if config.getoption("replay_record_dir"):
        return "replay dir: {}".format(config.getoption("replay_record_dir"))
