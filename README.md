## 基于视觉语义对齐的多模态场景理解与检索系统

一个集 **多模态推荐、RAG 检索问答、用户洞察可视化、订单管理** 于一体的端到端实验平台。项目整体采用「训练 - 后端 API - Vue 前端 - PyQt 管理大屏」四层架构，支持完全本地离线运行。

- **后端（`module_backend`）**：FastAPI + Chroma + DeepSeek RAG，多模态推荐与订单、用户画像 API。
- **前端（`module_frontend_vue`）**：Vue 3 + Vite，用户侧推荐与洞察工作台。
- **管理端（`module_admin_pyqt`）**：PyQt5 + pyqtgraph，管理员监控大屏（GMV、订单、活跃趋势、画像表格）。
- **训练与特征工程**：见 `TRAINING_README.md`，完成多模态特征提取与个性化模型训练。

---

## 1. 环境准备

### 1.1 Python 环境

- **Python 版本**：3.8+（推荐 3.10+）
- **推荐方式（Conda）**：

```bash
cd /path/to/Multimodal-Product-Recommendation-System

# 1）根据仓库提供的环境文件创建环境
conda env create -f requirements/environment.yml

# 2）激活环境
conda activate jin

# 3）如需使用 pip 安装（或不使用 Conda）
pip install -r requirements.txt
```

> 如需 GPU 训练和多模态模型加速，请参考 `TRAINING_README.md` 中的 GPU 安装说明（PyTorch + Transformers 等）。

### 1.2 Node.js 环境（前端）

- **Node.js**：建议 18+（确保 npm / pnpm 可用）

```bash
cd module_frontend_vue
npm install
```

安装完成后即可使用 `npm run dev / build / preview` 等命令。

---

## 2. 整体架构与模块说明

### 2.1 整体架构概览

```text
训练与特征工程（training, data, models）
        │
        ▼
FastAPI 后端（module_backend.main_api）
        │   ├─ 多模态召回与排序（CLIP + 推荐引擎）
        │   ├─ 用户画像 & 洞察（UserInsightEngine + DeepSeekAgent）
        │   ├─ 订单管理与本地 JSON 持久化
        │   └─ 本地 Chroma 向量库 /static 图片服务
        ▼
Vue 前端（module_frontend_vue）
        │   ├─ 推荐列表 & 搜索
        │   ├─ 洞察中心（事件流、向量偏移、桑基图、语义差分）
        │   └─ 订单创建 / 支付 / 查询
        ▼
PyQt 管理端（module_admin_pyqt）
            ├─ GMV、订单、活跃趋势折线图
            ├─ 推荐效果数据表 & 待办事项
            └─ 核心用户画像表格
```

### 2.2 后端模块 `module_backend`

- **入口**：`module_backend/main_api.py`
- **框架**：FastAPI + Uvicorn
- **主要能力**：
  - 多模态推荐接口 `/api/recommend`
  - 用户行为日志 `/api/log_action`
  - 用户画像与洞察 `/api/user_profile/*`, `/api/insights/*`
  - LLM 对话与智能推荐 `/api/ai_chat`
  - RAG 检索接口 `/api/rag_search`
  - 订单相关接口 `/api/orders/*`（详情见 `docs/订单接口.md`）
- **依赖的内部模块**：
  - `module_rag_ai.*`：DeepSeekAgent、CLIP 向量、Chroma 管理等
  - `core.recommendation_engine.SmartRecommendationEngine`
  - `core.user_insight_engine.UserInsightEngine`
  - 本地 JSON 数据：`data/meta/*.json`、向量库：`data/vector_store`、图片：`data/images`

> 服务启动时会自动检查 / 初始化向量库（`@app.on_event("startup")`），首次运行可能需要数十秒到数分钟。

### 2.3 前端模块 `module_frontend_vue`

- **入口**：`module_frontend_vue/src/App.vue`
- **构建工具**：Vite 6 + Vue 3
- **接口封装**：`module_frontend_vue/src/api.js`
  - 默认通过 Vite 代理访问后端：前端请求 `/api/*`，由 `vite.config.js` 转发到 `http://127.0.0.1:8000`
  - 支持通过 `.env.local` 设置 `VITE_API_BASE_URL` 直连后端
- **脚本**（见 `package.json`）：
  - `npm run dev`：开发模式（默认端口 `5173`）
  - `npm run build`：打包生产构建
  - `npm run preview`：本地预览生产构建

前端包含推荐首页、洞察工作台、订单列表与详情等页面，使用 ECharts 进行可视化。

### 2.4 管理端模块 `module_admin_pyqt`

- **入口**：`module_admin_pyqt/main_window.py`
  - 顶部注释说明支持两种运行方式：
    - 在项目根目录：`python -m module_admin_pyqt.main_window`
    - 在当前目录：`python main_window.py`
