[English](README_EN.md) | 中文

# 央视频同类账号分析器

一个爬取央视频（yspapp.cn）平台高校账号公开数据的桌面应用，内置数据可视化与快照对比功能。

## 功能

- **批量爬取** — 一键爬取 100+ 高校账号的粉丝数、播放量、视频数。支持开始/暂停/继续/停止，实时显示进度。
- **数据表格** — 可排序、可搜索的数据表，支持单位切换（个/万/亿）。武汉科技大学默认红色加粗高亮，也可自定义高亮任意学校。
- **交互图表** — 柱状图、直方图、散点图，鼠标悬停显示数值，滚轮缩放，点击标注。
- **仪表盘** — 多图表网格布局，随窗口大小自适应列数。
- **快照系统** — 每次爬取保存时间戳快照，可任选两次快照对比增长变化。
- **频率控制** — 可配置爬取频率限制，避免频繁请求服务器。

## 截图

*待补充*

## 运行环境

- Windows 10/11 64 位（macOS 计划支持）
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
│   │   ├── charts.py        # Matplotlib + seaborn 图表
│   │   └── stats.py         # Pandas 统计分析
│   └── ui/
│       ├── main_window.py   # Tkinter 主界面（爬取/数据/分析三页签）
│       ├── chart_windows.py # 交互式图表弹窗（缩放/悬停/点击）
│       └── workers.py       # 后台爬取线程
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
| 界面 | Tkinter（Python 内置） |
| 图表 | Matplotlib + Seaborn（TkAgg 后端） |
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
| Crawl | 爬取数据 |
| Data Table | 数据表格 |
| Analysis | 数据分析 |
| Start Crawl | 开始爬取 |
| Pause / Resume | 暂停 / 继续 |
| Stop | 停止 |
| Reset Limit | 重置限制 |
| Export CSV | 导出CSV |
| Analyze | 分析 |
| View | 查看 |
| Open Dashboard | 综合仪表盘 |
| Settings | 设置 |
| Snapshot Manager | 快照管理 |
| Single Snapshot | 单个快照分析 |
| Compare Snapshots | 快照对比 |

完整对照请参见 `使用说明.txt`。

## 开源协议

MIT License — 详见 [LICENSE](LICENSE) 文件。
