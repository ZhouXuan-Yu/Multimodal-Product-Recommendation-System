# 模块化本地推荐系统运行说明

## 1. 安装依赖
```bash
pip install -r requirements.txt
```

> 前端依赖（在 `module_frontend_vue/` 内执行）：
```bash
npm install vue@3 axios echarts
```

## 2. 模块一：初始化本地数据
```bash
python module_scraper/web_scraper.py --limit 30
```
生成：
- `data/images/`
- `data/meta/products.json`
- `data/meta/users_profile.json`

## 3. 模块二：多模态向量入库
```bash
python module_rag_ai/vector_db_manager.py
```

## 4. 模块三：启动 FastAPI
```bash
uvicorn module_backend.main_api:app --host 0.0.0.0 --port 8000 --reload
```

环境变量：
```bash
export DEEPSEEK_API_KEY=your_api_key_here
```

## 5. 模块四：启动 Vue 前端
在 `module_frontend_vue/` 项目中按你已有工具链启动（Vite 或 Vue CLI 均可）。

## 6. 模块五：启动 PyQt5 管理端
```bash
python module_admin_pyqt/main_window.py
```