- **样式与数据**：
  - 皮肤文件：`module_admin_pyqt/admin_dashboard.qss`
  - 数据来源：`module_admin_pyqt/local_data_monitor.py`
    - `data/meta/products.json`
    - `data/meta/users_profile.json`
    - `data/meta/orders.json`
    - `data/metrics/recommender_eval.json`
    - 日志：`logs/app.log`
- **主要界面元素**：
  - 左侧导航栏：品牌、总览仪表盘、刷新按钮
  - 顶部 Tile：GMV、订单总数、活跃用户数、CTR
  - 中部：活跃度 / 订单趋势折线 + 推荐效果指标表 + 待办事项
  - 底部：核心用户画像表（支持标签映射与画像说明 tooltip）

即使还没有真实数据，`local_data_monitor.py` 也会生成模拟用户和趋势，保证仪表盘不空白。

---

## 3. 启动方式与指令大全

本节整理项目常用指令，分为 **环境准备 / 后端 / 前端 / 管理端 / 训练与工具 / 故障排查** 六类。

### 3.1 环境与基础命令

```bash
# 克隆仓库
git clone <your-repo-url>
cd Multimodal-Product-Recommendation-System

# Conda 创建 + 激活环境
conda env create -f requirements/environment.yml
conda activate jin

# 或使用 pip 安装依赖
pip install -r requirements.txt

# 验证 Python / Conda
python --version
conda --version
conda env list
```

> 如需重新创建环境：  
> `conda env remove -n jin -y && conda env create -f requirements/environment.yml`

### 3.2 后端 API 服务（FastAPI）

在仓库根目录（包含 `module_backend` 的目录）下执行：

```bash
# 方式一：直接运行模块（推荐开发时使用）
python -m module_backend.main_api

# 方式二：手动使用 uvicorn（等价于 main_api 底部的 __main__ 启动逻辑）
uvicorn module_backend.main_api:app --host 0.0.0.0 --port 8000 --reload
```

默认监听 `0.0.0.0:8000`，静态图片路径挂载为 `/static/images`。

### 3.3 前端 Vue 应用

在 `module_frontend_vue` 目录下：

```bash
cd module_frontend_vue

# 安装依赖（首次）
npm install

# 开发模式（默认 http://localhost:5173）
npm run dev

# 构建生产包
npm run build

# 预览生产构建
npm run preview
```

开发模式下，请确保后端已运行在 `127.0.0.1:8000`，Vite 代理（见 `vite.config.js`）会自动转发 `/api` 和 `/static` 请求。

如需在其他机器访问开发服务，可直接访问：`http://<你的局域网 IP>:5173`。

### 3.4 管理端 PyQt 仪表盘

在仓库根目录下（推荐）：

```bash
# 方式一：通过模块路径运行
python -m module_admin_pyqt.main_window

# 方式二：进入目录后直接运行脚本
cd module_admin_pyqt
python main_window.py
```

> 注意：PyQt 管理端主要读取本地 JSON / 日志文件，不依赖 Web 服务器；  
> 建议在推荐系统运行一段时间后查看，数据更丰富。

### 3.5 训练与特征工程相关指令

训练部分有专门文档 `TRAINING_README.md`，这里列出核心命令：

```bash
# 一键启动 GPU 训练 + 可视化监控
python train_with_visualization.py

# 模块化训练流程
python start_visualizer.py &
python scripts/run_training_pipeline.py run

# 分步执行
python scripts/run_training_pipeline.py download   # 下载数据集
python scripts/run_training_pipeline.py extract    # 特征提取
python scripts/run_training_pipeline.py train      # 模型训练

# 查看训练状态
python scripts/run_training_pipeline.py status

# 单独测试/工具
python test_modular_training.py
python scripts/gpu_monitor.py
python scripts/train_manager.py --mode extract --coordinator
python scripts/train_manager.py --mode train --coordinator
```

> 更多细节（数据格式、特征维度、多模态融合策略等）请参考 `TRAINING_README.md`。

### 3.6 旧版一键启动与辅助脚本（可选）

项目中保留了一些「一键启动 / 演示」脚本，整理在 `RUN_COMMANDS.txt` 中，典型示例如下（视你当前分支与版本选择性使用）：

```bash
# 智能启动脚本（根据环境自动选择最合适的入口）
python run.py

# 企业级完整版本 / 简化版 / CLI 演示
python main_enterprise.py
python main.py
python demo.py

# 环境配置与数据库初始化
python scripts/setup_environment.py
python scripts/init_database.py
```

> 上述脚本主要面向早期一体化版本；推荐在「新架构」下分别启动：后端 + 前端 + PyQt 管理端。

### 3.7 故障排查与诊断指令

