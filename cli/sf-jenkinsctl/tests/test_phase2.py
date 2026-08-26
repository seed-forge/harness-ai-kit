"""jenkinsctl Phase 2 测试。"""
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from jenkinsctl.credential import _CRED_CLASSES, _get_cred_list
from jenkinsctl.tool import _TOOL_VERSION_CMDS, _TOOL_CONFIG_TAGS
from jenkinsctl.plugin import _load_required_plugins


class TestCredentialModule(unittest.TestCase):
    """credential 模块测试。"""

    def test_cred_classes_defined(self):
        """三种凭据类型应有对应的 Java 类映射。"""
        self.assertIn("ssh-key", _CRED_CLASSES)
        self.assertIn("username-password", _CRED_CLASSES)
        self.assertIn("secret-text", _CRED_CLASSES)

    def test_get_cred_list_api_failure(self):
        """API 失败时应返回空列表。"""
        mock_conn = MagicMock()
        mock_conn.api_get.side_effect = Exception("connection error")
        result = _get_cred_list(mock_conn)
        self.assertEqual(result, [])


class TestToolModule(unittest.TestCase):
    """tool 模块测试。"""

    def test_version_cmds_defined(self):
        """五种工具类型应有版本检测命令。"""
        for tool_type in ["maven", "jdk", "gradle", "ant", "nodejs"]:
            self.assertIn(tool_type, _TOOL_VERSION_CMDS)

    def test_config_tags_defined(self):
        """五种工具类型应有对应的 config.xml 标签。"""
        for tool_type in ["maven", "jdk", "gradle", "ant", "nodejs"]:
            self.assertIn(tool_type, _TOOL_CONFIG_TAGS)


class TestPluginModule(unittest.TestCase):
    """plugin 模块测试。"""

    def test_load_required_plugins(self):
        """应能加载 required-plugins.yaml。"""
        plugins = _load_required_plugins()
        self.assertIsInstance(plugins, list)
        self.assertTrue(len(plugins) > 0, "required-plugins.yaml 应包含至少一个插件")
        # 检查结构
        for p in plugins:
            self.assertIn("name", p)
            self.assertIn("description", p)

    def test_required_plugins_contain_core(self):
        """核心插件应在必需列表中。"""
        plugins = _load_required_plugins()
        names = [p["name"] for p in plugins]
        self.assertIn("git", names, "git 插件应在必需列表中")
        self.assertIn("ssh-agent", names, "ssh-agent 插件应在必需列表中")
        self.assertIn("workflow-cps", names, "workflow-cps 插件应在必需列表中")


if __name__ == "__main__":
    unittest.main()
