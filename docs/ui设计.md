合代码和日志，核心现状是：
商品 & 向量库
products.json 由 module_scraper/web_scraper.py 生成，并通过 module_rag_ai/vector_db_manager.py 写入 Chroma 向量库 products_multimodal。
/api/recommend 用 retrieve_top_k 从向量库召回，再用 DeepSeekAgent 做排序，最后分页返回给前端。
前端商城 & 搜索/分页
Vue 商城页是 ProductWaterfall.vue，通过 fetchRecommendations 调用 /api/recommend。
搜索框 handleSearch 会把关键字发给后端，逻辑是存在的：
查询参数：{ user_id, query: keyword.value || props.query, page, page_size: 50 }。
分页按钮 goFirst/goPrev/goNext 也都在调用同一个 loadRecommendations(page)。
但后端 retrieve_top_k 又在 /api/recommend 里被限制成：top_k = min(req.page * req.page_size, 80)，最多只会召回 80 条，前端一页 50 条 ⇒ 第 2 页之后基本就「没货」，你看到的就是“底部显示一页、点了也翻不了”的效果。
行为日志与洞察
前端 App.vue 和 ProductWaterfall.vue 已经通过 logUserAction 调用 /api/log_action，把 click 等行为写入 users_profile.json 的 history。
洞察中心 InsightCenter.vue 调 /api/insights/{user_id}/events，正是用这份 history + products.json 聚合出的时间线和类目分布。
也就是说：日志采集和洞察链路已经基本打通，主要问题在：数据量、召回上限、DeepSeek 在“搜索意图理解”的利用还不够，以及 PyQt 还没直接接上这些 API。
二、整合后的整体方案（在你说的基础上做了一点“项目化拓展”）
我把你的需求拆成 5 条主线，每条都对应到现有模块，不会“推倒重来”：
本地商品 & 向量库扩容到 ≥ 3000 条
扩展 module_scraper/web_scraper.py 的采集数量，使用其内置的样本扩增逻辑，把 products.json 提升到 3000+ 条。
重新运行 module_rag_ai/vector_db_manager.py，将所有商品写入 Chroma 持久化向量库。
调整 module_backend/main_api.py 里的 retrieve_top_k 调用上限，让 /api/recommend 能真正分页浏览大量商品（例如把 80 提升到 1000+）。
前端商城的分页 & 搜索体验修正
保持 ProductWaterfall.vue 的现有 UI 风格不变，只做逻辑层优化：
修正后端召回上限导致的“只能看一页”的问题。
如有需要，增加“跳转到第 N 页”的输入框或页码按钮（目前是上一页/下一页/首页）。
搜索逻辑保持「前端仅负责发 query，后端负责理解」：
点击搜索/回车 → 调用 /api/recommend，附上自然语言 query。
后端基于 DeepSeek + 向量库来决定召回哪些商品。
可选增强：在商品列表上方展示“搜索意图标签”，让用户看到 DeepSeek 理解出的类目/风格。
搜索意图理解：DeepSeek 驱动的“自然语言 → 类型/类目/场景”
在后端基于现有 DeepSeekAgent 新增一个“搜索意图解析”方法，例如：
输入：user_id + query
输出结构化 JSON：{ intent_type, categories, style, price_range, scenario, raw_query }
将该意图用于：
召回前过滤/加权（如优先该类目商品）。
返回给前端（前端展示标签，或者日志存入用户画像，用于心理洞察）。
为避免重复接 SDK，我们沿用当前的 HTTP requests 调用方式，只是多加一种 Prompt 和解析逻辑；你给的 OpenAI SDK 版本可以作为后续重构参考，但不强制换。
用户行为记录、个性化推荐与“心理洞察”闭环
统一用 /api/log_action 标准化行为上报：view / click / add_to_cart / buy / search 等，每个行为带上权重 weight 与上下文。
后端将 history 定期/实时转换成：
行为特征：行为频次、活跃时间段、偏好类目、价格带等。
心理标签：通过 DeepSeek 对 history + 搜索意图做归纳，例如“冲动型消费者、偏爱简约风、价格敏感度中等”等，写回 users_profile.json。
/api/insights 在现有基础上增加对这些新字段的聚合展示，让“个人数据洞察中心”看到“行为趋势 + 心理画像”。
PyQt 与个人数据洞察中心的实时/准实时联动
PyQt 侧（ui/main_window.py 或 module_admin_pyqt/main_window.py）：
新增/封装一个 HTTP 客户端（用 requests + 后台线程即可），调用：
/api/recommend 获取同源的推荐结果。
/api/insights/{user_id}/events 拉取行为时间线与心理标签。
在界面上增加一个“洞察面板”或在已有统计面板中展示这些信息。
联动方式：
关键行为触发时（例如点击/收藏/下单），前端上报 /api/log_action 后：
Vue 洞察中心刷新图表（已具备）。
PyQt 侧可通过轮询或“刷新按钮”拉取最新 /api/insights 数据（先用轮询或手动刷新实现，后续再考虑 WebSocket）。
三、按步骤落地的执行计划（后面我们就照这个一步步做）
下面是我建议的实施顺序，既符合你“分步骤实现”的要求，也尽量保证每一步都能跑通、看得见效果：
步骤 1：把商品 & 向量库扩容到 ≥ 3000 条，并修复分页上限
使用 module_scraper/web_scraper.py：
调整/直接运行（命令示例，在项目根目录执行）：
  python module_scraper/web_scraper.py --limit 3000