```bash
# 查看后端与业务日志
cat logs/app.log

# 检查关键依赖
pip list | findstr /R "PyQt|numpy|pandas"

# 重建 Conda 环境
conda env remove -n jin -y
conda env create -f requirements/environment.yml
```

如遇前端跨域 / 网络错误，请优先确认：

- 后端 FastAPI 是否已在 `127.0.0.1:8000` 启动；
- 前端是否通过 Vite 代理访问（保持 `BASE_URL` 为空），或 `.env.local` 中的 `VITE_API_BASE_URL` 是否正确。

---

## 4. 目录结构与文件夹含义

### 4.1 顶层目录

- **`core/`**：推荐系统核心逻辑
  - `product_manager.py`：商品管理与特征访问
  - `recommendation_engine.py`：多模态推荐逻辑（召回 + 排序）
  - `user_insight_engine.py`：用户行为事件、画像生成、洞察分析
  - `user_manager.py`：用户信息与画像管理
- **`data/`**：所有离线 / 在线数据资源
  - `raw/`：原始图片与数据
  - `processed/`：预处理后的 JSON 数据（商品 / 用户 / 交互）
  - `meta/`：运行时核心元数据
    - `products.json`：商品基础信息
    - `users_profile.json`：用户画像与行为历史
    - `orders.json`：订单数据（由后端订单接口维护）
  - `images/`：商品图片（由后端通过 `/static/images` 暴露）
  - `embeddings/`：文本 / 图像 / 融合特征向量（pkl / json）
  - `vector_store/`：Chroma 向量数据库文件
  - `metrics/`：离线评估指标，如 `recommender_eval.json`
  - `cache/`：运行时缓存
- **`models/`**：本地模型文件
  - 预训练 BERT / ResNet / 融合模型、协同过滤等
- **`module_backend/`**：FastAPI 后端服务（详见上文）
- **`module_frontend_vue/`**：Vue 3 + Vite 前端项目
  - `src/api.js`：所有前端 API 封装
  - `src/*.vue`：页面与组件
  - `vite.config.js`：开发代理与构建配置
- **`module_admin_pyqt/`**：PyQt 管理后台与本地监控逻辑
  - `main_window.py`：主窗口和 UI 布局
  - `local_data_monitor.py`：数据统计与模拟
  - `admin_dashboard.qss`：QSS 主题与样式
- **`module_rag_ai/`**：RAG 与多模态嵌入模块
  - `deepseek_agent.py`：与 DeepSeek 模型交互的 Agent 封装
  - `multimodal_embedding.py`：Chinese-CLIP 等多模态向量抽取
  - `vector_db_manager.py`：Chroma 向量库管理
  - `order_agent.py` / `model_worker.py`：订单与模型协作逻辑
- **`module_scraper/`**：数据爬取与外部商品抓取工具
- **`training/`**：训练脚本（与 `TRAINING_README.md` 对应）
  - 多模态特征提取、训练协调、可视化等
- **`scripts/`**：环境初始化、数据库 / 数据初始化脚本
- **`docs/`**：文档
  - `LOCAL_MODULAR_GUIDE.md`：本地模块化运行指南
  - `流程.md`：整体业务与数据流程
  - `订单接口.md`：订单相关 API 详细说明
  - `ui设计.md`、`规则.md` 等 UI 与业务规则说明
- **`logs/`**：运行日志（如 `app.log`，供管理端与调试使用）
- **`tests/`**：测试脚本与示例
- **`MD/`、`zz/`**：历史 README / 梳理文档与草稿

### 4.2 其他重要文件

- **`pyproject.toml` / `requirements.txt`**：Python 依赖定义
- **`RUN_COMMANDS.txt`**：早期运行指令汇总（本 README 已覆盖主要命令）
- **`TRAINING_README.md`**：训练与多模态特征工程的详细说明
- **`run.py` / `main_enterprise.py` / `main.py` / `demo.py`**：一体化版本与演示入口
- **`ui/`、`visualization/`**：GUI 与训练过程可视化工具

---

## 5. 建议的日常使用流程

1. **准备环境**：根据第 1 节创建并激活 Conda 环境、安装前端依赖。
2. **启动后端**：在项目根目录运行 `python -m module_backend.main_api`。
3. **启动前端**：进入 `module_frontend_vue` 运行 `npm run dev`，浏览器访问 `http://localhost:5173`。
4. **（可选）启动管理端**：在项目根目录运行 `python -m module_admin_pyqt.main_window`，观察 GMV / 订单 / 用户画像等指标。
5. **（可选）运行训练或离线评估**：按照 `TRAINING_README.md` 执行训练流水线，更新 `data/` 与 `models/`，再重启后端以加载最新模型与向量库。

如你在使用过程中有新的运行方式或脚本，建议同步更新本 `README.md`，保持仓库说明与实际工程行为一致。

