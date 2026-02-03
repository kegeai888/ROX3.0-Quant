# ROX 3.0 仙宫云 (Xiangong Cloud) 部署指南

本指南将帮助您在仙宫云 GPU 实例上部署 ROX 3.0 量化系统。

## 1. 创建实例

1.  登录 [仙宫云控制台](https://www.xiangongyun.com/)。
2.  点击 **"部署新实例"**。
3.  **GPU 选择**: ROX 3.0 的基础功能对显卡要求不高，但如果使用 AI 策略 (Kronos/Qbot)，建议选择 **RTX 3090 / 4090** 或更具性价比的显卡。
4.  **镜像选择**:
    *   推荐选择 **公共镜像** -> **PyTorch** (选择 Python 3.9 或 3.10 的版本)。
    *   或者选择 **Ubuntu 20.04/22.04** 基础镜像。
5.  点击 **"立即部署"**。

## 2. 上传代码

实例启动后，有两种方式上传代码：

### 方法 A: 使用 Git (推荐，方便更新)
1.  在控制台点击 **"JupyterLab"** 或 **"WebSSH"** 打开终端。
2.  启用学术加速 (提高 Github 速度):
    ```bash
    . /accelerate/start
    ```
3.  克隆您的代码库 (假设您的代码在 Github/Gitee):
    ```bash
    git clone https://github.com/your-repo/rox3.0.git
    cd rox3.0
    ```

### 方法 B: 手动上传 (如果不使用 Git)
1.  在控制台点击 **"文件管理"** 或 **"JupyterLab"**。
2.  将本地的 `rox3.0` 文件夹打包成 `.zip`。
3.  上传并解压:
    ```bash
    unzip rox3.0.zip
    cd rox3.0
    ```

## 3. 环境安装

在终端中执行以下命令初始化环境：

```bash
# 1. 更新 apt 源并安装 Redis (系统级依赖)
apt-get update
apt-get install -y redis-server

# 2. 安装 Python 依赖
pip install -r requirements.txt
```

## 4. 启动服务

我们提供了一个启动脚本 `start_xiangong.sh` 来简化操作。

```bash
# 赋予执行权限
chmod +x start_xiangong.sh

# 启动服务 (首次运行建议加 --install 确保依赖安装)
./start_xiangong.sh --install
```

启动成功后，您可以使用 `tail -f rox_server.log` 查看实时日志。

## 5. 访问系统 (端口映射)

ROX 3.0 默认运行在 `8081` 端口。

1.  回到仙宫云控制台的 **"实例管理"** 页面。
2.  找到 **"自定义端口"** 或 **"端口映射"** 功能。
3.  将容器端口 `8081` 添加映射。
4.  系统会生成一个公网访问链接 (例如 `http://region-a.xiangongyun.com:12345`)。
5.  在浏览器中访问该链接即可打开 ROX 3.0 界面。

---

## 常见问题 Q&A

### Q: 后续更新需要重新上传吗？
**不需要重新上传整个项目。**

*   **如果您使用 Git (推荐)**:
    只需在终端进入项目目录，执行：
    ```bash
    git pull
    # 如果有新依赖
    pip install -r requirements.txt
    # 重启服务
    pkill -f uvicorn
    ./start_xiangong.sh
    ```

*   **如果您手动上传**:
    只需将**修改过的文件**上传并覆盖对应文件即可。不需要删除原来的文件夹。覆盖后记得重启服务：
    ```bash
    pkill -f uvicorn
    ./start_xiangong.sh
    ```

### Q: 关闭网页后服务会停止吗？
如果您直接在 Jupyter 终端运行 `python main.py`，关闭网页可能会停止。
但使用我们的 `./start_xiangong.sh` 脚本，它使用了 `nohup` 后台运行，**即使关闭网页或断开 SSH，服务也会继续运行**。

### Q: 实例释放后数据还在吗？
*   如果您点击了 **"释放实例"**，数据会被清除！
*   如果想保留数据以便下次使用，请在释放前制作 **"私有镜像"**，或者将代码和数据存放在挂载的 **"网盘"** (如果有) 中。建议定期备份 `data/` 目录和 `docs.db` 数据库文件。
