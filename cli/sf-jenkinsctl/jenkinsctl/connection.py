"""Jenkins REST 连接 + jenkins-cli.jar 透传。"""
import subprocess
import sys
from typing import Any

import requests


class JenkinsConnection:
    """Jenkins REST API 连接封装。"""

    def __init__(self, config: dict):
        self.url = config["jenkins_url"].rstrip("/")
        self.user = config["jenkins_user"]
        self.token = config["jenkins_api_token"]
        self.container = config.get("jenkins_container", "jenkins-2.x")
        self.jenkins_home = config.get("jenkins_home", "/var/jenkins_home")
        self.cli_jar = config.get("jenkins_cli_jar", "/usr/share/jenkins/jenkins-cli.jar")
        self._session = requests.Session()
        self._session.auth = (self.user, self.token)
        self._session.headers.update({"Accept": "application/json"})

    def api_get(self, path: str) -> dict:
        """GET 请求 Jenkins REST API。"""
        resp = self._session.get(f"{self.url}{path}", timeout=30)
        resp.raise_for_status()
        return resp.json()

    def api_post(self, path: str, data: Any = None) -> requests.Response:
        """POST 请求 Jenkins REST API。"""
        resp = self._session.post(f"{self.url}{path}", data=data, timeout=30)
        resp.raise_for_status()
        return resp

    def get_version(self) -> str:
        """获取 Jenkins 版本号。"""
        headers = self._session.get(f"{self.url}/api/json", timeout=10).headers
        return headers.get("X-Jenkins", "unknown")

    def get_status(self) -> dict:
        """获取 Jenkins 状态概览。"""
        data = self.api_get("/api/json?tree=mode,nodeDescription,numExecutors,slaves,useSecurity,views[name]")
        return {
            "mode": data.get("mode", ""),
            "description": data.get("nodeDescription", ""),
            "executors": data.get("numExecutors", 0),
            "agents": len(data.get("slaves", [])),
            "security": data.get("useSecurity", False),
            "views": [v["name"] for v in data.get("views", [])],
        }

    def cli_passthrough(self, args: list[str]) -> int:
        """透传参数给 jenkins-cli.jar，返回退出码。"""
        cmd = [
            "java", "-jar", self.cli_jar,
            "-s", self.url,
            "-auth", f"{self.user}:{self.token}",
        ] + args
        try:
            result = subprocess.run(cmd, capture_output=False)
            return result.returncode
        except FileNotFoundError:
            print("错误: java 未安装或不在 PATH 中", file=sys.stderr)
            return 1
