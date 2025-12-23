import collections
import dataclasses
import json
import os
import time
from dataclasses import asdict
from glob import glob
from pathlib import Path
from typing import Any
from typing import Optional

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
        action="extend",
        nargs="*",
        type=Path,
        dest="replay_files",
        default=[],
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


@dataclasses.dataclass
class ReplayTestInfo:
    nodeid: str
    start: float = 0.0
    finish: Optional[float] = None
    outcome: Optional[str] = None
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)
    xdist_group: Optional[str] = None

    def to_clean_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v}


class _ReplayTestInfoDefaultDict(collections.defaultdict):
    def __missing__(self, key):
        self[key] = ReplayTestInfo(nodeid=key)
        return self[key]


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
        self.nodes = _ReplayTestInfoDefaultDict()
        self.session_start_time = config.replay_start_time

    @pytest.fixture(scope="function")
    def replay_metadata(self, request):
        return self.nodes[request.node.nodeid]

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
            self.nodes[nodeid].start = time.perf_counter() - self.session_start_time
            json_content = json.dumps(self.nodes[nodeid].to_clean_dict())
            self.append_test_to_script(nodeid, json_content)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item):
        report = yield
        result = report.get_result()
        if self.dir:
            self.nodes[item.nodeid].outcome = (
                self.nodes[item.nodeid].outcome or result.outcome
            )
            current = self.nodes[item.nodeid].outcome
            if not result.passed and current != "failed":
                # do not overwrite a failed outcome with a skipped one
                self.nodes[item.nodeid].outcome = result.outcome

            if result.when == "teardown":
                self.nodes[item.nodeid].finish = (
                    time.perf_counter() - self.session_start_time
                )
                json_content = json.dumps(self.nodes[item.nodeid].to_clean_dict())
                self.append_test_to_script(item.nodeid, json_content)

    def pytest_collection_modifyitems(self, items, config):
        replay_files = config.getoption("replay_files")
        if not replay_files:
            return

        enable_xdist = len(replay_files) > 1

        # Use a dict to deduplicate the node ids while keeping the order.
        nodeids = {}
        for num, single_rep in enumerate(replay_files):
            with open(single_rep, encoding="UTF-8") as f:
                for line in f.readlines():
                    stripped = line.strip()
                    # Ignore blank lines and comments. (#70)
                    if stripped and not stripped.startswith(("#", "//")):
                        node_info = json.loads(stripped)
                        nodeid = node_info["nodeid"]
                        if enable_xdist:
                            node_info["xdist_group"] = f"replay-gw{num}"
                        if "finish" in node_info:
                            self.nodes[nodeid] = ReplayTestInfo(**node_info)
                        nodeids[nodeid] = None

        items_dict = {item.nodeid: item for item in items}
        remaining = []
        # Make sure to respect the order from the JSON file (#52).
        for nodeid in nodeids:
            item = items_dict.pop(nodeid)
            if item:
                if xdist_group := self.nodes[nodeid].xdist_group:
                    item.add_marker(pytest.mark.xdist_group(name=xdist_group))
                remaining.append(item)
        deselected = list(items_dict.values())

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


@pytest.hookimpl(tryfirst=True)
def pytest_load_initial_conftests(early_config, parser, args):
    # Check both plugin names: "xdist" (normal install) and "xdist.plugin" (frozen executables with -p flag)
    is_xdist_enabled = early_config.pluginmanager.has_plugin(
        "xdist"
    ) or early_config.pluginmanager.has_plugin("xdist.plugin")
    replay_files = parser.parse_known_args(args).replay_files

    if len(replay_files) > 1 and not is_xdist_enabled:
        raise pytest.UsageError(
            "Cannot use --replay with multiple files without pytest-xdist installed."
        )
    if len(replay_files) > 1:
        if any(
            map(
                lambda x: any(
                    x == arg or x.startswith(f"{arg}=")
                    for arg in ("-n", "--dist", "--numprocesses", "--maxprocesses")
                ),
                args,
            )
        ):
            raise pytest.UsageError(
                "Cannot use --replay with --numprocesses or --dist or --maxprocesses."
            )
        args.extend(["-n", str(len(replay_files)), "--dist", "loadgroup"])


def pytest_configure(config):
    if config.getoption("replay_record_dir") or config.getoption("replay_files"):
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
