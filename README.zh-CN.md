<p align="center"><a href="README.md">English</a> · <strong>简体中文</strong></p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/hero-dark.png">
    <img src="docs/hero-light.png" alt="slopcheck — A linter for the mess AI agents leave in Python" width="820">
  </picture>
</p>

<p align="center">
  <a href="https://pypi.org/project/slopcheck/"><img alt="PyPI" src="https://img.shields.io/pypi/v/slopcheck?label=pypi"></a>
  <a href="https://github.com/yonguyungcs-pixel/slopcheck/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/yonguyungcs-pixel/slopcheck/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <img alt="Python 3.10 到 3.13" src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776AB">
  <img alt="Slop Score 100" src="docs/slop-score.svg">
</p>

<p align="center"><strong>一条命令。分数 0 到 100。越高越干净。</strong></p>

<p align="center">
  <img src="docs/demo.gif" alt="uvx slopcheck demo 得到 29 分，接着是修复提示，修完后得到 94 分" width="720">
</p>

给 AI 编程代理留在 Python 里的污泥做体检。Ruff 和 Pylint 不抓这些：裸 `except`、`import requets`、旁边还留着原函数的 `_v2`、请求路径上忘删的 `breakpoint()`。slopcheck 标出这些残留，并把发现交给 Claude Code、Codex 或 Cursor。

## 五秒安装

```bash
uvx slopcheck .
```

```bash
pipx install slopcheck
```

```bash
pip install slopcheck
```

需要 Python 3.10 或更新版本。在本仓库里：`pip install -e ".[dev]"`。

## 快速开始

```bash
slopcheck .                         # 终端报告和 Slop Score
slopcheck . --format sarif -o slopcheck.sarif
slopcheck prompt . > fix.md         # 贴进 Claude Code、Codex 或 Cursor
slopcheck . --fix-with-agent
```

GIF 里的脏树就是仓库自带的 demo。那一次扫描以 `20 findings · score 29 · fail` 结束。纯文本在 [`docs/demo.txt`](docs/demo.txt)。单独扫描 `demo/taskflow/ok.py` 是 100 分。

error 记 8，warning 记 4，note 记 2。`budget = lines / 5`，分数是 `round(100 * budget / (budget + raw))`。没有发现就是 100。200 行代码加上 5 个 error，分数是 50。

| 分数 | 标签 |
| --- | --- |
| 90–100 | clean |
| 75–89 | light residue |
| 50–74 | needs a wash |
| 25–49 | sloppy |
| 0–24 | hazardous sludge |

没有 error 和 warning，且分数不低于 `--min-score` 时退出码是 `0`。有发现、语法错误，或分数低于下限时是 `1`。参数或配置坏了是 `2`。只有 note 时进程不会失败，除非 `min-score` 把分数压到下限以下。`--exit-zero` 写完报告后始终以 0 退出。

## 为什么需要它

代理写出的代码看起来已经完成，失败时却不声不响。Ruff 很快，裸 `except` 会报成 E722。Pylint 也有自己的分数。它们不负责 `except` 周围那些残留。

| 写法 | Ruff / Pylint | slopcheck |
| --- | --- | --- |
| `except KeyError: return {}` | 不报 | SLP003 |
| `import requets` | 不报 | SLP010 |
| `summarize_tasks` 旁边还有 `summarize_tasks_v2` | 不报 | SLP007、SLP013 |
| `index += 1` 上面写着 `# increment index` | 不报 | SLP004 |
| `print(f"{tasks=}")` 和 `breakpoint()` | 默认不报 | SLP005 |

两个一起跑。Ruff 负责格式和缺陷。slopcheck 负责代理走后的那一遍。

<p align="center">
  <img src="docs/before-after.png" alt="裸 except、幻觉 import、以及 _v2 函数的修改前后" width="820">
</p>

## 规则

| ID | 级别 | 一小段例子 |
| --- | --- | --- |
| SLP001 | error | `except:` 然后 `pass` |
| SLP002 | error | `except Exception: return None` |
| SLP003 | error | `except KeyError: return {}` |
| SLP004 | note | `# increment index` |
| SLP005 | warning | `print(f"{tasks=}")`、`breakpoint()` |
| SLP006 | warning | `def _helper(): ...` 且没人调用 |
| SLP007 | warning | 形状几乎一样的第二个函数 |
| SLP008 | note | `name = "ada"` 然后 `if name is not None` |
| SLP009 | warning | `def export_tasks(): pass` |
| SLP010 | error | `import requets` |
| SLP011 | warning | `try` 里面套 `try` 再套 `try` |
| SLP012 | note | `return len(tasks)` 上面挂着长 docstring |
| SLP013 | warning | `def summarize_tasks_v2` |
| SLP014 | note | `# status = "archived"` |
| SLP015 | warning | `return "Error: failed to fetch title"` |

`slopcheck rules` 会打印每条发现附带的修改提示。

故意不报：解释原因的注释、`print(f"tasks={tasks}")`（会报的是 `f"{tasks=}"`）、`except ImportError` 里的可选导入、抽象方法、`Protocol`、`.pyi`，以及 `__exit__` 里的 `return False`。

