## 联想小新Pad Pro GT 13 Linux方案
### 适配情况
| 子系统 | 状态 | 说明 |
|---|---|---|
| 启动 / 双系统 | ✅ | 共享分区，a/b槽启动，使用fastboot切换槽位 |
| WiFi | ✅ | 千兆网络下测速 |
| UFS | ✅ | - |
| 显示 / 面板 | ✅ | 60/90/120/144Hz刷新率正常，背光可调节 |
| 音频（四扬声器+双麦克风） | ✅ | 扬声器可独立发声 |
| 触控 | ✅ | 触摸、手写笔正常 |
| 摄像头（前摄+后摄） | ✅ | 使用软件isp。部分软件需要libcamerify配合，未适配所有软件 |
| 视频硬件加速 | ✅ | VA-API与V4L2-M2M两种模型，浏览器可硬件解码 |
| 蓝牙 | ✅ | - |
| 电源 / 电池 | ✅ | 测试充电峰值40W |
| 磁吸皮套 | ✅ | 由sensord提供服务 |
| USB | ✅ | 10Gbps测试通过，可在host/device下工作，DP输出已测试2k@165Hz |
| 挂起 / 恢复 | ⚠️ | s2idle正常；deep下偶发自动唤醒 |
| GPU | ⚠️ | 偶发GPU hang,等上游修复 |
| RTC | ⚠️ | 可读写和定时唤醒，但冷启动后日期有偏移 |
| 传感器 | ⚠️ | 用户态实现，未接入IIO子系统。sensord向D-Bus提供环境光和屏幕方向、旋转声道 |
| 手写笔 | ⚠️ | 手写笔可实现基础功能（定位、压感、倾斜、电量）（适配AP501U），二代笔未测试。仅60/120Hz刷新率下可使用 |
| 手电筒 | ⚠️ | 可手动写sysfs打开，未测试用户层软件 |
| 磁吸键盘 | ❌ | 未适配，无法测试 |
| 杜比音效 | ❌ | 无法适配 |
### 食用方法
1. 请先解锁Bootloader  
2. 底包基于ZUXOS 2.0.10.252，请自行提取底包或首先刷入该ROM（或基于该底包的ROM），并同步AB槽
   * 可以使用bootloader刷入的：bluetooth, boot, cpucp, cpucp_dtb, dsp, dtbo, featenabler, init_boot, modem, multiimgqti, pdp, pvmfw, qweslicstore, recovery, shrm, soccp_dcd, soccp_debug, spuservice, uefi, vbmeta, vbmeta_system, vendor_boot
   * 只能使用root或者EDL刷入的：abl, aop, aop_config, devcfg, hyp, imagefv, keymaster, multiimgoem, qupfw, pdp_cdb, tz, uefisecapp, xbl, xbl_config
   * 由于线刷包只会写入A槽，请务必确保这些分区有实际内容，否则将会在切槽后陷入EDL模式！
