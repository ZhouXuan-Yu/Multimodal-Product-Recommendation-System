# 多模态商品推荐系统

基于多模态融合的个性化商品推荐系统，企业级架构实现。

## 📋 项目概述

本系统通过融合商品图像视觉特征和文本语义特征，实现个性化的商品推荐。采用企业级架构设计，确保代码的可维护性、可扩展性和高性能。

### 🎯 核心特性

- **多模态融合**: 结合图像(CNN)和文本(BERT)特征的深度融合
- **实时推荐**: 支持用户行为的实时反馈和推荐更新
- **企业级架构**: 分层设计，模块化开发，易于维护和扩展
- **高性能**: 异步处理、连接池、缓存机制
- **完整测试**: 单元测试、集成测试、性能测试
- **监控日志**: 完整的日志系统和错误处理

## 🏗️ 架构设计

### 分层架构

```
┌─────────────────────────────────────┐
│            表示层 (UI)              │
│   ├── 登录界面                        │
│   ├── 主界面                          │
│   ├── 商品卡片                        │
│   └── 统计面板                        │
├─────────────────────────────────────┤
│          业务逻辑层 (Core)           │
│   ├── 推荐引擎                        │
│   ├── 用户管理                        │
│   └── 商品管理                        │
├─────────────────────────────────────┤
│            数据层 (Data)             │
│   ├── 数据库模型                      │
│   ├── 连接池                          │
│   └── 数据访问                        │
├─────────────────────────────────────┤
│            基础设施 (Utils)          │
│   ├── 配置管理                        │
│   ├── 日志系统                        │
│   ├── 异常处理                        │
│   └── 工具函数                        │
└─────────────────────────────────────┘
```

### 目录结构

```
multimodal-recommendation-system/
├── config/                 # 配置管理
│   └── settings.py        # 系统配置
├── core/                   # 业务逻辑层
│   ├── __init__.py
│   ├── recommendation_engine.py  # 推荐引擎
│   ├── user_manager.py           # 用户管理
│   └── product_manager.py        # 商品管理
├── data/                   # 数据层
│   ├── __init__.py
│   ├── database.py        # 数据库连接
│   └── models.py          # 数据模型
├── ui/                     # 用户界面层
│   ├── __init__.py
│   ├── styles.py          # 样式定义
│   ├── login_window.py    # 登录窗口
│   ├── main_window.py     # 主窗口
│   ├── product_card.py    # 商品卡片
│   └── stats_panel.py     # 统计面板
├── utils/                  # 工具层
│   ├── __init__.py
│   ├── logger.py          # 日志系统
│   └── exceptions.py      # 异常处理
├── tests/                  # 测试层
│   ├── __init__.py
│   ├── base_test.py       # 测试基础类
│   └── test_user_manager.py  # 用户管理测试
├── scripts/                # 脚本工具
│   ├── setup_environment.py  # 环境设置
│   └── init_database.py      # 数据库初始化
├── requirements/           # 依赖管理
│   ├── environment.yml    # Conda环境配置
│   └── ...               # 其他依赖文件
├── docs/                   # 文档
├── logs/                   # 日志文件
├── main_enterprise.py     # 企业级主入口
├── main.py               # 简化版本主入口
└── README.md             # 项目文档
```

## 🚀 快速开始

### 环境要求

- Python 3.10+
- MySQL 8.0+
- Miniconda/Anaconda (推荐)

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd multimodal-recommendation-system
   ```

2. **创建Conda环境**
   ```bash
   # 使用自动脚本
   python scripts/setup_environment.py

   # 或手动创建
   conda env create -f requirements/environment.yml
   conda activate jin
   ```

3. **配置数据库**
   ```bash
   # 编辑配置文件
   vim config/settings.py

   # 初始化数据库
   python scripts/init_database.py
   ```

4. **运行程序**
   ```bash
   # 企业级版本
   python main_enterprise.py

   # 或简化版本
   python main.py
   ```

### 默认账户

- 用户名: `admin`, 密码: `admin`
- 用户名: `user1`, 密码: `123456`

## 📊 功能特性

### 🔐 用户系统
- 用户注册和登录
- 个人偏好设置
- 行为历史记录
- 密码安全管理

### 🛍️ 商品管理
- 商品信息管理
- 分类浏览
- 智能搜索
- 图片上传处理

### 🎯 推荐系统
- 多模态特征融合
- 个性化推荐算法
- 实时推荐更新
- 冷启动处理

### 📈 数据可视化
- 推荐效果统计
- 用户行为分析
- 图表展示
- 实时监控

## 🔧 技术栈

### 后端框架
- **Python 3.10+**: 现代Python版本
- **PyTorch**: 深度学习框架
- **MySQL**: 关系型数据库
- **SQLAlchemy**: ORM框架

### 前端界面
- **PyQt6**: 现代化GUI框架
- **Matplotlib**: 数据可视化
- **Qt Designer**: 界面设计

### 开发工具
- **Conda**: 环境管理
- **pytest**: 测试框架
- **black**: 代码格式化
- **mypy**: 类型检查

## 🧪 测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定测试
python -m pytest tests/test_user_manager.py

# 带覆盖率测试
python -m pytest --cov=core --cov=data tests/
```

## 📈 性能优化

### 数据库优化
- 连接池管理
- 查询结果缓存
- 索引优化
- 读写分离

### 算法优化
- 批量特征提取
- GPU加速推理
- 模型量化
- 缓存机制

### 系统优化
- 异步处理
- 内存管理
- 日志轮转
- 监控告警

## 🔒 安全特性

- 密码哈希存储
- SQL注入防护
- XSS防护
- 输入验证
- 访问控制

## 📚 文档

- [API文档](./docs/api.md)
- [部署指南](./docs/deployment.md)
- [开发规范](./docs/development.md)
- [测试报告](./docs/testing.md)

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 👥 开发团队

- 项目负责人: 荆传智
- 技术架构: 企业级分层架构
- 开发语言: Python
- GUI框架: PyQt6

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者！

---

**注意**: 这是一个毕业设计项目，旨在展示多模态推荐系统的完整实现。如有问题或建议，欢迎提交Issue或Pull Request。

