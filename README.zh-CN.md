# A股个股技术择时方法论

[English](./README.md)

`ashare-stock-timing` 是一个面向各类 AI Agent 的技术择时方法论包，用于分析 A 股个股的技术面、趋势、买点、卖点、资金动向、筹码结构和风险计划。

它只解决 **技术择时** 问题，不做基本面、财报、估值、DCF、目标价或长期投资价值判断。

## 适用场景

当用户询问以下问题时适合使用：

- 某只 A 股个股的技术面、趋势、波段结构。
- 买点、卖点、止损、止盈、加仓、减仓。
- 量价关系、突破、回踩、箱体、主升浪、派发风险。
- 主力资金、主力控盘、龙虎榜、两融、大宗交易、北向资金、筹码分布。
- 已有基本面判断，只需要技术入场和退出计划。

不适合用于：

- 公司基本面分析。
- 财报质量、盈利预测、行业空间、商业模式、护城河。
- PE/PB/PEG、DCF、目标价、内在价值。
- 长期投资价值判断，除非用户明确要求在已有基本面结论上做技术择时。

## 核心方法论

Skill 使用多层证据链，而不是单一指标：

```text
市场/板块过滤
  -> 筹码生命周期
  -> 个股趋势触发
  -> 量价/主力资金确认
  -> 风险与仓位计划
```

主要模块：

| 模块 | 作用 |
|---|---|
| 市场环境 | 判断大盘是否允许做多 |
| 板块强度 | 判断资金是否在该方向 |
| 个股趋势 | 判断趋势阶段、均线结构、新高/破位 |
| 量价资金 | 判断突破、回踩、派发、成交额确认 |
| 主力代理 | 用逐笔大单或日线代理评估资金行为 |
| 筹码分布 | 用 CYQ-style 成本分布代理评估支撑、压力、锁仓和派发 |
| 风险执行 | 处理 T+1、涨跌停、流动性、公告、止损距离 |

## 数据与脚本

核心 fallback 数据源只依赖 Python 标准库。若需要更完整的 A 股历史行情字段，可选择安装 BaoStock 和 AKShare 作为可选依赖。

### 1. 获取日线行情

```powershell
python scripts/fetch_eastmoney_kline.py 000001 --start 20240101 --end 20260425 --adjust qfq --source auto --output 000001_daily.csv
```

说明：

- 默认 `--source auto`：如果已安装 BaoStock，会先尝试 BaoStock，然后尝试 AKShare、Eastmoney、Tencent，最后回退 Yahoo Chart。
- 启用可选源：`pip install -r requirements-optional.txt`。
- BaoStock 是本项目当前更稳定的可选免费源，免费登录后通常返回价格、成交量、成交额、涨跌幅和换手率。
- AKShare 通常能在同一响应中提供价格、成交量、成交额、振幅、涨跌幅、涨跌额和换手率，但部分 AKShare 接口可能仍受 Eastmoney 上游可用性影响。
- Eastmoney 数据通常包含较完整的成交额和换手率。
- Tencent fallback 会补齐价格/成交量，并用未复权典型价 × 成交量估算历史成交额；如能取得最新流通股本，则估算换手率。
- Yahoo fallback 可能缺少 `amount` 和 `turnover`，此时成交额/换手率相关结论应降低置信度。

显式使用可选源：

```powershell
python scripts/fetch_eastmoney_kline.py 000001 --start 20240101 --end 20260425 --adjust qfq --source baostock --output 000001_daily.csv
python scripts/fetch_eastmoney_kline.py 000001 --start 20240101 --end 20260425 --adjust qfq --source akshare --output 000001_daily.csv
```

### 2. 技术指标评分

```powershell
python scripts/score_ashare_timing.py 000001_daily.csv --entry 10.50 --stop 9.85 --json
```

输出包括：

- MA5/10/20/60/120/250
- ATR、RSI、CMF、OBV、MACD histogram
- 20 日/55 日高低点
- 成交额倍数
- 趋势阶段
- CSV 技术评分

