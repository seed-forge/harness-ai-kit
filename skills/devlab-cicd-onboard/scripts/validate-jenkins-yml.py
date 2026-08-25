#!/usr/bin/env python3
"""
validate-jenkins-yml.py — 验证 .platform/jenkins.yml 配置完整性

用法:
    python3 validate-jenkins-yml.py .platform/jenkins.yml
    python3 validate-jenkins-yml.py .platform/jenkins.yml --schema references/jenkins-yml-schema.json

输出:
    验证通过 → exit 0 + 摘要
    验证失败 → exit 1 + 详细错误列表
"""
import sys
import json
import argparse
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML 未安装。运行: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


def load_yaml(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def validate_structure(config: dict) -> list[str]:
    """基础结构验证（不依赖 jsonschema）。"""
    errors = []

    # 1. environments 必须存在
    if 'environments' not in config:
        errors.append("缺少顶层键: environments（部署环境定义）")

    # 2. 每个 environment 必须有 host 或 deployHost
    for env_name, env_config in (config.get('environments') or {}).items():
        if not isinstance(env_config, dict):
            errors.append(f"environments.{env_name}: 期望对象，实际为 {type(env_config).__name__}")
            continue
        if not (env_config.get('host') or env_config.get('deployHost')):
            errors.append(f"environments.{env_name}: 缺少 host 或 deployHost")

    # 3. pathMapping 验证
    path_mapping = config.get('modules', {}).get('pathMapping', {})
    for svc, mapping in path_mapping.items():
        if isinstance(mapping, dict):
            if not mapping.get('compilePath'):
                errors.append(f"modules.pathMapping.{svc}: 对象格式缺少 compilePath")
            if not mapping.get('deployPath'):
                errors.append(f"modules.pathMapping.{svc}: 对象格式缺少 deployPath")

    # 4. healthCheck 配置验证
    hc = config.get('steps', {}).get('sc_javaJarDeploy', {}).get('healthCheck', {})
    if hc:
        valid_keys = {'script', 'port', 'url', 'dir', 'timeout', 'retries', 'delay'}
        unknown_keys = set(hc.keys()) - valid_keys
        if unknown_keys:
            errors.append(f"steps.sc_javaJarDeploy.healthCheck: 未知字段 {unknown_keys}")

    # 5. environments 字段别名一致性检查
    for env_name, env_config in (config.get('environments') or {}).items():
        if not isinstance(env_config, dict):
            continue
        # 检查是否同时使用了别名和标准名
        alias_pairs = [('host', 'deployHost'), ('port', 'deployPort'),
                       ('user', 'deployUser'), ('remoteDir', 'deployDir')]
        for alias, standard in alias_pairs:
            if alias in env_config and standard in env_config:
                errors.append(
                    f"environments.{env_name}: 同时使用了 '{alias}' 和 '{standard}'，"
                    f"请只保留一个（推荐 '{alias}'）"
                )

    return errors


def validate_schema(config: dict, schema_path: str) -> list[str]:
    """JSON Schema 验证（需要 jsonschema 库）。"""
    if not HAS_JSONSCHEMA:
        return ["跳过 Schema 验证（jsonschema 未安装，运行: pip install jsonschema）"]

    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)

    validator = jsonschema.Draft7Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(config), key=lambda e: list(e.path)):
        path = '.'.join(str(p) for p in error.path) or '(root)'
        errors.append(f"{path}: {error.message}")
    return errors


def main():
    parser = argparse.ArgumentParser(description='验证 .platform/jenkins.yml 配置')
    parser.add_argument('yaml_file', help='要验证的 jenkins.yml 路径')
    parser.add_argument('--schema', '-s', default=None,
                        help='JSON Schema 文件路径（可选，默认使用内置结构验证）')
    parser.add_argument('--strict', action='store_true',
                        help='严格模式：Schema 验证失败也视为错误')
    args = parser.parse_args()

    yaml_path = Path(args.yaml_file)
    if not yaml_path.exists():
        print(f"ERROR: {yaml_path} not found", file=sys.stderr)
        sys.exit(1)

    config = load_yaml(str(yaml_path))
    all_errors = []

    # 1. 基础结构验证
    print(f"📋 验证: {yaml_path}")
    print(f"   结构验证...", end=" ")
    struct_errors = validate_structure(config)
    if struct_errors:
        print(f"❌ {len(struct_errors)} 个问题")
        all_errors.extend(struct_errors)
    else:
        print("✅")

    # 2. Schema 验证（如提供）
    if args.schema:
        schema_path = Path(args.schema)
        if schema_path.exists():
            print(f"   Schema 验证...", end=" ")
            schema_errors = validate_schema(config, str(schema_path))
            if schema_errors and not (len(schema_errors) == 1 and '跳过' in schema_errors[0]):
                print(f"❌ {len(schema_errors)} 个问题")
                if args.strict:
                    all_errors.extend(schema_errors)
            else:
                print("✅" if not schema_errors else "⚠️ " + schema_errors[0])
        else:
            print(f"   Schema 验证... ⚠️ {args.schema} not found，跳过")

    # 3. 汇总
    env_count = len(config.get('environments', {}))
    svc_count = len(config.get('modules', {}).get('pathMapping', {}))
    print(f"\n📊 配置摘要: {env_count} 个环境, {svc_count} 个服务")

    if all_errors:
        print(f"\n❌ 验证失败: {len(all_errors)} 个问题\n")
        for i, err in enumerate(all_errors, 1):
            print(f"  {i}. {err}")
        sys.exit(1)
    else:
        print(f"\n✅ 验证通过")
        sys.exit(0)


if __name__ == '__main__':
    main()