3. 前往 [Releases](https://github.com/PickaxeHit/linux-zhiyu-next/releases) 下载最新分区镜像

   公共部分：
   * [vendor_boot.img](https://github.com/PickaxeHit/linux-zhiyu-next/releases/download/zhiyu-images/vendor_boot.img)
   * [init_boot.img](https://github.com/PickaxeHit/linux-zhiyu-next/releases/download/zhiyu-images/init_boot.img)

   发行版相关：
   * 不指定主 LSM（默认，如 ArchLinux）：[boot.img](https://github.com/PickaxeHit/linux-zhiyu-next/releases/download/zhiyu-images/boot.img) + [vbmeta.img](https://github.com/PickaxeHit/linux-zhiyu-next/releases/download/zhiyu-images/vbmeta.img)
   * 启用 SELinux，RedHat 系（如 Fedora）：[boot-selinux.img](https://github.com/PickaxeHit/linux-zhiyu-next/releases/download/zhiyu-images/boot-selinux.img) + [vbmeta-selinux.img](https://github.com/PickaxeHit/linux-zhiyu-next/releases/download/zhiyu-images/vbmeta-selinux.img)
   * 启用 AppArmor，Debian 系（如 Ubuntu）：[boot-apparmor.img](https://github.com/PickaxeHit/linux-zhiyu-next/releases/download/zhiyu-images/boot-apparmor.img) + [vbmeta-apparmor.img](https://github.com/PickaxeHit/linux-zhiyu-next/releases/download/zhiyu-images/vbmeta-apparmor.img)
4. 前往[rootfs仓库](https://github.com/PickaxeHit/linux-zhiyu-rootfs-builder)，[fork](https://github.com/PickaxeHit/linux-zhiyu-rootfs-builder/fork)该仓库到自己账号下，并启用Action  
5. 在自己的rootfs仓库下，根据自己的偏好与设置，在Action中触发一次构建  
6. 下载构建好的rootfs，并解压到设备中，内容物为.tar.xz后缀。请自行核对hash  
7. 使用具有root权限的终端，在/data/下创建linux子目录。完整路径为/data/linux/  
8. 将rootfs以root身份解压至/data/linux下，并检查/data/linux/sbin/init是否存在（有可能多一级或少一级，此时需要删除整个linux目录并从第7步开始）。
   * 非SELinux: `tar -xJvf /path/to/rootfs.tar.xz -C /data/linux`
   * 启用SELinux: `tar -xJvf /path/to/rootfs.tar.xz -C /data/linux --numeric-owner --same-owner --same-permissions --xattrs --xattrs-include='security.*'`
9. 刷入第3步下载的四个镜像至未使用的槽位（可使用`adb shell getprop ro.boot.slot_suffix`检查当前槽位）  
10. 重启至该槽位
### 注意事项
1. 请先自行备份所有关键分区并确保自己有救砖条件，在刷入和执行前先自行检查镜像内容
2. 共享分区方案为实验性可能会导致分区出错，不保证android端不出现数据损坏、无法开机等现象。可自行评估风险与可用性
3. linux端具有root权限，具有读写任意分区（以及RPMB区块）的能力，谨防恶意软件与误操作
4. 系统内安装有`qbootctl`，仅用于标记启动成功。在[PR#7](https://github.com/linux-msm/qbootctl/pull/7)或相关PR合并并同步至发行版前，请勿使用`qbootctl -s`切换槽位
5. 若使用过程中出现严重问题请及时反馈
### 参考项目
https://github.com/yzddmr6/xiaomipad-8pro-mainline

https://github.com/KunBuFenZi/progt13-ubuntu

### 构建与开发
见 `./build.sh help` 查看构建目标。`./build.sh all` 构建公共镜像及三发行版软件包；使用 Docker 或 Podman。`python3 scripts/deps.py lock --missing` 锁定依赖。

### Nix / NixOS

Flake 使用原生 `aarch64-linux` 构建。在 x86_64 Linux 上可求值，或通过
[Nix remote builder](https://nix.dev/manual/nix/latest/advanced-topics/distributed-builds.html)
把构建交给 ARM64 主机。求值无需初始化子模块。测试期间使用 `github:PickaxeHit/linux-zhiyu-nix/nix-full`，
正式合并后使用 `github:PickaxeHit/linux-zhiyu-next`。可用 Git tag 或完整提交固定 BSP 版本。

```bash
nix flake show github:PickaxeHit/linux-zhiyu-nix/nix-full --all-systems
nix build github:PickaxeHit/linux-zhiyu-nix/nix-full#kernel
nix build 'github:PickaxeHit/linux-zhiyu-nix/nix-full#kernel^dev,modules'
nix build github:PickaxeHit/linux-zhiyu-nix/nix-full#initramfs
nix build github:PickaxeHit/linux-zhiyu-nix/nix-full#zhiyu-images
```

`zhiyu-images` 包含四个分区镜像、大小和 SHA-256 清单。可单独构建
`zhiyu-boot`、`zhiyu-vendor-boot`、`zhiyu-init-boot` 和 `zhiyu-vbmeta`。
启动镜像使用仓库公开的 AVB 测试密钥，需要解锁的 Bootloader。
生产签名密钥应在 Nix 之外的签名环节使用。Nix 镜像流水线使用 `flake.lock`
固定的 nixpkgs `android-tools`，传统构建继续用 `deps.json` 固定的
Android 15 工具。BusyBox、F2FS 和 KeyMint 的静态依赖由两个后端共用的
源码提交固定。

内核通过 `linuxManualConfig` 读取共享 Kconfig，输出内核、模块和外部模块
所需的开发树。Nix 构建显式设置空的 `LOCALVERSION`，仅使用 Kconfig 中
的 `-zhiyu` 后缀。DTB 只依赖内核源码中的绑定头文件和主仓 DTS。
早期启动程序以 musl 静态链接，ramdisk 由传统构建也使用的脚本组装。
固件、AudioReach topology、SNS 配置、UCM2 和用户态硬件支持都有独立输出。

#### NixOS 硬件模块

[NixOS Rootfs Builder](https://github.com/PickaxeHit/linux-zhiyu-rootfs-builder-test)
负责系统配置、rootfs 和同一 generation 的四个启动镜像。自建系统也可导入
BSP Flake 的 `nixosModules.default`，设置 `zhiyu.enable = true`，并统一两边的
nixpkgs input。模块将匹配镜像导出为 `system.build.zhiyuImages`。

首次安装后，同一套启动镜像由 Bootloader 从为 Linux 预留的槽位加载。
在已经运行的 Zhiyu NixOS 上，可以用原生工具检查或安装显式指定的 generation：

```bash
sudo zhiyu-install --dry-run --expect-slot b /nix/var/nix/profiles/system
```

将 `b` 替换为当前 Linux 槽位，验证完成后去掉 `--dry-run` 执行写入。
`zhiyu.flashOnSwitch` 默认关闭。启用它后，`nixos-rebuild boot` 和
`nixos-rebuild switch` 会通过 external bootloader 调用同一个工具。

`boot.kernelParams` 进入 boot.img，`zhiyu.bootconfig` 进入 vendor_boot.img。
早期启动同时核对内核及模块的构建标识，以及 DTB、ramdisk、bootconfig 的
构建标识。它优先选择兼容的当前 profile，随后检查已安装、待安装和历史
generation。两条标识都匹配才进入 NixOS stage 2。每个 generation 保留自己的
镜像，回滚时可以用同一工具恢复旧镜像。纯用户态更新会跳过内容一致的分区。
工具只写当前 Linux slot，检查整套镜像和板载 UFS 分区后开始写入，最后写
vbmeta 并逐项读回校验。如果写入中断，四分区更新仍可能处于混合状态，
应重新完成安装或通过 fastboot 恢复再重启。

#### 更新源码锁

```bash
# 更新 Git 依赖时先编辑 deps/deps.json 的 tag，再解析该依赖
python3 scripts/deps.py lock firmware
# 移动子模块后先 git add 相应子模块目录
python3 scripts/gen-nix-sources.py
python3 scripts/gen-nix-sources.py --check
# 可选，重新计算并核对下载内容及生成的版本
python3 scripts/gen-nix-sources.py --check --verify-hashes
# 单独更新工具链时
nix flake update nixpkgs
```

Git 依赖提交以 `deps/deps.json` 为准，内核与 libcamera 提交以主仓
Git index 中的 gitlink 为准，Cargo crate 固定在 `keymint/idlc.Cargo.lock`。
`deps/nix-sources.json` 由工具生成，保存固定输出 fetcher 用的哈希和从源码
提取的版本。传统后端专用条目可设置 `"nix": false`，这类条目由传统后端的依赖锁校验覆盖。
GitHub 归档使用解包目录的递归哈希，Git fetcher 使用
导出目录的 NAR 哈希。普通 tarball 的归档字节哈希仍由 `deps.json` 声明。
锁检查不联网，ARM64 构建会校验实际固定输出。

#### CI 和二进制缓存

`Nix BSP` workflow 单独验证版本锁、Flake、外部模块、启动工具和四个镜像，
并通过模块求值检查 NixOS 使用的 kernel、firmware 和 initramfs 与独立包一致。

缓存包含 kernel、modules、外部模块用的开发树、DTB、initramfs、固件、
设备用户态及可独立重用的早期工具。发布使用这些输出的运行时闭包，跳过
cache.nixos.org 已提供的路径。Android 镜像在 CI 中验证，用户按自己的
cmdline 和 LSM 在本地生成。内核源码归档、编译器、Cargo vendor 树和
临时构建目录仅在需要编译时获取。同一组输出也能通过标准 `nix copy` 发布
到 S3 兼容的 Nix 缓存。

Debian、Arch Linux ARM、Fedora 和 Nix 的软件包统一发布到
[`linux-zhiyu-pkgs`](https://github.com/PickaxeHit/linux-zhiyu-pkgs)，各自的
客户端地址见该仓库 README。独立启动镜像继续由 BSP 提供。

发布 workflow 需要源码仓的 Actions secret `PACKAGE_PUBLISH_TOKEN`，
使用一个只对包仓拥有 Contents read/write 的 fine-grained PAT。
构建产物仍使用当前源码仓的 Actions token 拉取。

维护者可运行下列命令生成自己的缓存密钥。将私钥写入 Actions secret
`NIX_CACHE_SIGNING_KEY`，将公开密钥写入 Actions variable
`NIX_CACHE_PUBLIC_KEY` 并分发给使用者。私钥文件应置于仓库和 Nix store
之外。

```bash
umask 077
nix key generate-secret --key-name linux-zhiyu-next-1 > /secure/path/zhiyu-cache.key
nix key convert-secret-to-public < /secure/path/zhiyu-cache.key
```

在默认分支手动运行 workflow 并选中 `publish_cache`。发布步骤先上传并
验证独立包仓库 Release 中的 NAR，再增量更新 `nix-cache-index` Release。
发布失败时，可填原任务的 `cache_from_run` 重试仍有效的 artifact。
缺少 secret 时构建和校验仍可运行。消费者配置如下，其中公开密钥使用
维护者提供的实际值。

```nix
{
  nix.settings = {
    extra-substituters = [ "https://github.com/PickaxeHit/linux-zhiyu-pkgs/releases/download/nix-cache-index/" ];
    extra-trusted-public-keys = [ "<维护者提供的公开密钥>" ];
  };
}
```

BSP 消费者在自己的 `flake.lock` 里固定通过验证的提交。二进制缓存索引累积保留已经发布的 store path。
