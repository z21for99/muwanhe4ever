# muwanhe4ever

**本地优先、开源的长篇小说角色运行时。**  
不是“角色卡聊天”，而是把一部长篇小说的场景、对话、关系和口吻编译成可检索、可评测的角色记忆，让角色在**全书最新时间线**上，用自己的心理和语言逻辑与用户对话。

当前版本 **v0.1**：解析、对话提取、场景分段、向量 / FTS 检索、style bank、角色引擎、OpenAI 兼容 API 和本地 Web 都已经跑通。speaker 归属和风格样本仍是实验性的，离“完本角色”还有距离。

仓库只包含**引擎代码**。原著文本、角色数据、向量索引和 API key 都由使用者本地提供，不随仓库分发。

---

## 这是什么

这是一个“把小说角色跑起来”的工程，不是通用聊天机器人，也不是角色卡平台。

- 角色：**沐婉荷**，长篇小说《花嫁》中的母亲角色。
- 用户身份：**白风远**，她的儿子；也是原著的第一人称叙述者。
- 时间线：全书结尾之后。阴雷、窃脂、拾棘、洊雷四卷都已经发生，角色知道自己经历过这些事，不会被演成早期章节里的人。
- 内容边界：原著包含成年人的复杂关系和敏感题材；本项目默认**非露骨**，亲密场景只保留情感、心理和关系后果。
- 目标不是做 18+ 内容，而是复刻一个读者熟悉的角色：她的口吻、防御、心软、逞强、对儿子的依赖和矛盾。

如果你没看过原著，也可以把它当作一个“有长期记忆和固定口吻的角色 runtime”来试；但想得到接近原著的效果，需要你自己的小说文本，并在本地完成编译。

---

## 为什么做这个

角色卡通常只有几百到几千字的人设，聊久了会忘、会飘、会把“母亲”演成通用的温柔姐姐。

长篇小说的角色不是这样工作的：

- 她的性格是被几百个场景、几千句对话塑造出来的；
- 她的口吻和她对某个人的态度绑定，换一个人就不一样；
- 她知道什么、不知道什么，取决于故事走到哪一卷；
- 她的记忆不是一段摘要，而是可追溯的场景和原话。

所以这个项目把“角色”拆成几层：

| 层 | 作用 | 当前状态 |
|---|---|---|
| canon 记忆 | 原著场景、对话、事件，作为事实依据 | 已实现：向量 + FTS 检索 |
| style 记忆 | 她实际怎么说：句长、称呼、反问、动作 | 已实现：223 条高精度样本 |
| personal 记忆 | 和当前用户的多轮对话 | 已实现：SQLite session |
| inferred 记忆 | 从 canon 推断出的心理、关系状态 | 规划中，暂未单独建模 |
| critic | 独立的内容边界检查 | 规划中；当前只有 prompt 约束 |

设计原则：

1. **完整角色，不是章节快照**：以全书最新时间线为锚点。
2. **本地优先**：每个人跑自己的实例，用自己的 key、自己的文本。
3. **开源引擎，不分发内容**：仓库给代码，不给小说、角色包和索引。
4. **可评测**：尽量把“像不像”拆成检索、归属、风格和对话指标。
5. **非露骨**：保留关系和心理后果，跳过具体描写。

---

## 它现在能做什么

- 解析长篇小说的卷 / 章 / 分节 / 场景，支持乱序卷重排
- 提取引号对话，做规则归属：`cue` / `voice` / `vocative`，其余标 `unverified`
- 用 LLM 把场景切成更细的 segment（可分批）
- 场景和 segment 的向量索引、语义检索
- SQLite FTS5 trigram 关键词索引；中文短查询走 `LIKE` 兜底
- 从高置信度对话里构建 style bank
- 角色引擎：检索原著片段 + style bank + 角色核心 / 可选角色档案 + 多轮 history → LLM
- 本地 Web 聊天页：自动加载历史、一键重新开始
- OpenAI 兼容 API：`/v1/chat/completions`、`/v1/models`、`stream=true`
- 服务端 session：请求里的 `user` 作为 session key
- 评估命令：检索 eval、attribution gold eval