生成至少 3000 条商品到 data/meta/products.json，并自动下载图片到 data/images/。
运行 module_rag_ai/vector_db_manager.py，重新写入向量库：
  # 简单方式：直接运行 demo，将 products 全量 upsert 进 Chroma
  python -m module_rag_ai.vector_db_manager
或在 Python 中调用：
  from module_rag_ai.vector_db_manager import load_products, VectorDBManager
  from module_rag_ai.multimodal_embedding import ChineseCLIPEmbedder
  products = load_products()
  embedder = ChineseCLIPEmbedder()
  db = VectorDBManager()
  db.upsert_products(products, embedder)
修改 module_backend/main_api.py 中 /api/recommend 对 top_k 的限制（已实现）：
  top_k = min(req.page * req.page_size, 1000)
并在降级兜底路径中也放宽到 1000 条：
  candidates = products[: min(len(products), 1000)]
验证：启动后端（uvicorn），打开前端商城，多次点击“下一页”可以真正翻页，日志中 /api/recommend 的 items_len 会随 page 变化（例如 page=1/2/3 时分别接近 page_size）。
步骤 2：前端分页/搜索体验打磨
保持 ProductWaterfall.vue 结构不变，只针对交互与状态做优化：
- **分页逻辑对齐后端**：
  - loadRecommendations 中优先使用后端返回的 data.total 判断是否还有更多数据：targetPage * pageSize >= total 视为尾页。
  - 若后端未提供 total，则继续使用 items.length < pageSize 作为 noMore 判定。
  - 分页按钮禁用条件：page<=1 或 loadingMore 时禁用“首页/上一页”，noMore 或 loadingMore 时禁用“下一页”，避免用户误触。
- **空结果体验**：
  - 当非加载中且 products 为空时展示“暂无相关商品”的空状态，并给出“尝试换一个关键词”的提示文案。
  - 保证在搜索无结果、或 query 很偏时，用户不会只看到一片空白。
- **搜索交互**：
  - 搜索框使用 keyword 作为本地输入状态，点击搜索按钮或回车触发 handleSearch，将 page 重置为 1 并调用 loadRecommendations(1)。
  - 请求参数 query 为 keyword.value || props.query || ''，确保 AI 联动场景下外部 query 生效。
  - 通过浏览器控制台观察 /api/recommend 请求与返回内容，确认搜索结果随关键字或外部 query 变化。
步骤 3：后端接入 DeepSeek 搜索意图解析
在 DeepSeekAgent 中新增 analyze_intent(query: str) 方法，调用同一个 DeepSeek API，但使用“意图分类”Prompt，返回结构化 JSON。
新增一个 Pydantic 模型与 FastAPI 路由：
方案 A：在 /api/recommend 内部调用，把 intent 一起放在响应中。
方案 B：新增 /api/search_intent，前端搜索时先拿到 intent，再调 /api/recommend。
我会倾向于 方案 A，因为对前端改动最小、体验连贯。
确保 DeepSeek API Key 只通过环境变量 DEEPSEEK_API_KEY 读取，不在代码中硬编码，也不会在日志中打印。
步骤 4：行为日志 → 用户画像 & 心理洞察的算法层
扩展 /api/log_action：
支持更多 action 类型，以及从前端传来的 extra 上下文。
在写入 history 时，附带简化的“行为特征”，例如 session id、页面来源等。
新增一个定期/实时更新画像的小函数：
读取某个用户的 history，计算类目偏好、价格偏好、活跃时间段等；
调用 DeepSeek 把这些特征总结成“心理画像标签”，写回 users_profile.json。
扩展 /api/insights 返回值，把这些标签和统计一起提供给前端；洞察中心增加相应展示模块。
步骤 5：PyQt 前端接入推荐 & 洞察 API
在 ui/main_window.py（或者 module_admin_pyqt/main_window.py）里：
新增/修改数据获取逻辑，从当前本地 RecommendationEngine 为主，逐步引入 HTTP 调用后端 API 的模式。
增加一个“用户行为与心理洞察”面板，从 /api/insights 拉数据展示。
初版先采用“手动刷新/定时轮询”的方式，后续如有需要再设计更实时的机制。
四、接下来我会怎么做
下一步我会从【步骤 1】开始落地：
在代码里调整 /api/recommend 的 top_k 限制，让分页先真正可用。
给你一套在本机上把商品扩充到 3000+ 的具体命令（基于现有 web_scraper 与 vector_db_manager）。
然后按上面的顺序，分别实现 DeepSeek 搜索意图、行为洞察算法和 PyQt 对接。
如果这个整体方案你认可，我就直接按这个顺序边改代码、边给你每一步的运行方式和验证方法。