用 `# slopcheck: ignore[SLP003]` 关掉一行。单独占一行的注释作用到下一行代码。`# slopcheck: disable` 关掉文件余下部分，直到 `# slopcheck: enable`。

```toml
[tool.slopcheck]
exclude = ["demo/**", "tests/fixtures/**"]
ignore = ["SLP004"]
min-score = 90

[tool.slopcheck.rules.SLP010]
allowed_modules = ["pytest"]
```

`--select` 替换配置里的选择。`--ignore` 追加到忽略列表。本仓库把 `min-score` 设为 100，并排除 demo，所以 `slopcheck .` 遇到任何发现都会失败。`slopcheck demo` 会把该路径重新纳入扫描。

<p align="center">
  <img src="docs/report.png" alt="演示项目的 HTML 报告，分数 29，带筛选和前几条发现" width="760">
</p>

`slopcheck . --format html -o report.html` 写出一个文件，不请求网络。同一次扫描也可以是 JSON、SARIF 2.1.0，或 SVG 徽章：`slopcheck badge . -o slop-score.svg`。

## 配合 Claude Code、Codex 和 Cursor

```bash
slopcheck prompt . > fix.md
```

提示词要求保持行为、该抛出的不要改成假返回值、不要靠关掉规则来抬分数，然后重新运行 slopcheck。

技能文件是 [`skills/slopcheck/SKILL.md`](skills/slopcheck/SKILL.md)。`.claude/skills`、`.cursor/skills`、`.agents/skills` 里是同一份文件的链接。

Claude Code 可以在每次编辑后检查。复制 [`examples/hooks/slopcheck.sh`](examples/hooks/slopcheck.sh)，匹配规则在 [`examples/hooks/claude-code.settings.json`](examples/hooks/claude-code.settings.json)。

## CI、pre-commit、GitHub Action

打上 `v0.1.0` 标签之后的 pre-commit：

```yaml
repos:
  - repo: https://github.com/yonguyungcs-pixel/slopcheck
    rev: v0.1.0
    hooks:
      - id: slopcheck
```

GitHub Action，把 SARIF 上传到 code scanning：

```yaml
- uses: yonguyungcs-pixel/slopcheck@v0.1.0
  with:
    path: .
    upload-sarif: "true"
```

Action 定义在 [`action.yml`](action.yml)。完整工作流在 [`examples/workflows/slopcheck.yml`](examples/workflows/slopcheck.yml)。本仓库的 CI 在 Python 3.10 到 3.13 上运行 pytest 和 `slopcheck .`。

## 对照

| | slopcheck | Ruff | Pylint | eslint-plugin-slop |
| --- | --- | --- | --- | --- |
| 语言 | Python | Python | Python | TypeScript |
| 假退路 `return {}` | 会 | 不会 | 不会 | 不会 |
| 幻觉 import | 会 | 不会 | 不会 | 不会 |
| 近重复的 `_v2` | 会 | 不会 | 不会 | 不会 |
| 复述注释 | 会 | 不会 | 不会 | 不会 |
| 给代理看的分数 | 0–100 | 无 | 0–10，另一件事 | 无 |
| 修复提示 | 有 | 无 | 无 | 无 |
| SARIF | 有 | 有 | 无 | 通过 ESLint |
| 取代其他工具 | 否 | 否 | 否 | 语言不同 |

[eslint-plugin-slop](https://github.com/antfu/eslint-plugin-slop) 是 TypeScript 上的同类。[no-ai-slop](https://github.com/petergyang/no-ai-slop) 改文章。[hallmark](https://github.com/Nutlope/hallmark) 查界面。这个查 Python。

## 常见问题

**它取代 Ruff 吗？** 不。打开 Ruff。再用 slopcheck 抓 Ruff 不会命名的残留。

**它会判定这段代码是 AI 写的吗？** 不会。它只标模式。人也会写出 `except: pass`。

**一条 note 让构建失败了。** note 记 2 分。只有分数掉到 `--min-score` 以下时，进程才会失败。本仓库的下限是 100，所以一条 note 也会让 `slopcheck .` 失败。

**误报怎么留着？** 在那一行写 `# slopcheck: ignore[SLP010]`。这里没装上的可选依赖，写进 `allowed_modules`。

**哪个 Python？** 3.10、3.11、3.12、3.13。

## 路线图

- 对复述注释、注释掉的代码、调试残留做不改变行为的自动修改。
- 基线文件。脏仓库可以只要求新代码变干净。
- LSP。代理还在打字时就能看到分数。
- 幻觉出来的关键字参数。
- 插件 API，给只在某一个代码库里有意义的规则用。

## 参与贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。开 PR 之前，`pytest` 和 `slopcheck .` 都应该是干净的。变更记录在 [CHANGELOG.md](CHANGELOG.md)。

## Star 历史

<p align="center">
  <a href="https://star-history.com/#yonguyungcs-pixel/slopcheck&Date">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=yonguyungcs-pixel/slopcheck&type=Date&theme=dark">
      <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=yonguyungcs-pixel/slopcheck&type=Date">
      <img alt="yonguyungcs-pixel/slopcheck 的 Star 历史" src="https://api.star-history.com/svg?repos=yonguyungcs-pixel/slopcheck&type=Date">
    </picture>
  </a>
</p>

## 许可证

[MIT](LICENSE)
