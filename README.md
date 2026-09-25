[English](README_EN.md) | 中文

# 央视频同类账号分析器

一个爬取央视频（yspapp.cn）平台高校账号公开数据的现代桌面应用，内置数据可视化、快照对比与全高校爆款监测。界面采用 PySide6，默认浅色并支持深色切换。

## 功能

- **批量爬取** — 一键爬取 100+ 高校账号的粉丝数、播放量、视频数。支持开始/暂停/继续/停止，实时显示进度。
- **数据表格** — 可排序、可搜索的数据表，支持单位切换（个/万/亿）。武汉科技大学默认红色加粗高亮，也可自定义高亮任意学校。
- **交互图表** — 排名与对比柱图采用紧凑刻度、悬停高亮和精确值浮层；直方图、散点图支持滚轮缩放与点击标注。
- **仪表盘** — 多图表网格布局，随窗口大小自适应列数。
- **快照系统** — 每次爬取保存时间戳快照，可任选两次快照对比增长变化。自动判断时间顺序，避免反向对比。
- **对比增强** — 4 个增长排行图表，含量化误差区间（confirmed / uncertain ±500）。支持自动补全搜索，单击查看详情，双击填入输入框。
- **全高校爆款监测** — 选择快照区间后同时扫描账号列表中的全部高校，按播放增长、视频增长、单条新增视频效率和稳健异常信号排名；“筛选门槛”提供通俗原理说明和固定倍数单位，缺失快照区间不参与判定，并可双击下钻单校明细。
- **频率控制** — 可配置爬取频率限制，避免频繁请求服务器。
- **易用设置** — 采集参数使用大号减/加按钮、纯数字输入区与固定单位，减少误输并便于连续调整。

## 运行环境

- Windows 10/11 64 位
- macOS 代码层已兼容，正式安装包仍待在真实 Mac 上验证
- 使用预编译 EXE 则无需安装 Python

## 快速开始

### 方式一：下载 EXE 直接运行

1. 从 [Releases](../../releases) 页面下载 `YSP-Analyzer.zip`
2. 解压后双击 `YSP-Analyzer.exe`

### 方式二：从源码运行

```bash
# 克隆仓库
git clone https://github.com/zerosignal666/yangshipin-similar-account-analyzer.git
cd yangshipin-similar-account-analyzer

# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

## 项目结构

```
ysp-analyzer/
├── main.py                  # 程序入口
├── requirements.txt         # Python 依赖
├── 同类账号.txt              # 账号列表（校名 [TAB] URL）
├── src/
│   ├── crawler/             # 爬虫模块
│   │   ├── engine.py        # 爬取编排（线程池 + 频率限制）
│   │   ├── fetcher.py       # HTTP 客户端（httpx）
│   │   ├── parser.py        # HTML/JSON 解析（提取 __STATE_USER__）
│   │   └── url_parser.py    # 账号文件解析 + CPID 提取
│   ├── models/
│   │   ├── schema.py        # 数据库表定义 + 单位归一化
│   │   └── database.py      # SQLite 增删改查
│   ├── analysis/
│   │   ├── charts.py        # Matplotlib 图表生成 + 中文字体
│   │   ├── stats.py         # 统计分析 + 变化量区间
│   │   └── burst.py         # 学校爆款区间与稳健阈值
│   └── ui/
│       ├── main_window.py   # PySide6 主界面（六个侧栏工作区）
│       ├── burst_page.py    # 全高校爆款监测、排名与筛选
│       ├── theme.py         # 浅色/深色主题与跨平台字体
│       ├── widgets.py       # 通用卡片、标题与指标组件
│       ├── chart_windows.py # QtAgg 通用交互图表
│       ├── burst_window.py  # 单校爆款证据详情窗口
│       └── workers.py       # QThread 后台爬取线程
└── data/                    # SQLite 数据库（自动生成，已 gitignore）
```

## 自定义账号列表

编辑 `同类账号.txt` 添加或删除账号，格式：

```
学校名称[TAB键]https://www.yspapp.cn/...
```

每行一个账号，保存后重新打开程序即可生效。

## 技术栈

| 层级 | 使用库 |
|---|---|
| 界面 | PySide6（Qt 6） |
| 图表 | Matplotlib（QtAgg 后端） |
| 数据 | Pandas + NumPy |
| 网络 | httpx |
| 解析 | BeautifulSoup4 + lxml |
| 数据库 | SQLite |
| 打包 | PyInstaller |

## 数据来源

由于央视频主营移动端，网页端无法搜索央视频账号，项目中所有账号首页的数据获取来源于央视频app，通过手动搜索关键词“大学/学院/学校”关键词找到对应的央视频号，通过“分享”功能获取链接。


所有数据来自 [yspapp.cn](https://www.yspapp.cn) 公开的个人主页。程序解析页面 HTML 源码中的 `window.__STATE_USER__` JSON 数据。无需登录，无需 API Key。


目前还是才疏学浅了！希望后面可以开发出更加自动化的方法。

## 界面中英对照

| 英文（界面） | 中文 |
|---|---|
| Collect | 采集中心 |
| Snapshots | 数据快照 |
| Analyze | 单次分析 |
| Compare | 对比分析 |
| Pulse Watch | 爆款监测 |
| Settings | 采集设置 |
| Start | 开始采集 |
| Pause / Resume | 暂停 / 继续 |
| Stop | 停止 |
| Export CSV | 导出 CSV |
| Dashboard | 综合仪表盘 |
| Snapshot Manager | 管理快照 |
| School Detail | 学校详情 |
| Search School | 搜索学校（自动补全） |
| confirmed / uncertain | 确认增长 / 不确定（舍入误差内） |

完整对照请参见 `使用说明.txt`。

## 开源协议

MIT License — 详见 [LICENSE](LICENSE) 文件。
