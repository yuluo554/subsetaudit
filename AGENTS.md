# AGENTS.md

本仓库遵循 **`ai-tool-project-sprint`** 方法论（装订日期：2026-10-21）。

## 任何新对话的第一件事

```bash
py tools/check_sprint_layout.py    # 布局门；必须绿，红了先修布局再干活
py tools/check_desensitized.py     # 脱敏门；发布前与每次改文档后必跑
```

- 续接对话：读 `plan/HANDOFF-M<k>.md`（那是第 k 棒的收尾交接单），**先跑上面两条门**。
- 接手对话（无 HANDOFF）：先读 `plan/00`、`plan/05`、`plan/06` 与各 HANDOFF，重建"当前状态 + K 口径清单"再动手。
- **门不存在 = 本项目没装订** → 先补第零步（锚点 + 门 + `plan/00` 顶部一行），再做别的。

## 强制布局（布局门逐条断言，改动前先看这里）

| 项 | 位置 | 判据 |
| --- | --- | --- |
| 计划套件 | `plan/00`–`plan/06` + `data/README.md` | 存在且各含必需小节（标题关键词） |
| 数据台账 | `data/README.md` | 查证记录 + 数值口径在位（三态标注） |
| 交接单 | `plan/HANDOFF-M<k>.md` | 每个 ✅ 里程碑一份（M0 已声明豁免：其收尾记录 = 计划套件本身）；七节齐 |
| 里程碑状态副本 | `plan/00` 里程碑表 + `plan/05` 状态表 + `README.md` 状态表 | **逐处一致**（逐副本采集，不取任何单副本为真值） |
| 承诺-证据台账 | `plan/00` 的「承诺-证据台账」表 | 状态格不得同时含未完成标记与已 ✅ 的里程碑号 |
| 缺口表 | `plan/06` 首格为「缺口」的表 | 缺口格不得提及已 ✅ 的里程碑 |
| 发布留档 | `plan/RELEASE-M6.md`（两栏）或 `plan/WRAPUP-M6.md` | M6 翻 ✅ 后才要求存在；两栏 + 覆盖对账小节 |
| 文档点名的工具 | `plan/*.md`、`AGENTS.md`、`README.md` 里出现的 `tools/*.py` | 必须有实物；**未到里程碑的按 `PENDING_TOOLS` 显式登记并打印 SKIP**，登记项在其里程碑翻 ✅ 后必须删除，否则门变红 |

## 环境事实与禁忌（只写实测过的，带日期）

- 2026-10-21 实测：`py -0p` 有 **3.8.8-64** 与 **3.12-64**；3.8 通道装了 fontTools **4.57.0**、pytest 7.4.4；3.12 通道**没有** fontTools（CI 里两条都装）。
- 2026-10-21 实测：Node v24.15.0 在位（本项目的三道门仍用 Python 写，避免 CI 多一条运行时依赖）。
- 用 `py` 不用 `python`（后者是商店占位符）；跑中文输出一律 `py -X utf8`（CI 侧 `python` + `PYTHONUTF8=1`）。
- 本机代理与网络：`gh` 已登录 `yuluo554`（keyring，https）；`git push` 受阻时按"HTTPS 直连 → 本地代理 → 裸 SSH"顺序探测，**只对单条命令用 `-c http.proxy=`**，不改全局。
  **2026-10-21 M6 实测**：本机 git 的 https 通道会整个连不上，而 `gh api` 一直可用 → 远端判据
  （`tools/check_release.py --online`）**一律走 `gh api`**；推送走**一次性 SSH URL**，不改全局配置。
- **禁止**：把"未执行"写成已完成；在 tag 之后改交付面（要改就**重切 tag** 并把原因写进 `plan/RELEASE-M6.md` §二）；把商用字体（Arial/Calibri/msyh/seguiemj…）复制进仓库。
- 入库文档**一律相对路径**；绝对路径只出现在用户侧启动命令里。**脱敏门的扫描面 = 仓库内容**（`.gitignore` 里每条本地产物/环境目录都必须在 `tools/check_desensitized.py` 的 `SKIP_DIRS`/`SKIP_SUFFIXES` 里有对应项，否则假红）。

## 本项目的三条不可动摇的口径

1. **数值口径单点**：一切判定式/白名单/退出码只在 `data/README.md` §六 定义，代码与文案不得另立第二套。
2. **零网络零模型**：运行期不联网、不加载模型；仅 `tools/fetch_fonts.py`（用户显式触发）可下载 OFL 字体。
3. **结论是技术判定不是法律意见**：每条 finding 必带 `spec_ref` 或实测证据，`SKIPPED(reason=...)` 必须出现在输出里且不影响退出码。
