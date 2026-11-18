# Fleasion

[English](README.md) | **简体中文**

Fleasion 可以在 Windows、macOS 和 Linux（Sober）上实时替换 Roblox 游戏资产。它在 Roblox 与服务器之间运行本地代理，让贴图、音频、网格、动画等资产在进入游戏客户端前被替换、移除或缓存。

> [!IMPORTANT]
> 这是 Fleasion 的一个小型兼容性 fork。它在当前 `main` 代码基础上，为较新的 Windows Roblox Player 加入 live TLS splice 与 HTTP/2 支持。实机验证目前集中在 **Phantom Forces**；其他游戏没有系统性测试过。

> [!CAUTION]
> 这个 fork 的兼容构建发布在它自己的 [Releases](https://github.com/n8sPxD/Fleasion/releases) 页面。官方 Fleasion 项目、官网和社区仍在 [fleasion/Fleasion](https://github.com/fleasion/Fleasion) 与 [fleasion.github.io](https://fleasion.github.io/)。

Fleasion 原作者拥有本应用以及活跃开发中的 `feat/rewrite-ui-v2` 重构工作的功劳。这个 fork 的范围刻意更小：只在较旧的 `main` 代码线上移植少量兼容性改动，供一个小范围用户群使用；它不会替代或掩盖上游正在进行的重写工作。

## 安装

从本 fork 的 [Releases](https://github.com/n8sPxD/Fleasion/releases) 页面下载最新兼容构建。运行打包版不需要安装 Python。

如需从源码运行、构建或参与开发，请查看 [CONTRIBUTING.md](CONTRIBUTING.md)。

<details>
<summary><b>安装问题排查</b></summary>

- **Windows 出现 `DLL load failed`：** 把 `.exe` 移到其他文件夹，例如 Documents。Windows 可能加载 exe 所在目录里的不兼容 DLL。也可以清理 `%temp%`，删除残留的 `_MEI` 文件夹。
- **Linux GUI 无法启动：** 安装系统发行版提供的 PortAudio。
- **Arch 系发行版**还需要 Qt6 原生 widgets 包：

  ```bash
  sudo pacman -S --needed qt6-base
  ```

</details>

## 使用方法

1. 启动 Fleasion。
2. 在 Replacer 页面添加替换规则。
3. 修改规则后清除 Roblox 缓存，让 Roblox 重新通过代理下载资产。
4. 启动 Roblox，流量会经过 Fleasion。

> [!NOTE]
> 修改 Dashboard 中的任何配置后，都需要清除 Roblox 缓存或重启 Roblox。Fleasion 可以自动处理：
>
> - **Clear Cache on Launch** 会在代理启动时关闭 Roblox 并删除 `rbx-storage.db`。
> - **Auto Delete Cache on Exit** 会在 Roblox 关闭后删除缓存数据库。
> - 也可以从托盘菜单手动清除缓存。

<details>
<summary><b>系统托盘</b></summary>

Fleasion 会在系统托盘中后台运行。左键图标可以显示或隐藏窗口，右键图标可以打开：

- **Dashboard：** 配置资产替换。
- **Delete Cache：** 手动清除缓存资产。
- **Logs：** 查看实时代理日志。
- **About：** 应用信息。
- **Settings：** 主题、缓存、开机启动等设置。

</details>

<details>
<summary><b>开机启动</b></summary>

打开 **Settings > Run on Boot** 可以自动启动 Fleasion：

- **Windows** 创建普通用户权限的任务计划程序任务。
- **macOS** 创建用户级 LaunchAgent。
- **Linux** 创建用户级 XDG 自启动项。

Env Proxy 的开机启动不需要管理员权限。Hosts File 模式启动后仍可能请求平台 helper 或管理员权限。**Settings > Create desktop/start menu integration on boot** 会在每个平台刷新启动器入口。

</details>

## 工作原理

Fleasion 在本机运行轻量 HTTPS 代理，并支持两种路由模式。Roblox 请求资产时，Fleasion 可以：

- 按 ID 替换资产，例如将一张贴图、音频或模型换成另一个资产。
- 移除资产，例如从请求中剥离贴图。
- 将资产重定向到自定义 CDN URL 或本地文件。
- 缓存原始资产，便于浏览、预览和导出。

所有处理都发生在你的本机。

<details>
<summary><b>代理模式</b></summary>

- **Roblox Env Proxy** 是默认模式，监听 loopback 端口 `58443`，并通过代理环境变量重新启动 Roblox Player。如果 Windows 已占用该端口，Fleasion 会自动选择其他 loopback 空闲端口。此模式不修改 hosts 文件，也不占用 443 端口。Roblox Player 的 `ssl/cacert.pem` 仍会加入 Fleasion 本地 CA，使客户端信任拦截流量。
  - Microsoft Store 与 Xbox（GDK）版 Roblox 会通过包感知激活并注入受限环境。如果系统不支持该方式，Fleasion 不会强行重启客户端，而是报告错误。
  - 此模式永远不会重启、拦截、修补或关闭 Roblox Studio。
- **Hosts File** 是较旧的兼容模式。它将受拦截的 Roblox 域名指向 localhost 并监听 443 端口，因此需要管理员权限或平台 helper。

Env Proxy 在所有平台都以普通用户运行。只有修复受保护的 Roblox 安装或旧的开机启动任务时，才可能偶尔请求管理员权限。

</details>

<details>
<summary><b>证书与 FastFlags</b></summary>

Windows 使用 live TLS splice 传输：Roblox 保留原始证书链，Fleasion 只恢复本进程的 TLS 会话密钥；ClientSettings 保持端到端隧道，以保留响应签名。其他平台会设置 `DFFlagHttpUseEmbeddedCaCerts=False`，让 Roblox 信任修补后的 `ssl/cacert.pem`，并通过 ClientSettings 响应下发该覆盖和刷新间隔。

Sober 的固定 bootstrap 请求保持隧道，Linux 拦截会等待 Sober 现有 bootstrap 延迟结束后再启动。这些内部覆盖不会出现在已保存的 FastFlag 列表中，证书验证也保持开启。

开启自定义 FastFlags 时，Windows 会预填启动 flag 缓存；其他平台也会把覆盖合并进 ClientSettings 响应。这样 Roblox 启动早期读取的 flag 可以立即生效。在 Roblox 校验签名响应期间，Windows 动态 ClientSettings 覆盖保持禁用。

</details>

<details>
<summary><b>Linux 客户端</b></summary>

Fleasion 支持 Sober Flatpak（`org.vinegarhq.Sober`）。它使用 Sober 的资产覆盖目录 `~/.var/app/org.vinegarhq.Sober/data/sober/asset_overlay`，并将 Sober FastFlags 写入 `~/.var/app/org.vinegarhq.Sober/config/sober/config.json`。

客户端路径、启动行为、进程检测和代理支持都经过客户端注册表处理，方便之后添加其他 Linux 客户端。当前唯一支持的是 Sober。

</details>

<details>
<summary><b>macOS 说明</b></summary>

- Fleasion 支持标准 Roblox、Froststrap 管理的 `RobloxPlayer.app` 版本以及 AppleBlox 自定义路径。它会将托管文件和证书状态复制到 Froststrap 与 AppleBlox 的恢复快照。AppleBlox 会在启动前重建 `Contents/MacOS/ClientSettings`，因此 Fleasion 也会在 Roblox 读取前合并允许的 FastFlags；冲突时以 Fleasion 的值为准。
- Fleasion 会在写入 hosts 前验证 helper 是否修补过 `ssl/cacert.pem`。验证失败时代理不会启动。
- macOS 的 Account Manager 启动会使用 Roblox auth ticket `roblox-player:` 链接。Place、私人服务器、job ID 和普通应用启动都会尝试，但 Roblox 可能拒绝其中一些链接。普通打开 Roblox 时使用已登录账号。
- 首次启动时，Fleasion 会询问哪个浏览器已登录 roblox.com。功能需要 Roblox 登录时会读取该浏览器，macOS 可能请求访问浏览器数据的权限。选择 **Always Allow** 可以避免重复提示。Fleasion 也可以复用有效的加密 Chrome 系缓存。缓存不确定时会保留并跳过重复提示。如需更换浏览器或手动导入登录信息，使用 **Settings > Roblox Login** 或 **Miscellaneous > Account Manager > Import Browser Login**。

</details>

> [!WARNING]
> **VPN：** Env Proxy 只影响 Roblox Player 进程，通常可以与 VPN 共存。Hosts File 模式要求 VPN 尊重本机 hosts 文件。
>
> **Roblox 规则：** 资产替换发生在你的客户端，只有你能看到变化。撰写本文时没有已知检测或封禁报告，但 Roblox 不允许这类修改，游戏管理员仍可能处理。请自行评估风险。

## 功能

<details>
<summary><b>资产替换</b></summary>

- 在 Dashboard 中配置替换规则。
- 按 ID 替换资产，重定向到外部 URL，或服务本地文件。
- 保留多个配置文件并切换。
- 以 JSON 导入和导出配置。
- 通过 PreJsons 使用社区预设。
- 配置列表可显示 **creator name** 列，默认关闭。
- 预览按钮旁可显示 **asset name**。

</details>

<details>
<summary><b>自定义 FastFlags</b></summary>

Fleasion 可以在 Roblox 运行时通过代理覆盖 FastFlags。打开 Dashboard 中 **Modifications** 页的 **Fast Flags** 可以：

- 实时编辑自定义 FastFlags，并通过代理生效。
- 以 JSON 导入和导出 FastFlags。
- 保存命名配置，并按替换或合并方式加载。
- 预填 Windows FastFlag 缓存，让启动早期读取的 flag 在首次刷新前生效。

> [!CAUTION]
> 自定义 FastFlags 会绕过 Roblox 少量本地允许的 flag。**Roblox 可能因此封禁账号。** Fleasion 打开前会要求确认风险。请完全自担风险。

</details>

<details>
<summary><b>缓存抓取器</b></summary>

缓存抓取器会捕获 Roblox 游戏过程中下载的资产。在 Dashboard 开启后，它会在后台运行。

**资产抓取流程**

1. **资产跟踪：** 读取发往 `assetdelivery.roblox.com` 的资产 batch 请求，在下载前记录资产 ID、类型和下载地址。
2. **CDN 捕获：** 读取 Roblox CDN 的实际下载，保存内容、URL、Content-Type、hash、大小和时间戳。

**表格**

- 右键列头可以显示或隐藏列。Creator name 与 Roblox CDN 链接默认隐藏。
- 列可以调整宽度和排序，布局会保存。

**自动转换**

- **KTX 贴图**（图片与 decal）会在本机转换为 PNG。
- **TexturePack** 会通过 XML manifest 解析为 Color、Normal、Metalness 和 Roughness。
- **3D 模型**（mesh 与 SolidModel）支持与 `.obj` 互转。

**性能**

- 转换运行在 4 线程后台池中，代理不会等待网络转换。
- 复用 HTTP session，减少重复 API 调用开销。
- 资产查找使用 hash map，不线性扫描全部记录。

**缓存范围**

Roblox 使用的所有资产类型都会被捕获，包括图片、decal、音频、网格、动画、服装和配件。每个资产都会保存类型、原始 URL、内容 hash、文件大小和捕获时间。

</details>

<details>
<summary><b>3D 查看器与预览</b></summary>

**网格查看器**（OpenGL）

- 轨道相机与第一人称相机。
- 线框与网格显示，网格默认开启。
- 缓存渲染，保证平滑性能。
- 支持顶点色与自动旋转。

**动画查看器**

- 在 R15 与 R6 骨架上实时 3D 播放。
- 自由相机便于观察。
- 播放速度控制。
- 网格显示默认开启。

**转换支持**

- **Mesh 转 CSG：** 先把 `.mesh` 转为 `.obj`，再作为 CSG 注入。
- **CSG 转 mesh：** 替换 mesh 前，先把 CSG 模型转为 `.obj`。
- **CSG 转 CSG：** 通过 CDN 链接直接替换 CSG 模型。
- **CDN OBJ 文件：** 下载并转换来自 Discord、Cloudflare 等链接的 OBJ。

</details>

<details>
<summary><b>缓存查看器</b></summary>

- 按类型浏览所有已捕获资产。
- 按 ID、名称、类型、hash 或 URL 搜索和过滤。
- 预览图片、网格、音频、动画、TexturePack 和 JSON。
- 通过 Roblox API 查询资产名称。
- 以转换后、二进制或原始格式导出资产。
- 直接复制转换后的文件到剪贴板。
- 从列头菜单按分类过滤。

</details>

## 配置

设置保存在：

- Windows：`%LocalAppData%\FleasionNT\`
- macOS：`~/Library/Application Support/FleasionNT/`
- Linux：`~/.config/Fleasion/`

<details>
<summary><b>文件与目录</b></summary>

| 文件或目录 | 用途 |
| --- | --- |
| `settings.json` | 应用设置 |
| `configs/` | 替换配置文件（JSON） |
| `FastFlagProfiles/` | 命名自定义 FastFlag 配置（JSON） |
| `Cache/` | 缓存资产文件与索引 |
| `Exports/` | 导出的资产 |
| `PreJsons/` | 社区预设数据 |
| `proxy_ca/` | 生成的 CA 证书与按主机证书 |
| `logs/fleasion.log` | 应用与代理日志 |
| `Temp/ConvertedMeshes/` | 临时 OBJ 与 mesh 转换 |

</details>

<details>
<summary><b>通过文件共享配置</b></summary>

配置 JSON 直接放在 `configs/` 根目录。如果配置需要附带文件，例如 OBJ 模型，请在 `configs/` 下创建同名资产文件夹：

```text
configs/
├── Replace all weapons with sticks.json
└── StickObj/
    └── stick.obj
```

替换字段中 `/StickObj/stick.obj` 表示“使用 Fleasion configs 目录下 `StickObj` 文件夹中的 `stick.obj`”。该格式在 Windows、macOS 和 Linux 中一致。**Browse** 按钮和拖拽操作会在文件位于 configs 子文件夹时自动使用这种格式。

- 资产文件夹最多嵌套 10 层。
- 配置 JSON 必须位于 `configs/` 根目录。资产文件夹内的 JSON 不会显示为配置。
- 普通文件路径仍可用。macOS 与 Linux 上，如果 `/Folder/file` 同时匹配 configs 资产路径和绝对路径，优先使用 configs 内的文件。

</details>

## 社区

- **Discord：** [discord.gg/hXyhKehEZF](https://discord.gg/hXyhKehEZF)
- **捐赠原作者：** [ko-fi.com/fleasion](https://ko-fi.com/fleasion)

## 许可

本项目按原样提供，仅用于教育与个人使用。
