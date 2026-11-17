# JX3 Combat Coach

剑网3 JCL AI 竞技场复盘系统的第一阶段骨架。优先 JJC 3V3，模块不绑定门派或心法。当前提供保守日志解析和证据链基础能力，尚不提供控制链识别、技能交换评分或死亡原因诊断。

## 本地安装、运行与测试

需要 Python 3.11+。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
# 可选：.env.example 仅为模板，应用不自动加载 .env
export JX3_DATABASE_PATH=./combat-coach.sqlite3
uvicorn jx3_combat_coach.api.app:app --host 127.0.0.1 --port 8000
```

另开终端：

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
pytest
python -m build
```

交互式接口文档：http://127.0.0.1:8000/docs 。SQLite 在应用 lifespan 启动时初始化，默认路径 `./combat-coach.sqlite3`。

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyses \
  -H 'Content-Type: application/json' \
  -d '{"text":"0\t100\t1700000000\t1000\t28\t{2001}\n"}'
# 使用响应的 analysis_id 查询
curl http://127.0.0.1:8000/api/v1/analyses/ANALYSIS_ID
```

POST 返回 201，包含原始解析结果、逐行错误、标准化事件、末次状态及发现；部分坏行不阻止有效行分析，调用者必须检查 `analysis.parsed.errors`。空输入得到空分析。API 接受已解码 Unicode 文本（上限一百万字符）；原始 GBK 文件应在 Python 层调用 `analyze(path.read_bytes(), encoding="gbk")`，这样才能保留原始文件字节。

## Docker

```bash
docker build -t jx3-combat-coach:bootstrap .
docker run --rm -p 127.0.0.1:8000:8000 -v jx3-coach-data:/data jx3-combat-coach:bootstrap
curl http://127.0.0.1:8000/health
```

镜像使用 Python 3.11 和非 root 用户；命名卷保存 SQLite。服务目前无身份认证，仅用于本地开发，不应直接开放公网。

## 模块与数据流

`JCLParser → JCLNormalizer → BattleStateEngine → RuleEngine → Tool Calling contracts / FastAPI`

- `models`：原始记录、解析错误、统一事件、状态、结构化发现与分析结果。
- `parser`：`bytes → ParseResult`；六列文本、受限 Lua 数据语法、明确指定编码。保留稀疏/重复键、nil、原始字节、行号和三种时钟；禁止执行 Lua。深度上限 64，超出或不支持的语法逐行报错。
- `normalizer`：`list[RawEvent] → list[Event]`；目前仅解释事件 4（名字）、5（生命）、19（施放记录）、28（死亡）；其余变为 unknown 并引用完整原始记录。不推断施放成功、技能命中、冷却或击杀者缺省值。
- `state`：按原始行顺序重放，可通过 `through_sequence` 截断历史。生命是观测值；从生命推导存活是 inferred；死亡事件本身是 observed。状态是最后一次记录，不承诺期间持续有效；未实现多场战斗分段，请一次输入一场日志。
- `rules`：注册、去重、执行和证据引用校验。目前仅内置 `death_observed`，输出死亡事实，不给出原因判断。
- `knowledge`：按游戏版本和技能 ID 查询语义，冷却可未知；默认字典为空。
- `agent`：`ToolDefinition/ToolCall/ToolResult/CombatTool` 契约；预留 LangGraph，不调用真实 LLM。
- `api` / `service.py` / `storage.py`：HTTP 路由、分析编排和 SQLite 持久化。

事件 ID 为文件 SHA-256 与物理行号组合，可稳定回溯到原始数据。标准化时间采用客户端毫秒原值，不宣称是相对开战时间。CRC 未验证。Lua 表使用 `{"$table": [[key,value], ...]}` 保留键类型、顺序及 nil；不支持完整 Lua 语言。

格式依据：https://hidewnd.com/game/jx3/j0008/ （2026-11-17 查阅）。测试全部为合成数据，未声称通过真实客户端日志全量验证。字段映射后续需配套真实脱敏样本和版本确认。

开发约束见 `AGENTS.md`，阶段进度与限制见 `docs/PROGRESS.md`。本次环境未收到 `PROJECT_CONTEXT.md`，尚待与原文核对。

若构建环境使用私有 HTTPS 代理 CA，可通过临时 secret 提供可信 CA（无需关闭 TLS 校验）：

```bash
docker build --secret id=proxy_ca,src=/path/to/trusted-ca-bundle.pem -t jx3-combat-coach:bootstrap .
```

CA 仅在安装依赖的构建步骤中挂载，不复制到最终镜像。普通网络直接使用前面的 `docker build` 命令。

## 解析测试页面

启动服务后访问 http://127.0.0.1:8000/ 。可上传 JCL（最大 10 MB），选择 GBK、UTF-8 或 GB18030，也可粘贴日志或载入合成示例。页面显示成功/错误计数、前 200 条原始事件、逐行错误、状态与规则发现，并可下载完整 JSON。文件使用原始字节接口 `POST /api/v1/analyses/file?encoding=gbk`；无需 Node.js 或额外前端构建。

基础数据参考审阅见 `docs/REFERENCE_DATA.md`。

## 第一版回放与报告

上传后，页面一次加载并展示完整事件列表，提供人物/类型筛选、技能名称/ID搜索、人物整场数值统计和可展开的事件证据；不再使用播放时间轴。记录不是三维动画；当前未重建 Buff 持续覆盖、自动确认解控、队伍归属或多场分段。伤害/治疗读取事件21的有效量标签，不从血量变化推算；事件29保留坐标但未绘制地图。人物卡片使用末次资料名称，展示整场记录伤害、治疗和死亡次数。

新增接口：

- `GET /api/v1/analyses/{id}/replay`
- `GET /api/v1/analyses/{id}/report`：本地死亡前10秒证据报告，非AI。
- `POST /api/v1/analyses/{id}/report/ai`：显式请求 OpenAI-compatible Chat Completions。

### 本地资料导入

```bash
git clone https://github.com/Akatsuki-kurumi/jx3-death-review.git ../jx3-death-review
python scripts/import_reference.py ../jx3-death-review
export JX3_CATALOG_PATH="$PWD/local-data/catalog.json"
```

本次固定参考提交 ae60146c5dc799a310a0842fca619b833f750261，本地导入 3297 条有名称的技能/Buff参考记录。数据为本地文件，不随源码包再分发；上游第三方资料说明见其 THIRD_PARTY_NOTICES.md。不是全游戏完整技能机制字典：冷却未知、版本未匹配，等级必须精确匹配。Docker 中需将该文件挂载到容器，并设置 JX3_CATALOG_PATH。

### AI 配置

在运行服务的终端显式设置（应用不自动读取 .env）：

```bash
export JX3_LLM_BASE_URL=https://api.openai.com/v1
export JX3_LLM_MODEL=你的模型名称
read -rs -p 'API Key: ' JX3_LLM_API_KEY
export JX3_LLM_API_KEY
uvicorn jx3_combat_coach.api.app:app --host 127.0.0.1 --port 8000
```

点击页面“发送事件并生成 AI 报告”才会调用供应商。密钥不发送到浏览器、不写入 SQLite。请求包含最多最近600条已识别非人物资料事件，去除名称、原始行及外部参考文本；仍含战斗ID、数值与证据ID。较长对局截断会影响报告完整性。当前通过模拟接口验证调用，不代表真实供应商/模型已验证；未配置时明确返回503。