---

## 工作方式

```text
小说文本
  │
  ├─ parse      卷 / 章 / 分节 / 场景
  ├─ extract    引号对话 + 规则归属（strict 模式）
  ├─ refine     可选：LLM 语义分段 / 低置信度归属复核
  ├─ index      scene + segment 向量（Qwen embedding）
  ├─ index-fts  scene + segment 关键词索引（不耗 embedding 额度）
  └─ style      从高置信度台词构建 style bank

用户一句话
  │
  ├─ 向量检索（失败自动降级 FTS）
  ├─ style samples
  ├─ 角色核心 / 可选角色档案
  ├─ 最近 8 轮 history
  └─ LLM → 沐婉荷的回复
```

运行时不是把整本书塞进 prompt，而是每次只取最相关的几段场景 / segment，再加上固定的人设和风格样本。这样上下文可控，也方便替换模型和检索实现。

---

## 快速开始

### 0. 前置条件

- Python **3.11+**
- 一个 Qwen / 百炼 embedding key（当前 embedding 实现只支持 Qwen）
- 一个 OpenAI 兼容的 LLM key / base URL / model（火山 Ark 或其他兼容服务）
- 你自己合法拥有的一份《花嫁》文本，例如 `花嫁(2).txt`
- 建议在本地运行；不要把 API 直接暴露到公网

> 开发和验证环境是 Windows + PowerShell。Linux / macOS 没有系统验证过，但 Python 代码本身不依赖 Windows。

### 1. 安装

```powershell
git clone https://github.com/z21for99/muwanhe4ever.git
cd muwanhe4ever
python -m pip install -e ".[dev]"
```

只想运行、不跑测试的话：

```powershell
python -m pip install -e .
```

### 2. 配置 key

```powershell
Copy-Item .env.example .env
```

Linux / macOS：

```bash
cp .env.example .env
```

然后编辑 `.env`。最小配置是：

```ini
# embedding
QWEN_API_KEY=你的 Qwen key
QWEN_BASE_URL=https://maas.qianwenaiapi.com/compatible-mode/v1
QWEN_EMBEDDING_MODEL=qwen3.7-text-embedding-flash
QWEN_EMBEDDING_DIM=1024

# LLM：两种写法二选一
LLM_API_KEY=你的 LLM key
LLM_BASE_URL=https://你的兼容服务/v1
LLM_MODEL=你的账号实际可用的 model id
```

或者走火山 Ark 回退：

```ini
ARK_API_KEY=你的 Ark key
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
LLM_MODEL=你的账号实际可用的 model id
```

注意：

- `LLM_MODEL` 必须替换成**你自己账号里已开通、可调用**的 model id。README 里的 `doubao-seed-2-0-mini-260428` 只是开发时用的例子，不保证对所有人可用。
- `.env` 已经在 `.gitignore` 里，不要提交。
- 当前 `serve` 启动时会构造 Qwen embedder，所以**没有 Qwen key 会直接启动失败**。FTS 兜底是在 embedder 构造成功之后的运行期降级，不是“完全不需要 embedding 配置”。

### 3. 解析小说

把文本放在项目根目录或任意本地路径，不要提交。

```powershell
python -m muwanhe.cli parse --input "花嫁(2).txt" --db "data/muwanhe.db" `
  --volume-order "阴雷篇,窃脂篇,拾棘篇,洊雷篇"
```

`--volume-order` 是必要的：源文件的卷顺序和故事时间线不一致，必须按 **阴雷 → 窃脂 → 拾棘 → 洊雷** 重排。

### 4. 编译角色数据

```powershell
# 4.1 严格归属：只保留高置信度台词，其余标 unverified
python -m muwanhe.cli extract --db "data/muwanhe.db" --strict

