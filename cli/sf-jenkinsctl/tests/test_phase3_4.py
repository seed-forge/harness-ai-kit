"""jenkinsctl Phase 3+4 测试。"""
import unittest
from unittest.mock import patch, MagicMock


class TestConfigCmdModule(unittest.TestCase):
    """config_cmd 模块测试。"""

    def test_config_group_defined(self):
        from jenkinsctl.config_cmd import config_group
        self.assertIsNotNone(config_group)
        # 检查子命令
        cmds = config_group.commands
        self.assertIn("get", cmds)
        self.assertIn("set", cmds)
        self.assertIn("show", cmds)
        self.assertIn("backup", cmds)
        self.assertIn("restore", cmds)


class TestUserModule(unittest.TestCase):
    """user 模块测试。"""

    def test_user_group_defined(self):
        from jenkinsctl.user import user_group
        self.assertIsNotNone(user_group)
        cmds = user_group.commands
        self.assertIn("list", cmds)
        self.assertIn("add", cmds)
        self.assertIn("remove", cmds)
        self.assertIn("token", cmds)


class TestJobModule(unittest.TestCase):
    """job 模块测试。"""

    def test_job_group_defined(self):
        from jenkinsctl.job import job_group
        self.assertIsNotNone(job_group)
        cmds = job_group.commands
        self.assertIn("list", cmds)
        self.assertIn("build", cmds)
        self.assertIn("console", cmds)
        self.assertIn("get", cmds)
        self.assertIn("folder", cmds)
        self.assertIn("multibranch", cmds)


class TestSharedLibModule(unittest.TestCase):
    """sharedlib 模块测试。"""

    def test_sharedlib_group_defined(self):
        from jenkinsctl.sharedlib import sharedlib_group
        self.assertIsNotNone(sharedlib_group)
        cmds = sharedlib_group.commands
        self.assertIn("list", cmds)
        self.assertIn("register", cmds)
        self.assertIn("remove", cmds)


class TestNotifyModule(unittest.TestCase):
    """notify 模块测试。"""

    def test_notify_group_defined(self):
        from jenkinsctl.notify import notify_group
        self.assertIsNotNone(notify_group)
        cmds = notify_group.commands
        self.assertIn("test", cmds)


class TestOnboardModule(unittest.TestCase):
    """onboard 模块测试。"""

    def test_onboard_command_defined(self):
        from jenkinsctl.onboard import onboard
        self.assertIsNotNone(onboard)
        self.assertEqual(onboard.name, "onboard")


class TestScanModule(unittest.TestCase):
    """scan 模块测试。"""

    def test_scan_group_defined(self):
        from jenkinsctl.scan import scan_group
        self.assertIsNotNone(scan_group)
        cmds = scan_group.commands
        self.assertIn("image", cmds)
        self.assertIn("deps", cmds)
        self.assertIn("config", cmds)


if __name__ == "__main__":
    unittest.main()