### 3. 主力资金参考

日线代理：

```powershell
python scripts/estimate_main_force.py 000001_daily.csv --mode daily --json
```

逐笔成交模式：

```powershell
python scripts/estimate_main_force.py ticks.csv --mode ticks --json
```

逐笔模式支持字段：

```text
date,time,price,volume,amount,side,bid1,ask1
```

输出包括：

- 大单/超大单主动买入、卖出、净额。
- `ddx_amount_proxy`
- `ddx_volume_proxy`
- `ddy_absorption_proxy`
- `ddz_attack_proxy`

注意：日线模式只能计算“主力行为代理”，不能得到真实主力净流入。

### 4. 筹码分布 / CYQ 代理

```powershell
python scripts/estimate_chip_distribution.py 000001_daily.csv --lookback 250 --json
```

输出包括：

- 成本分位点：`q05/q15/q50/q85/q95`
- 成本峰：`peaks`
- 支撑峰：`support_peaks_below_close`
- 压力峰：`resistance_peaks_above_close`
- 获利盘比例：`profit_ratio`
- 套牢/上方压力比例：`overhead_ratio`
- 筹码集中度：`concentration`
- 生命周期状态：`lifecycle`

注意：这是本地 CYQ-style 代理，不是券商或行情软件的专有筹码分布。

## 安装 / 用于 AI Agent

将仓库克隆到你的 AI Agent 能读取本地工具、参考文档和脚本的位置：

```powershell
git clone https://github.com/non-convex/ashare-stock-timing.git
```

如果你的 Agent 支持 skill-style 本地目录，可以克隆到对应的 skills 目录。例如：

```powershell
git clone https://github.com/non-convex/ashare-stock-timing.git C:/path/to/agent-skills/ashare-stock-timing
```

或在 macOS/Linux：

```bash
git clone https://github.com/non-convex/ashare-stock-timing.git <agent-skills-dir>/ashare-stock-timing
```

之后 Agent 可以加载 `SKILL.md`，调用 `scripts/` 下的脚本，并按需读取 `references/` 下的方法论文件，用于回答 A 股技术面、趋势或买卖点问题。

## 典型使用方式

用户问题：

> 帮我分析一下 000001 的技术面，现在有没有买点？

Agent 推荐流程：

```powershell
python scripts/fetch_eastmoney_kline.py 000001 --start 20240101 --end 20260425 --adjust qfq --source auto --output 000001_daily.csv
python scripts/score_ashare_timing.py 000001_daily.csv --json
python scripts/estimate_main_force.py 000001_daily.csv --mode daily --json
python scripts/estimate_chip_distribution.py 000001_daily.csv --lookback 250 --json
```

然后结合：

- 大盘与板块环境。
- 最新公告、减持、解禁、停复牌、ST 风险。
- 龙虎榜、两融、大宗交易、沪深股通等实时信息。
- T+1、涨跌停、流动性和止损距离。

最终输出：

- 可行动 / 观察 / 回避。
- 买点触发条件。
- 加仓条件。
- 止损和失效条件。
- 减仓和卖出规则。
- 风险和缺失数据。

## 文件结构

```text
.
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── chip-distribution-methods.md
│   ├── data-sources.md
│   ├── main-force-methods.md
│   ├── methodology.md
│   └── report-template.md
└── scripts/
    ├── estimate_chip_distribution.py
    ├── estimate_main_force.py
    ├── fetch_eastmoney_kline.py
    └── score_ashare_timing.py
├── requirements-optional.txt
```

## 重要限制

- 本项目不是投资建议，也不保证收益。
- 本项目不做基本面或估值判断。
- “主力资金”“主力净流入”“筹码分布”均为模型或代理指标，不是交易所直接披露的真实账户数据。
- 脚本计算结果必须结合价格结构、板块环境、公告风险、流动性和实际可执行性使用。
- A 股存在 T+1、涨跌停、停牌、公告跳空、流动性断层等特殊风险。

## License

MIT License. See [LICENSE](./LICENSE).