# 4.2 可选：LLM 语义分段（可分批，避免一次调用太多）
python -m muwanhe.cli refine --db "data/muwanhe.db" --segments-only `
  --limit 30 --offset 0 --model "你的模型ID"

# 4.3 场景向量索引
python -m muwanhe.cli index --db "data/muwanhe.db" --kind scene

# 4.4 可选：segment 向量索引；Qwen 额度紧张时按 20 段一批
python -m muwanhe.cli index --db "data/muwanhe.db" --kind segment `
  --limit 20 --offset 0

# 4.5 FTS 关键词索引：不耗 embedding 额度，建议至少建一次
python -m muwanhe.cli index-fts --db "data/muwanhe.db"

# 4.6 style bank
python -m muwanhe.cli style --db "data/muwanhe.db" --min-samples 3
```

如果先只想快速试对话，最少需要：

```text
parse → extract --strict → index --kind scene → style → serve
```

segment 和 FTS 可以后补。

### 5. 可选：写角色档案

`data/muwanhe_profile.md` 如果存在，会自动拼进 system prompt：

```text
data/muwanhe_profile.md
```

它不是必需的；没有它时，引擎只用 `runtime/prompt.py` 里的核心人设。

### 6. 启动

```powershell
python -m muwanhe.cli serve --db "data/muwanhe.db" `
  --model "你的模型ID"
```

如果你已经在 `.env` 里设置了 `LLM_MODEL`，可以省略 `--model`：

```powershell
python -m muwanhe.cli serve --db "data/muwanhe.db"
```

打开：

```text
http://127.0.0.1:8000
```

Web 页会：

- 自动加载 `web-local` 这个 session 的历史；
- 发送时只带最新一句，由服务端维护多轮；
- 右上角“重新开始”会清空服务端和页面历史。

### 7. 第一次对话

```text
你：我回来了
她：（手里还攥着刚洗好的青菜，围裙带子在腰上晃了晃，转头瞪你一眼）饿了就等会儿！
```

或者用 CLI 一次性调用：

```powershell
python -m muwanhe.cli chat --db "data/muwanhe.db" --message "我回来了"
```

---

## 对话接口

### OpenAI 兼容

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "muwanhe",
    "user": "local",
    "messages": [{"role": "user", "content": "我回来了"}]
  }'
```

`user` 是 session key。相同 `user` 的后续请求会自动带上服务端保存的 history；如果客户端自己传了完整 `messages`，则以客户端 history 为准。

### Python OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="local",  # 本地服务不校验鉴权，占位即可
)

response = client.chat.completions.create(
    model="muwanhe",
    user="web-local",
    messages=[{"role": "user", "content": "我回来了"}],
)
print(response.choices[0].message.content)
```

### 流式

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "muwanhe",
    "user": "local",
    "stream": true,
    "messages": [{"role": "user", "content": "我回来了"}]
  }'
