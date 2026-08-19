# 脸幻（FaceFusion 非官方中文）

基于开源 [FaceFusion](https://github.com/facefusion/facefusion) 的中文界面版本，**非官方发行**。许可证：OpenRAIL-AS。

界面在你自己电脑上打开，不是云端。请只处理你有权使用的照片和视频。

## 使用方法（Windows）

环境只需装一次：

1. 安装 Miniconda、FFmpeg
2. 打开终端执行：

```
conda create --name facefusion python=3.12
conda activate facefusion
python install.py directml
```

仅 CPU 时把最后一行改成 `python install.py default`。

3. 双击 `启动换脸.bat`，或执行：

```
conda activate facefusion
python facefusion.py run --open-browser
```

浏览器打开后：

1. 「脸」里放要贴上去的人脸照片  
2. 「原图/视频」里放被换的图或视频  
3. 点「开始」  

默认已勾选换脸和增强。第一次可能联网下载模型（优先 GitHub）。

英文界面：`python facefusion.py run --open-browser --language en`

更多命令见 `python facefusion.py -h`。原项目文档：https://docs.facefusion.io
