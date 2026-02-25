# 🚀 多模态商品推荐系统 - 启动指令

## 快速启动（推荐）

### 一键智能启动
```bash
python run.py
```
**自动检测环境并运行最合适版本**

### 快速配置启动
```bash
python quick_start.py
```
**自动配置环境并启动程序**

---

## 启动方式对比

| 方式 | 命令 | 特点 | 适用场景 |
|------|------|------|----------|
| **智能启动** | `python run.py` | 自动检测环境，智能降级 | ⭐ 推荐 |
| **完整版本** | `python main_enterprise.py` | 企业级架构，全功能 | 需要完整环境 |
| **简化版本** | `python main.py` | 基础功能，少依赖 | 快速测试 |
| **命令行演示** | `python cli_demo.py` | 纯文本界面，无GUI | 环境受限 |
| **一键配置** | `python quick_start.py` | 自动配置环境 | 首次使用 |

---

## 平台特定启动

### Windows
```bash
# 双击运行
start.bat

# 或命令行
python run.py
```

### Linux/macOS
```bash
# 添加执行权限
chmod +x start.sh

# 运行
./start.sh

# 或直接
python run.py
```

---

## 环境配置步骤

### 1. 自动配置（推荐）
```bash
python quick_start.py
```

### 2. 手动配置
```bash
# 创建Conda环境
conda env create -f requirements/environment.yml
conda activate jin

# 或手动安装
pip install PyQt6 numpy pandas matplotlib seaborn scikit-learn pillow
```

### 3. 数据库初始化（可选）
```bash
python scripts/init_database.py
```

---

## 默认账户信息

- **管理员**: `admin` / `admin`
- **用户**: `user1` / `123456`

---

## 故障排除

### 问题1: PyQt6启动失败
```bash
# 解决方案
pip uninstall PyQt6 PyQt6-Qt6
conda install pyqt
# 或使用命令行版本
python cli_demo.py
```

### 问题2: 数据库连接失败
```bash
# 检查MySQL是否运行
# 或跳过数据库，使用模拟数据
python main.py
```

### 问题3: Conda环境问题
```bash
# 重新创建环境
conda env remove -n jin -y
conda env create -f requirements/environment.yml
```

### 问题4: 依赖安装失败
```bash
# 使用国内源
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple package_name
```

---

## 系统要求

### 最低配置
- Python 3.8+
- 4GB RAM
- 2GB磁盘空间

### 推荐配置
- Python 3.10+
- 8GB RAM
- 5GB磁盘空间
- 支持OpenGL的显卡（用于PyQt6）

---

## 文件说明

```
├── run.py                    # 智能启动脚本 ⭐
├── quick_start.py           # 一键配置启动
├── main_enterprise.py       # 企业级完整版本
├── main.py                  # 简化版本
├── cli_demo.py              # 命令行演示
├── start.bat                # Windows批处理
├── start.sh                 # Linux/macOS脚本
├── START_GUIDE.md          # 详细启动指南
└── RUN_COMMANDS.txt        # 指令合集
```

---

## 验证启动成功

启动成功标志：
```
============================================================
多模态商品推荐系统 - 登录
============================================================

用户名: ________
密码: __________

[登录] [注册]

演示账户: admin/admin 或 user1/123456
```

---

## 获取帮助

1. **查看日志**: `logs/app.log`
2. **详细指南**: `START_GUIDE.md`
3. **环境检查**: `python cli_demo.py` 选择选项5
4. **界面预览**: `python simple_ui_demo.py`

---

## 🎯 推荐使用流程

1. **首次使用**: `python quick_start.py`（自动配置）
2. **日常使用**: `python run.py`（智能启动）
3. **开发调试**: `python main.py`（简化版本）
4. **演示展示**: `python cli_demo.py`（命令行界面）

**祝你使用愉快！🎊**

