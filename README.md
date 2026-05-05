<div align="center">

# 🔨 CommitForge

**Lightweight AI-Powered Git Commit Message Generator & Conventional Commits Validator CLI**

[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Zero-success.svg)]()
[![Tests: 131](https://img.shields.io/badge/Tests-131%20passed-brightgreen.svg)]()

**[简体中文](#-简体中文) | [繁體中文](#-繁體中文) | [English](#-english)**

---

<p>
<img src="https://img.shields.io/badge/✨_Multi--LLM_Backend-OpenAI%20%7C%20Anthropic%20%7C%20DeepSeek%20%7C%20Ollama%20%7C%20Gemini-blueviolet" />
<img src="https://img.shields.io/badge/🧠_Offline_Rules_Engine-Zero_AI_Needed-success" />
<img src="https://img.shields.io/badge/📋_Conventional_Commits-v1.0.0-orange" />
<img src="https://img.shields.io/badge/🌍_Multi_Language-EN%20%7C%20ZH-informational" />
</p>

</div>

---

## 🇨🇳 简体中文

### 🎉 项目介绍

**CommitForge** 是一款轻量级的终端 Git 提交信息智能生成与规范化 CLI 工具。它能够自动分析 Git 暂存区的代码变更，结合 AI 大模型或离线规则引擎，生成符合 [Conventional Commits](https://www.conventionalcommits.org/) 规范的高质量提交信息。

**解决的核心痛点：**
- ❌ 每次提交都要苦思冥想写什么 commit message
- ❌ 团队提交信息风格不统一，难以追溯变更历史
- ❌ 现有 AI 提交工具依赖复杂，安装配置繁琐
- ❌ 无法离线使用，必须联网才能生成提交信息

**自研差异化亮点：**
- 🚀 **零运行时依赖** — 仅使用 Python 标准库，无需安装任何第三方包
- 🧠 **双引擎架构** — AI 智能生成 + 离线规则引擎，有无网络都能用
- 🔌 **多 LLM 后端** — 支持 OpenAI、Anthropic、DeepSeek、Ollama（本地）、Google Gemini
- 📋 **规范验证器** — 内置 Conventional Commits 完整校验，自动修复建议
- 🪝 **Git Hook 集成** — 一键安装钩子，每次提交自动生成信息
- 📊 **历史分析** — 学习仓库提交风格，越用越懂你
- 🌍 **中英双语** — 原生中英文支持，不是机翻

### ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🤖 **AI 智能生成** | 支持 5 大 LLM 后端，智能分析代码变更生成精准提交信息 |
| 🧩 **离线规则引擎** | 基于关键词检测、文件类型推断、变更幅度分析的纯本地生成方案 |
| ✅ **Conventional Commits 校验** | 完整支持 v1.0.0 规范，包含类型/作用域/破坏性变更验证 |
| 📊 **提交历史分析** | 统计提交类型分布、学习团队风格、提供改进建议 |
| 🪝 **Git Hook 集成** | 自动安装 `prepare-commit-msg` 钩子，提交前自动生成 |
| ⚙️ **灵活配置** | TOML 配置文件 + 环境变量 + CLI 参数，三级优先级 |
| 🎨 **精美终端输出** | 彩色高亮、表格展示、进度指示，终端体验一流 |
| 🧪 **131 个测试** | 完整的单元测试覆盖，代码质量有保障 |

### 🚀 快速开始

**环境要求：** Python 3.8+

```bash
# 克隆仓库
git clone https://github.com/gitstq/CommitForge.git
cd CommitForge

# 安装（开发模式）
pip install -e .

# 验证安装
commitforge --version
```

**一键使用：**

```bash
# 暂存你的变更
git add .

# 生成提交信息（离线规则引擎，无需网络）
commitforge gen

# 使用 AI 生成（需配置 API Key）
commitforge gen --backend openai

# 中文输出
commitforge gen --lang zh --emoji
```

### 📖 详细使用指南

#### 生成提交信息

```bash
commitforge                        # 分析暂存区变更，生成提交信息
commitforge gen                    # 同上
commitforge gen --backend deepseek # 使用 DeepSeek 后端
commitforge gen --no-ai            # 强制使用离线规则引擎
commitforge gen --lang zh          # 中文输出
commitforge gen --type feat        # 强制提交类型为 feat
commitforge gen --scope api        # 强制作用域为 api
commitforge gen --emoji            # 在提交信息中包含 Emoji
commitforge gen --dry-run          # 预览模式，不实际提交
commitforge gen -v                 # 详细输出模式
```

#### 验证提交信息

```bash
commitforge check                  # 验证最近一次提交信息
commitforge check --lang zh        # 中文输出验证结果
```

#### 提交历史分析

```bash
commitforge history                # 分析最近 50 次提交
commitforge history -n 100         # 分析最近 100 次提交
commitforge history --stats-only   # 仅显示统计数据
```

#### Git Hook 管理

```bash
commitforge hook install           # 安装 prepare-commit-msg 钩子
commitforge hook uninstall         # 卸载钩子
commitforge hook status            # 查看钩子状态
```

#### 配置管理

```bash
commitforge init                   # 创建默认配置文件
commitforge init --install-hook    # 创建配置并安装钩子
commitforge config show            # 显示当前配置
```

#### 配置文件示例

在项目根目录创建 `.commitforge.toml`：

```toml
backend = "rules"          # 默认后端: rules / openai / anthropic / deepseek / ollama / gemini
language = "zh"            # 输出语言: en / zh
emoji = true               # 是否包含 Emoji
verbose = false            # 详细输出
history_count = 50         # 历史分析提交数

[openai]
api_key = "sk-xxx"         # OpenAI API Key
model = "gpt-4o-mini"      # 模型名称
base_url = "https://api.openai.com/v1"
temperature = 0.7

[deepseek]
api_key = "sk-xxx"         # DeepSeek API Key
model = "deepseek-chat"
base_url = "https://api.deepseek.com/v1"

[ollama]
model = "llama3"           # 本地模型名称
base_url = "http://localhost:11434"
```

#### 环境变量

| 变量名 | 说明 |
|--------|------|
| `COMMITFORGE_BACKEND` | 默认 AI 后端 |
| `COMMITFORGE_LANGUAGE` | 输出语言 (en/zh) |
| `COMMITFORGE_OPENAI_API_KEY` | OpenAI API Key |
| `COMMITFORGE_ANTHROPIC_API_KEY` | Anthropic API Key |
| `COMMITFORGE_DEEPSEEK_API_KEY` | DeepSeek API Key |
| `COMMITFORGE_GEMINI_API_KEY` | Google Gemini API Key |
| `COMMITFORGE_OLLAMA_BASE_URL` | Ollama 服务地址 |
| `NO_COLOR` | 禁用彩色输出 |

### 💡 设计思路与迭代规划

**设计理念：** CommitForge 遵循"零依赖、双引擎、可扩展"的设计哲学。核心引擎完全基于 Python 标准库实现，确保在任何 Python 环境中都能开箱即用。AI 后端作为可选增强，通过统一的接口抽象，支持任意 LLM 服务。

**技术选型原因：**
- **Python 标准库** — 最大化兼容性，零安装成本
- **TOML 配置** — 现代化配置格式，可读性强
- **Conventional Commits** — 业界标准规范，生态完善

**后续迭代计划：**
- [ ] 支持 GitHub/GitLab Commitizen 集成
- [ ] 添加交互式 TUI 选择界面
- [ ] 支持自定义提交信息模板
- [ ] 添加 VS Code / JetBrains 插件
- [ ] 支持更多 AI 后端（通义千问、文心一言等国产模型）

### 📦 安装与部署

```bash
# 从 PyPI 安装（即将发布）
pip install commitforge

# 从源码安装
git clone https://github.com/gitstq/CommitForge.git
cd CommitForge
pip install -e .

# 验证
commitforge --version
commitforge examples
```

### 🤝 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feat/amazing-feature`)
3. 提交变更 (`git commit -m 'feat: add amazing feature'`)
4. 推送分支 (`git push origin feat/amazing-feature`)
5. 提交 Pull Request

提交信息请遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范。

### 📄 开源协议

本项目基于 [MIT License](LICENSE) 开源。

---

## 🇹🇼 繁體中文

### 🎉 專案介紹

**CommitForge** 是一款輕量級的終端 Git 提交資訊智慧生成與規範化 CLI 工具。它能夠自動分析 Git 暫存區的程式碼變更，結合 AI 大模型或離線規則引擎，生成符合 [Conventional Commits](https://www.conventionalcommits.org/) 規範的高品質提交資訊。

**解決的核心痛點：**
- ❌ 每次提交都要苦思冥想寫什麼 commit message
- ❌ 團隊提交資訊風格不統一，難以追溯變更歷史
- ❌ 現有 AI 提交工具依賴複雜，安裝配置繁瑣
- ❌ 無法離線使用，必須聯網才能生成提交資訊

**自研差異化亮點：**
- 🚀 **零運行時依賴** — 僅使用 Python 標準庫，無需安裝任何第三方套件
- 🧠 **雙引擎架構** — AI 智慧生成 + 離線規則引擎，有無網路都能用
- 🔌 **多 LLM 後端** — 支援 OpenAI、Anthropic、DeepSeek、Ollama（本地）、Google Gemini
- 📋 **規範驗證器** — 內建 Conventional Commits 完整校驗，自動修復建議
- 🪝 **Git Hook 整合** — 一鍵安裝鉤子，每次提交自動生成資訊
- 📊 **歷史分析** — 學習倉庫提交風格，越用越懂你
- 🌍 **中英雙語** — 原生中英文支援，不是機翻

### ✨ 核心特性

| 特性 | 說明 |
|------|------|
| 🤖 **AI 智慧生成** | 支援 5 大 LLM 後端，智慧分析程式碼變更生成精準提交資訊 |
| 🧩 **離線規則引擎** | 基於關鍵字檢測、檔案類型推斷、變更幅度分析的純本地生成方案 |
| ✅ **Conventional Commits 校驗** | 完整支援 v1.0.0 規範，包含類型/作用域/破壞性變更驗證 |
| 📊 **提交歷史分析** | 統計提交類型分佈、學習團隊風格、提供改進建議 |
| 🪝 **Git Hook 整合** | 自動安裝 `prepare-commit-msg` 鉤子，提交前自動生成 |
| ⚙️ **靈活配置** | TOML 配置檔 + 環境變數 + CLI 參數，三級優先順序 |
| 🎨 **精美終端輸出** | 彩色高亮、表格展示、進度指示，終端體驗一流 |
| 🧪 **131 個測試** | 完整的單元測試覆蓋，程式碼品質有保障 |

### 🚀 快速開始

**環境要求：** Python 3.8+

```bash
# 克隆倉庫
git clone https://github.com/gitstq/CommitForge.git
cd CommitForge

# 安裝（開發模式）
pip install -e .

# 驗證安裝
commitforge --version
```

**一鍵使用：**

```bash
# 暫存你的變更
git add .

# 生成提交資訊（離線規則引擎，無需網路）
commitforge gen

# 使用 AI 生成（需配置 API Key）
commitforge gen --backend openai

# 中文輸出
commitforge gen --lang zh --emoji
```

### 📖 詳細使用指南

#### 生成提交資訊

```bash
commitforge                        # 分析暫存區變更，生成提交資訊
commitforge gen                    # 同上
commitforge gen --backend deepseek # 使用 DeepSeek 後端
commitforge gen --no-ai            # 強制使用離線規則引擎
commitforge gen --lang zh          # 中文輸出
commitforge gen --type feat        # 強制提交類型為 feat
commitforge gen --scope api        # 強制作用域為 api
commitforge gen --emoji            # 在提交資訊中包含 Emoji
commitforge gen --dry-run          # 預覽模式，不實際提交
commitforge gen -v                 # 詳細輸出模式
```

#### 驗證提交資訊

```bash
commitforge check                  # 驗證最近一次提交資訊
commitforge check --lang zh        # 中文輸出驗證結果
```

#### 提交歷史分析

```bash
commitforge history                # 分析最近 50 次提交
commitforge history -n 100         # 分析最近 100 次提交
commitforge history --stats-only   # 僅顯示統計資料
```

#### Git Hook 管理

```bash
commitforge hook install           # 安裝 prepare-commit-msg 鉤子
commitforge hook uninstall         # 卸載鉤子
commitforge hook status            # 查看鉤子狀態
```

#### 配置管理

```bash
commitforge init                   # 建立預設配置檔
commitforge init --install-hook    # 建立配置並安裝鉤子
commitforge config show            # 顯示當前配置
```

#### 配置檔範例

在專案根目錄建立 `.commitforge.toml`：

```toml
backend = "rules"          # 預設後端: rules / openai / anthropic / deepseek / ollama / gemini
language = "zh"            # 輸出語言: en / zh
emoji = true               # 是否包含 Emoji
verbose = false            # 詳細輸出
history_count = 50         # 歷史分析提交數

[openai]
api_key = "sk-xxx"         # OpenAI API Key
model = "gpt-4o-mini"      # 模型名稱
base_url = "https://api.openai.com/v1"
temperature = 0.7

[deepseek]
api_key = "sk-xxx"         # DeepSeek API Key
model = "deepseek-chat"
base_url = "https://api.deepseek.com/v1"

[ollama]
model = "llama3"           # 本地模型名稱
base_url = "http://localhost:11434"
```

#### 環境變數

| 變數名 | 說明 |
|--------|------|
| `COMMITFORGE_BACKEND` | 預設 AI 後端 |
| `COMMITFORGE_LANGUAGE` | 輸出語言 (en/zh) |
| `COMMITFORGE_OPENAI_API_KEY` | OpenAI API Key |
| `COMMITFORGE_ANTHROPIC_API_KEY` | Anthropic API Key |
| `COMMITFORGE_DEEPSEEK_API_KEY` | DeepSeek API Key |
| `COMMITFORGE_GEMINI_API_KEY` | Google Gemini API Key |
| `COMMITFORGE_OLLAMA_BASE_URL` | Ollama 服務位址 |
| `NO_COLOR` | 停用彩色輸出 |

### 💡 設計思路與迭代規劃

**設計理念：** CommitForge 遵循「零依賴、雙引擎、可擴展」的設計哲學。核心引擎完全基於 Python 標準庫實現，確保在任何 Python 環境中都能開箱即用。AI 後端作為可選增強，透過統一的介面抽象，支援任意 LLM 服務。

**技術選型原因：**
- **Python 標準庫** — 最大化相容性，零安裝成本
- **TOML 配置** — 現代化配置格式，可讀性強
- **Conventional Commits** — 業界標準規範，生態完善

**後續迭代計畫：**
- [ ] 支援 GitHub/GitLab Commitizen 整合
- [ ] 新增互動式 TUI 選擇介面
- [ ] 支援自訂提交資訊範本
- [ ] 新增 VS Code / JetBrains 外掛
- [ ] 支援更多 AI 後端（通義千問、文心一言等國產模型）

### 📦 安裝與部署

```bash
# 從 PyPI 安裝（即將發布）
pip install commitforge

# 從原始碼安裝
git clone https://github.com/gitstq/CommitForge.git
cd CommitForge
pip install -e .

# 驗證
commitforge --version
commitforge examples
```

### 🤝 貢獻指南

歡迎貢獻！請遵循以下步驟：

1. Fork 本倉庫
2. 建立功能分支 (`git checkout -b feat/amazing-feature`)
3. 提交變更 (`git commit -m 'feat: add amazing feature'`)
4. 推送分支 (`git push origin feat/amazing-feature`)
5. 提交 Pull Request

提交資訊請遵循 [Conventional Commits](https://www.conventionalcommits.org/) 規範。

### 📄 開源協議

本專案基於 [MIT License](LICENSE) 開源。

---

## 🇺🇸 English

### 🎉 Introduction

**CommitForge** is a lightweight terminal Git commit message intelligent generation and standardization CLI tool. It automatically analyzes staged Git changes and leverages AI models or an offline rules engine to generate high-quality commit messages that comply with the [Conventional Commits](https://www.conventionalcommits.org/) specification.

**Core Pain Points Solved:**
- ❌ Struggling to write meaningful commit messages every time
- ❌ Inconsistent commit styles across teams, making history hard to trace
- ❌ Existing AI commit tools are complex with heavy dependencies
- ❌ Cannot work offline — always requires network access

**Differentiation Highlights:**
- 🚀 **Zero Runtime Dependencies** — Uses only Python standard library, no third-party packages needed
- 🧠 **Dual-Engine Architecture** — AI-powered generation + offline rules engine, works with or without internet
- 🔌 **Multi-LLM Backend** — Supports OpenAI, Anthropic, DeepSeek, Ollama (local), Google Gemini
- 📋 **Conventional Commits Validator** — Full v1.0.0 spec support with auto-fix suggestions
- 🪝 **Git Hook Integration** — One-click hook installation for automatic message generation
- 📊 **History Analysis** — Learns from your repo's commit patterns, gets smarter over time
- 🌍 **Multi-Language** — Native English and Chinese support

### ✨ Core Features

| Feature | Description |
|---------|-------------|
| 🤖 **AI-Powered Generation** | 5 major LLM backends for intelligent code change analysis and precise message generation |
| 🧩 **Offline Rules Engine** | Pattern-based local generation using keyword detection, file type inference, and change magnitude analysis |
| ✅ **Conventional Commits Validation** | Full v1.0.0 spec support including type/scope/breaking change verification |
| 📊 **Commit History Analysis** | Statistics on commit type distribution, team style learning, and improvement suggestions |
| 🪝 **Git Hook Integration** | Auto-installs `prepare-commit-msg` hook for seamless pre-commit generation |
| ⚙️ **Flexible Configuration** | TOML config files + environment variables + CLI flags with 3-level priority |
| 🎨 **Beautiful Terminal Output** | Colored highlights, table displays, progress indicators for a premium terminal experience |
| 🧪 **131 Tests** | Comprehensive unit test coverage ensuring code quality |

### 🚀 Quick Start

**Requirements:** Python 3.8+

```bash
# Clone the repository
git clone https://github.com/gitstq/CommitForge.git
cd CommitForge

# Install (development mode)
pip install -e .

# Verify installation
commitforge --version
```

**Quick Usage:**

```bash
# Stage your changes
git add .

# Generate commit message (offline rules engine, no network needed)
commitforge gen

# Use AI generation (requires API key configuration)
commitforge gen --backend openai

# With emoji
commitforge gen --emoji
```

### 📖 Detailed Usage Guide

#### Generate Commit Messages

```bash
commitforge                        # Analyze staged changes and generate message
commitforge gen                    # Same as above
commitforge gen --backend deepseek # Use DeepSeek backend
commitforge gen --no-ai            # Force offline rules engine
commitforge gen --lang zh          # Chinese output
commitforge gen --type feat        # Force commit type to feat
commitforge gen --scope api        # Force scope to api
commitforge gen --emoji            # Include emoji in message
commitforge gen --dry-run          # Preview mode, don't actually commit
commitforge gen -v                 # Verbose output mode
```

#### Validate Commit Messages

```bash
commitforge check                  # Validate last commit message
commitforge check --lang zh        # Chinese output for validation results
```

#### Commit History Analysis

```bash
commitforge history                # Analyze last 50 commits
commitforge history -n 100         # Analyze last 100 commits
commitforge history --stats-only   # Show statistics only
```

#### Git Hook Management

```bash
commitforge hook install           # Install prepare-commit-msg hook
commitforge hook uninstall         # Uninstall hook
commitforge hook status            # Show hook status
```

#### Configuration

```bash
commitforge init                   # Create default config file
commitforge init --install-hook    # Create config and install hook
commitforge config show            # Show current configuration
```

#### Configuration File Example

Create a `.commitforge.toml` file in your project root:

```toml
backend = "rules"          # Default backend: rules / openai / anthropic / deepseek / ollama / gemini
language = "en"            # Output language: en / zh
emoji = true               # Include emoji
verbose = false            # Verbose output
history_count = 50         # History analysis commit count

[openai]
api_key = "sk-xxx"         # OpenAI API Key
model = "gpt-4o-mini"      # Model name
base_url = "https://api.openai.com/v1"
temperature = 0.7

[deepseek]
api_key = "sk-xxx"         # DeepSeek API Key
model = "deepseek-chat"
base_url = "https://api.deepseek.com/v1"

[ollama]
model = "llama3"           # Local model name
base_url = "http://localhost:11434"
```

#### Environment Variables

| Variable | Description |
|----------|-------------|
| `COMMITFORGE_BACKEND` | Default AI backend |
| `COMMITFORGE_LANGUAGE` | Output language (en/zh) |
| `COMMITFORGE_OPENAI_API_KEY` | OpenAI API Key |
| `COMMITFORGE_ANTHROPIC_API_KEY` | Anthropic API Key |
| `COMMITFORGE_DEEPSEEK_API_KEY` | DeepSeek API Key |
| `COMMITFORGE_GEMINI_API_KEY` | Google Gemini API Key |
| `COMMITFORGE_OLLAMA_BASE_URL` | Ollama service URL |
| `NO_COLOR` | Disable colored output |

### 💡 Design Philosophy & Roadmap

**Design Philosophy:** CommitForge follows a "zero-dependency, dual-engine, extensible" philosophy. The core engine is built entirely on Python's standard library, ensuring it works out of the box in any Python environment. AI backends serve as optional enhancements through a unified interface abstraction.

**Technology Choices:**
- **Python Standard Library** — Maximum compatibility, zero installation cost
- **TOML Configuration** — Modern config format with excellent readability
- **Conventional Commits** — Industry standard with a mature ecosystem

**Roadmap:**
- [ ] GitHub/GitLab Commitizen integration
- [ ] Interactive TUI selection interface
- [ ] Custom commit message templates
- [ ] VS Code / JetBrains plugins
- [ ] Additional AI backends (Qwen, ERNIE Bot, etc.)

### 📦 Installation & Deployment

```bash
# Install from PyPI (coming soon)
pip install commitforge

# Install from source
git clone https://github.com/gitstq/CommitForge.git
cd CommitForge
pip install -e .

# Verify
commitforge --version
commitforge examples
```

### 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork this repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

Please follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages.

### 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

**Made with ❤️ by [gitstq](https://github.com/gitstq)**

**⭐ If you find this project helpful, please give it a star! ⭐**

</div>