```

返回 SSE chunk，最后是 `data: [DONE]`。注意：当前实现是拿到完整回复后按字符切片，不是真正的 token 级流式。

### 接入自己的 agent / IM

任何支持 OpenAI 兼容 provider 的 agent、前端或 IM 网关都可以接：

```text
Base URL: http://127.0.0.1:8000/v1
Model:    muwanhe
API Key:  local（占位）
```

AstrBot / LangBot / Open WebUI 等只是例子，仓库不绑定具体平台。给每个用户分配稳定的 `user` 值即可隔离 session。

安全提醒：当前 API **没有鉴权**，只适合 `127.0.0.1` 本地使用。不要直接暴露到公网；需要公网访问时，自己在前面加反向代理和鉴权。

---

## 设计：为什么不是角色卡

### 1. 角色是“检索 + 说话方式”，不是一段人设

只写“温柔、嘴硬、爱儿子”会让模型自由发挥。这里把角色拆成：

- **事实**：原著里发生过什么，由 scene / segment 检索提供；
- **口吻**：她实际怎么说话，由 style bank 提供；
- **边界**：她不知道什么、不会说什么，由核心 prompt 和时间线约束；
- **关系**：她和当前用户的多轮互动，由 session history 提供。

### 2. 时间线是全书结尾之后

角色的“完本形态”意味着她经历过四卷的事，而不是停在第一章。核心 prompt 会明确这一点；检索也会优先取全书范围内的场景。

### 3. 归属先于风格

如果 speaker 归属错了，style bank 会把别人的话学成她的口吻。当前策略是：

- `strict` 模式只保留 `cue` / `voice` / `vocative` 高置信度归属；
- 其余标 `unverified`，不进入 style bank；
- 用 44 条人工 gold 评估 precision / coverage，而不是只看“像不像”。

这也是当前最大的短板：多人物场景里 `我 / 她 / 孙淑怡` 会互相抢话，44 条 gold 上 precision 只有 **0.529**。

### 4. 非露骨

原著有成年人的复杂关系。本项目默认：

- 不生成露骨性描写；
- 亲密场景只保留情感、心理和关系后果；
- 角色可以回避、反问、转移话题。

当前这是 **prompt 级约束**，还没有独立 critic。不要把它当成硬性内容审核。

---

## 效果

以下都是 v0.1 的真实模型输出（开发时用 `doubao-seed-2-0-mini`，不是固定脚本，也不保证每次一致）：

**输入：** `我回来了`

> （赶紧凑过来，指尖蹭过你湿冷的校服领口，声音发紧）怎么淋成这样？伞呢？不是跟你说过放学别在外面晃？快脱了，我给你拿干毛巾。

**输入：** `妈，我饿了`

> 饿了就等会儿，妈这就给你煮面，加你爱吃的煎蛋，要溏心的还是全熟的？

**输入：** `我饿了`（FTS 兜底、embedding 配额用尽时）

> （手里还攥着刚洗好的青菜，围裙带子在腰上晃了晃，转头瞪你一眼）饿了就等会儿！刚摘的青菜还没炒，你急着投胎啊？

能看出：

- 有动作、有生活细节，不是纯对白；
- 会唠叨、反问、管束；
- 不是通用的“温柔母亲”模板。

但也要诚实：这些是**样例**，不是稳定质量保证。归属噪声、检索误差和模型能力都会影响输出。

---

## 当前指标

- **69 个单元测试通过**
- 向量索引：**121 scene + 703 segment**
- FTS 索引：**121 scene + 703 segment**
- strict 对话：**4,134 条**
- 高精度 style 样本：**223 条**
- scene 检索（20 场景 leave-one-out）：向量 top1 **0.85** / top5 **0.90**；FTS exact-substring top1 **1.0**
- attribution gold（44 条，2 个场景）：accuracy **0.500** / coverage **0.386** / precision **0.529**

这些数字是 v0.1 的基线，不是最终效果。尤其是 attribution：14 条 gold 时 precision 看起来有 0.889，扩到 44 条后掉到 0.529，说明第一版指标过拟合了第一场戏。

---

## 当前限制

- **没有原著文本 / 角色包 / 索引**：仓库只有引擎，必须自己准备文本并编译。
- **Qwen key 是启动硬依赖**：`serve` 会构造 embedder；没有 Qwen 配置不能启动，FTS 兜底不能绕过启动配置。
- **模型 ID 因账号而异**：README 和 `.env.example` 里的 model 只是示例，必须换成你账号实际可用的。
- **Ark 欠费**：开发用的 Ark 账户当前欠费，live chat 会返回 403；这是账户问题，不是代码问题。换成你自己的 key 即可。
- **Qwen 免费额度有限**：一次索引 703 段可能 429；建议 `--limit 20 --offset ...` 分批。
- **attribution 仍不稳**：多人物场景会串话；strict coverage 只有 0.386。
- **style bank 仍有噪声**：223 条里仍有少量“别人说的话”，需要人工抽检。
- **没有 voice / Live2D**：v1 只做文本；语音和形象只保留接口位置，未实现。
- **没有 LangGraph / 独立 critic**：当前是普通 Python engine + prompt 约束。
- **API 没有鉴权**：只适合本地。
- **Web 不支持流式**：API 支持 `stream=true`，Web 页仍是一次性返回。
- **只在 Windows 验证过**：其他平台理论可行，但未系统测试。
- **单角色**：引擎围绕沐婉荷；换角色需要改 core / 数据 / 评估。

---

## FAQ

### 我没有看过原著，能用吗？

能启动、能对话，但效果会明显下降。这个项目的“角色”来自原著编译数据；没有文本，就只剩核心 prompt 和通用风格，容易变成普通的温柔母亲。

### 我需要自己准备小说吗？

需要。仓库不包含《花嫁》文本，也不分发角色包或向量索引。请使用你合法拥有的副本，并自行确认所在地区的版权和内容合规要求。

### 我能换别的 LLM 吗？

可以，只要它是 OpenAI 兼容接口：

```ini
LLM_API_KEY=...
LLM_BASE_URL=...
LLM_MODEL=...
```

如果服务不支持 `response_format=json_object`，`refine` 的 JSON 解析可能失败；对话本身通常没问题。

### 我能换 embedding 吗？

当前只实现了 Qwen。`.env.example` 里的 `ark` / `local_bge` 是预留选项，没有完成实现。FTS 可以在运行期兜底，但不能替代 Qwen 的启动配置。

### 为什么回复很泛？

常见原因：

1. 没有跑 `parse / extract / index / style`；
2. 没有配置或没有命中检索；
3. 模型太小或 system prompt 被截断；
4. speaker 归属噪声导致 style bank 不干净；
5. 角色档案 `data/muwanhe_profile.md` 不存在。

### 为什么 API 返回 503？

当前实现会把 LLM 的 403 欠费 / 权限错误转成 503，并返回明确 message。先检查你的 Ark / LLM 账户是否欠费、key 是否有效、model 是否开通。

### 能直接部署到公网吗？

不建议。当前没有鉴权、限流和多用户隔离，只适合本机。公网部署请自己加反向代理、鉴权、限流和日志脱敏。

### 这是 18+ 项目吗？

不是。原著包含成年人的敏感关系，但本项目默认非露骨，只保留心理和关系后果。请不要用它生成违法或伤害未成年人的内容。

---

## 目录

```text
src/muwanhe/
  api.py            OpenAI 兼容 API + Web 入口
  web.py            本地聊天页
  cli.py            parse / extract / refine / index / search / style / chat / serve
  compiler/         parse / dialogue / attribution / extract / refine / index / style
  providers/        LLM / embedding
  runtime/          prompt + character engine
  storage/          SQLite parse / extraction / vector / FTS / session
tests/              单元测试
eval/               attribution gold
docs/               设计 spec、状态与交接
```

常用命令：

```powershell
python -m muwanhe.cli --help
python -m muwanhe.cli eval-retrieval --db "data/muwanhe.db" --mode fts --limit 20
python -m muwanhe.cli eval-attribution --db "data/muwanhe.db" --gold "eval/attribution_gold.json"
```

---

## 数据与边界

- 原著文本、`.env`、`data/`、SQLite、向量索引都在本地，已 gitignore。
- 公开仓库只包含引擎、schema、测试、评估标签和中性 Web 页。
- 角色数据由使用者自己的文本生成，不随仓库分发。
- 默认非露骨；但这是 prompt 约束，不是硬性内容审核。
- 请自行确认原著版权、所在地区法律和平台内容政策。

## License

MIT。仓库只包含引擎代码；原著文本、角色数据、向量索引和 key 由使用者本地提供。
