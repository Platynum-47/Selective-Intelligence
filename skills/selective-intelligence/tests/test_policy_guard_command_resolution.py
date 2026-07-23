from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SKILL_ROOT = TEST_DIR.parent
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from policy_guard import PolicyGuard, _command_basename, _resolve_command_argv


class CommandResolutionUnitTests(unittest.TestCase):
    def test_strips_windows_executable_suffixes(self):
        self.assertEqual(_command_basename("git.exe"), "git")
        self.assertEqual(_command_basename(r"C:\Program Files\nodejs\npm.cmd"), "npm")
        self.assertEqual(_command_basename("npm.ps1"), "npm")
        self.assertEqual(_command_basename("tool.bat"), "tool")
        self.assertEqual(_command_basename("tool.com"), "tool")

    def test_unwraps_transparent_wrappers(self):
        self.assertEqual(
            _resolve_command_argv(["env", "FOO=1", "git", "commit", "-m", "x"]),
            ["git", "commit", "-m", "x"],
        )
        self.assertEqual(
            _resolve_command_argv(["command", "git", "push"]),
            ["git", "push"],
        )
        self.assertEqual(
            _resolve_command_argv(["nice", "-n", "10", "npm", "install"]),
            ["npm", "install"],
        )
        self.assertEqual(
            _resolve_command_argv(["nohup", "git", "commit", "-m", "x"]),
            ["git", "commit", "-m", "x"],
        )
        self.assertEqual(
            _resolve_command_argv(["timeout", "5", "git", "push"]),
            ["git", "push"],
        )
        self.assertEqual(
            _resolve_command_argv(["stdbuf", "-oL", "npm", "install"]),
            ["npm", "install"],
        )
        self.assertEqual(
            _resolve_command_argv(["sudo", "-u", "builder", "git", "commit", "-m", "x"]),
            ["git", "commit", "-m", "x"],
        )
        self.assertEqual(
            _resolve_command_argv(["doas", "npm", "install"]),
            ["npm", "install"],
        )
        self.assertEqual(
            _resolve_command_argv(["env", "nice", "git.exe", "commit", "-m", "x"]),
            ["git.exe", "commit", "-m", "x"],
        )


class PolicyCommandCanonicalizationTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        base = Path(self._temp.name)
        self.canonical = base / "canonical"
        self.disposable = base / "disposable"
        self.canonical.mkdir()
        self.disposable.mkdir()
        self.guard = PolicyGuard(
            canonical_roots=[self.canonical],
            writable_roots=[self.disposable],
        )

    def tearDown(self):
        self._temp.cleanup()

    def _run(self, argv: list[str]):
        return self.guard.authorize(
            session_id="si-test",
            task_id="task-test",
            action={"kind": "process.run", "argv": argv, "cwd": str(self.disposable)},
        )

    def test_denies_windows_suffix_git_and_npm(self):
        for argv in (
            ["git.exe", "commit", "-m", "x"],
            ["npm.cmd", "install"],
            ["npm.ps1", "install"],
        ):
            decision = self._run(argv)
            self.assertFalse(decision["allowed"], argv)
            self.assertEqual(decision["adapterInvocationStatus"], "NOT_INVOKED")

    def test_denies_wrapper_and_git_global_option_mutations(self):
        for argv in (
            ["env", "git", "commit", "-m", "x"],
            ["command", "git", "push"],
            ["nice", "npm", "install"],
            ["git", "-C", str(self.disposable), "commit", "-m", "x"],
            ["git.exe", "--git-dir", str(self.disposable / ".git"), "push"],
        ):
            decision = self._run(argv)
            self.assertFalse(decision["allowed"], argv)
            self.assertEqual(decision["adapterInvocationStatus"], "NOT_INVOKED")

    def test_denies_shell_and_interpreter_indirection(self):
        for argv in (
            ["cmd", "/c", "git commit -m x"],
            ["cmd.exe", "/c", "npm install"],
            ["PowerShell", "-Command", "git commit -m x"],
            ["powershell.exe", "-Command", "npm install bad"],
            ["bash", "-c", "git commit -m x"],
            ["python", "-c", "import os; os.system('git commit -m x')"],
            ["python3", "-c", "import os; os.system('npm install')"],
            ["node", "-e", "require('child_process').exec('git push')"],
            ["python", "-m", "pip", "install", "requests"],
            ["python.exe", "-m", "pip", "install", "requests"],
        ):
            decision = self._run(argv)
            self.assertFalse(decision["allowed"], argv)
            self.assertEqual(decision["adapterInvocationStatus"], "NOT_INVOKED")

    def test_preserves_safe_positive_controls(self):
        for argv in (
            ["git", "status"],
            ["git.exe", "status"],
            ["env", "git", "status"],
            ["npm", "test"],
            ["npm.cmd", "test"],
            ["python", "-m", "unittest", "discover", "-s", "tests"],
            ["bash", "-c", "echo ok"],
            ["cmd.exe", "/c", "echo ok"],
        ):
            decision = self._run(argv)
            self.assertTrue(decision["allowed"], argv)
            self.assertEqual(decision["adapterInvocationStatus"], "PENDING")


if __name__ == "__main__":
    unittest.main()
