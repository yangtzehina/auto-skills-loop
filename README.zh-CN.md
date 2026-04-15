# auto-skills-loop

`auto-skills-loop` 是一个本地优先、带策略约束的 AI agent skill 创建与治理框架。它不是只生成 `SKILL.md`，而是把 repo 证据、skill 规划、产物生成、结构校验、安全审计、运行时治理和稳态运营串成一条可复查的链路。

[English README](README.md)

## 为什么需要它

很多 skill 生成工具只解决“写一份说明文档”。这个项目把 skill create 当成完整生命周期：

- 从代码、文档、脚本、配置和 workflow 中提取 repo-grounded 需求
- 规划 skill package
- 生成 `SKILL.md`、references、scripts 和 eval scaffold
- 校验结构、安全风险和 operation contract
- 评审 requirement coverage 和质量
- 可选地接入运行时证据
- 通过只读报告和人工批准处理 pilot、source promotion、operation-backed follow-up

默认策略是保守的：先只读报告，真实变更前需要人工批准，不自动 promotion，不自动刷新 baseline。

## 核心能力

- **Repo-grounded skill creation**：先读真实仓库证据，再规划 skill。
- **双轨 skill 类型**：支持普通 guidance skill，也支持基于操作契约的 operation-backed skill。
- **Eval scaffold**：生成 trigger、output、benchmark 等检查文件。
- **安全审计门禁**：扫描凭据访问、数据外传、动态执行、持久化安装、浏览器会话访问、prompt injection、确认绕过等风险。
- **运行时治理**：把运行时证据归纳为 `no_change`、`patch_current`、`derive_child` 或 `hold`，但不自动改默认行为。
- **稳态运营**：create-seed、prior pilot、public source promotion、operation-backed backlog 都通过只读 CLI 暴露状态。

## 快速开始

要求：

- Python 3.11+
- `pydantic`

```bash
git clone https://github.com/yangtzehina/auto-skills-loop.git
cd auto-skills-loop
python3 -m venv .venv
source .venv/bin/activate
pip install pydantic
PYTHONPATH=src python3 scripts/run_tests.py
```

运行默认稳态检查：

```bash
PYTHONPATH=src python3 scripts/run_simulation_suite.py --mode full
PYTHONPATH=src python3 scripts/run_verify_report.py --mode full
PYTHONPATH=src python3 scripts/run_ops_roundbook.py --mode quick --format markdown
PYTHONPATH=src python3 scripts/run_operation_backed_backlog.py --format markdown
```

## 常用命令

```bash
# 运行默认测试
PYTHONPATH=src python3 scripts/run_tests.py

# 检查 simulation fixture 是否漂移
PYTHONPATH=src python3 scripts/run_simulation_suite.py --mode quick
PYTHONPATH=src python3 scripts/run_simulation_suite.py --mode full

# 输出统一 verify report
PYTHONPATH=src python3 scripts/run_verify_report.py --mode full

# 输出运营 roundbook
PYTHONPATH=src python3 scripts/run_ops_roundbook.py --mode quick --format markdown

# 查看 operation-backed 稳态状态和 backlog
PYTHONPATH=src python3 scripts/run_operation_backed_status.py --format markdown
PYTHONPATH=src python3 scripts/run_operation_backed_backlog.py --format markdown
```

## 架构概览

主链路分为：

1. **Preload / Extract**：读取仓库证据。
2. **Plan**：决定生成 guidance skill 还是 operation-backed skill。
3. **Generate**：生成 skill 文档、引用资料、脚本、evals 和可选 operation contract。
4. **Validate**：校验 frontmatter、artifact 结构、eval 文件、operation contract 和安全风险。
5. **Review**：评审需求覆盖、质量和 repair suggestion。
6. **Govern**：用只读报告和 approval surface 管理运行时 follow-up。

默认生成物会写到 `.generated-skills/`。该目录是本地运行产物，不是源码，公开发布时默认忽略。

可以通过环境变量修改生成目录：

```bash
export AUTO_SKILLS_LOOP_OUTPUT_ROOT=/path/to/generated-skills
```

OpenSpace 观察和运行时使用报告是可选能力，默认关闭。需要时显式配置：

```bash
export AUTO_SKILLS_LOOP_OPENSPACE_PYTHON=/path/to/openspace/python
export AUTO_SKILLS_LOOP_OPENSPACE_DB_PATH=/path/to/openspace.db
```

为了兼容已有本地配置，旧的 `SKILL_CREATE_*` 环境变量仍然会被识别。

## 安全模型

安全审计是本地规则式，不依赖外部服务，也不把 LLM 作为主判定器。

默认等级语义：

- `LOW`：信息性，通过
- `MEDIUM`：可疑，warn
- `HIGH`：高风险，fail
- `REJECT`：明显不可接受，fail/refuse

高危安全问题默认不可自动 repair。系统不会尝试把恶意 skill “修饰”成看起来安全的版本。

## Operation-Backed Skill

只有当仓库存在稳定操作面时，才进入 operation-backed 轨道，例如 native CLI、Python backend、shell wrapper 或 API client。

operation-backed skill 可以生成：

- `references/operations/contract.json`
- `evals/operation_validation.json`
- `evals/operation_coverage.json`
- 从 contract 派生的 `SKILL.md`
- 必要时的轻量 helper script

这不代表所有 skill 都要变成 CLI。对于文档型、流程型、操作面不稳定的仓库，guidance skill 仍然是默认主线。

## 当前默认运营模式

项目默认进入 steady-state：

- 不自动重开 create-seed
- 不默认启用 runtime prior
- 不自动 promotion public source
- 不自动刷新 baseline
- 不自动修复高危安全问题
- operation-backed backlog 没有真实触发器时不做 patch/derive

是否有下一步，应该以 roundbook 和 backlog 命令为准。

## 参考来源

本项目参考了以下公开项目和方法论：

- [slowmist/slowmist-agent-security](https://github.com/slowmist/slowmist-agent-security)：启发了本地安全审计、红旗模式、信任边界和 agent safety review 思路。
- [HKUDS/CLI-Anything](https://github.com/HKUDS/CLI-Anything)：启发了 executable operation surface 与 agent-facing skill guidance 分层。
- Claude / Codex 风格 skill 生态及公开 skill collection：启发了 discovery、reuse、promotion 和 regression workflow。

这些是设计参考，不是运行时 vendored dependency。

## License

Apache-2.0。见 [LICENSE](LICENSE)。
