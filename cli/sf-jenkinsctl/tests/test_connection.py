"""jenkinsctl Phase 1 基础测试。"""
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from jenkinsctl.config import load_config
from jenkinsctl.connection import JenkinsConnection
from jenkinsctl import output


class TestConfig(unittest.TestCase):
    """配置加载测试。"""

    def test_load_defaults_only(self):
        """仅加载默认值（无用户配置时，required 字段应报错）。"""
        with patch("jenkinsctl.config._USER_CONFIG", Path("/nonexistent")):
            with self.assertRaises(ValueError) as ctx:
                load_config()
            self.assertIn("缺少必填配置", str(ctx.exception))

    def test_load_with_overrides(self):
        """CLI 覆盖应优先。"""
        with patch("jenkinsctl.config._USER_CONFIG", Path("/nonexistent")):
            config = load_config({
                "jenkins_url": "http://test:8080",
                "jenkins_user": "admin",
                "jenkins_api_token": "test-token",
            })
            self.assertEqual(config["jenkins_url"], "http://test:8080")
            self.assertEqual(config["jenkins_user"], "admin")
            self.assertEqual(config["jenkins_api_token"], "test-token")

    def test_defaults_applied(self):
        """非 required 字段应有默认值。"""
        with patch("jenkinsctl.config._USER_CONFIG", Path("/nonexistent")):
            config = load_config({
                "jenkins_url": "http://test:8080",
                "jenkins_user": "admin",
                "jenkins_api_token": "test-token",
            })
            self.assertEqual(config["jenkins_container"], "jenkins-2.x")
            self.assertEqual(config["jenkins_home"], "/var/jenkins_home")


class TestConnection(unittest.TestCase):
    """连接层测试。"""

    def _make_config(self):
        return {
            "jenkins_url": "http://test:8080",
            "jenkins_user": "admin",
            "jenkins_api_token": "test-token",
            "jenkins_container": "jenkins-2.x",
            "jenkins_home": "/var/jenkins_home",
            "jenkins_cli_jar": "/usr/share/jenkins/jenkins-cli.jar",
        }

    def test_connection_init(self):
        """连接初始化应正确设置属性。"""
        conn = JenkinsConnection(self._make_config())
        self.assertEqual(conn.url, "http://test:8080")
        self.assertEqual(conn.user, "admin")
        self.assertEqual(conn.container, "jenkins-2.x")

    def test_url_trailing_slash_stripped(self):
        """URL 尾部斜杠应被去除。"""
        config = self._make_config()
        config["jenkins_url"] = "http://test:8080/"
        conn = JenkinsConnection(config)
        self.assertEqual(conn.url, "http://test:8080")

    @patch("jenkinsctl.connection.requests.Session")
    def test_get_version(self, mock_session_cls):
        """get_version 应从 X-Jenkins header 获取版本。"""
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_resp = MagicMock()
        mock_resp.headers = {"X-Jenkins": "2.541.2"}
        mock_session.get.return_value = mock_resp

        conn = JenkinsConnection(self._make_config())
        ver = conn.get_version()
        self.assertEqual(ver, "2.541.2")


class TestOutput(unittest.TestCase):
    """输出模块测试。"""

    def test_print_table_empty(self):
        """空数据应显示 (无数据)。"""
        import io
        import sys
        captured = io.StringIO()
        sys.stdout = captured
        output.print_table(["A", "B"], [], title="Test")
        sys.stdout = sys.__stdout__
        self.assertIn("(无数据)", captured.getvalue())

    def test_print_table_with_data(self):
        """有数据时应正确输出。"""
        import io
        import sys
        captured = io.StringIO()
        sys.stdout = captured
        output.print_table(["Name", "Value"], [["foo", "bar"]])
        sys.stdout = sys.__stdout__
        out = captured.getvalue()
        self.assertIn("foo", out)
        self.assertIn("bar", out)


if __name__ == "__main__":
    unittest.main()
