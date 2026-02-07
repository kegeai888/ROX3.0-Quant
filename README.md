
# 🚀 ROX 3.0 Quant Platform - 专业级全资产量化投研系统

![ROX 3.0 Banner](https://img.shields.io/badge/ROX-3.0_Pro-blueviolet?style=for-the-badge&logo=python)
![Python](https://img.shields.io/badge/python-3.9+-blue?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=flat-square&logo=fastapi&logoColor=white)
![Vue/Tailwind](https://img.shields.io/badge/Frontend-Tailwind_CSS-38B2AC?style=flat-square&logo=tailwindcss&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)

**ROX 3.0** 是一款专为高阶个人投资者和小型私募团队设计的**开源量化投研平台**。它打破了传统且昂贵的机构级终端限制，将**A股、美股、加密货币**三大市场数据整合于统一的现代化界面中，并提供从宏观分析、策略回测到模拟交易的全流程支持。

> **当前状态**: ✅ 生产就绪 (Production Ready) - Phase 1-6 功能已全部交付

---

## 🌟 核心亮点 (Key Features)

### 🌍 1. 全球市场覆盖 (Multi-Asset)
不再需要在多个看盘软件间切换。ROX 3.0 通过统一的数据抽象层 (`DataProvider`)，实现了跨市场的无缝体验：
- **A股 (CN)**: 集成 `AkShare`，提供精确的股票、指数实时行情及历史 K 线。
- **美股 (US)**: 集成 `yfinance`，支持纳斯达克/纽交所全市场毫秒级数据。
- **加密货币 (Crypto)**: 集成 `ccxt`，直连 Binance/OKX 等头部交易所，支持 BTC/ETH 等数字资产。
- **一键切换**: 顶部导航栏毫秒级切换市场视图，系统自动调整底层数据源与计价单位。

### 🧠 2. 机构级策略引擎 (Strategy Engine)
- **Tick 级高精度回测**: 内置 `TickEngine`，支持基于 Order Book 的高频回测，精确模拟滑点与成交撮合。
- **算法交易 (Algo Trading)**: 
    - **TWAP**: 时间加权平均与 VWAP 成交量加权算法，大额订单智能拆单。
    - **Grid Trading**: 经典的网格交易策略，自动化高抛低吸。
- **策略超市 (Strategy Store)**: 社区化策略管理中心，支持一键安装/卸载策略插件（如 *Grid Master*, *Momentum Alpha*, *R-Breaker*）。

### 📊 3. 宏观与数据智能 (Macro & Intelligence) - New!
- **宏观仪表盘 (Macro Dashboard)**: 
    - 实时接入国家统计局数据，可视化展示 **GDP, CPI/PPI, PMI** 趋势。
    - **M1-M2 剪刀差**: 独家的流动性监测图表，精准辅助判断牛熊周期。
- **全天候资讯 (Info Radar)**: 
    - 聚合 WallStreet/EastMoney 7x24 小时全球财经快讯。
    - 实时推送持仓股的重要公告（财报预告、重组停牌等）。
- **主题挖掘 (Theme Mining)**: 
    - 独创“概念资金流”组件，追踪一级市场（VC/PE）热钱流向，捕捉如*固态电池*、*低空经济*等早期风口。

### ☁️ 4. 云端同步与社交 (Cloud & Social)
- **私有云同步**: 完整的系统快照备份与恢复机制 (ZIP)。支持在公司/家庭电脑间一键无缝迁移所有策略与设置。
- **交易员身份系统**: 自定义头像、简介与能力标签 (Tags)，构建个人投研品牌。
- **Copy Trading (Beta)**: 模拟跟单引擎，支持订阅信号源 (`SignalSource`) 并自动执行跟单逻辑。

---

## 🛠️ 系统架构 (Architecture)

ROX 3.0 采用前后端分离的现代化架构，确保高性能与可扩展性：

```mermaid
graph TD
    User[用户 Browser] --> |HTTP/WebSocket| Frontend[ROX UI (Vue/Tailwind)]
    Frontend --> |REST API| Backend[FastAPI Server]
    
    subgraph "Backend Core"
        Backend --> QuantEngine[量化引擎 (TickEngine/Backtest)]
        Backend --> DataManager[数据管家 (Pandas/SQLite)]
        Backend --> CloudSync[云同步模块]
    end
    
    subgraph "External Data Sources"
        DataManager --> |API| AkShare[A股数据 (AkShare)]
        DataManager --> |API| YFinance[美股数据 (Yahoo)]
        DataManager --> |API| CCXT[加密货币 (Exchanges)]
        DataManager --> |API| EastMoney[资讯/公告]
        DataManager --> |API| StatsGov[国家统计局]
    end
```

---

## 🚀 快速上手 (Quick Start)

### 1. 环境准备
确保您的系统已安装 **Python 3.9+** 和 **Git**。

### 2. 获取代码
```bash
git clone https://github.com/a1050154895/ROX3.0-Quant.git
cd ROX3.0-Quant
```

### 3. 安装依赖
推荐使用虚拟环境 (Virtualenv/Conda) 运行：
```bash
# 创建虚拟环境 (可选)
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# 安装核心库
pip install -r requirements.txt
```

### 4. 启动系统
```bash
# 开发模式启动 (支持热重载)
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

### 5. 开始使用
打开浏览器访问: `http://localhost:8002`
- **默认账户**: 系统初次运行会自动初始化数据库，无需手动注册。
- **数据源**: 初次加载 A 股数据可能需要 1-2 分钟用于缓存初始化。

---

## 📂 项目目录结构

```
ROX3.0-Quant/
├── app/
│   ├── api/                 # API 路由 (Endpoints for Market, Trade, Macro...)
│   ├── rox_quant/           # 量化核心 (TickEngine, Algos, DataProviders)
│   │   ├── datasources/     # 数据源适配器 (AkShare, CCXT...)
│   │   └── algos/           # 交易算法实现
│   ├── strategies/          # 用户策略目录 (Drop your .py files here)
│   ├── static/              # 前端静态资源 (JS, CSS, Images)
│   └── templates/           # HTML 模板入口
├── data/
│   ├── db/                  # SQLite 数据库 (rox.db)
│   └── documents/           # 知识库与文档数据
├── tests/                   # 单元测试与验证脚本
├── requirements.txt         # 依赖清单
└── README.md                # 项目文档
```

---

## ⚠️ 免责声明 (Disclaimer)

本项目 (`ROX 3.0`) 仅供**量化投研学习与研究**使用。
1. **数据说明**: 项目引用的数据源 (如 AkShare, Yahoo) 均来自公开网络，不保证数据的实时性与准确性。
2. **风险提示**: 量化交易存在极高风险，程序的历史回测业绩不代表未来收益。请勿直接将未经验证的策略用于实盘交易。
3. **免责条款**: 开发者不对任何因使用本软件而导致的资金损失负责。

---

## 🤝 贡献与支持 (Contributing)

ROX 3.0 是一个开源项目，我们需要您的参与！
- **提交 Bug**: 请在 Issues 页面反馈。
- **贡献代码**: 欢迎提交 Pull Request，不论是修复 Bug 还是新增策略。

---

MIT License © 2026 ROX Quant Team
