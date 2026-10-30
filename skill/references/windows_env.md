# 本机 Windows 环境踩坑清单

## Python 调用方式

用绝对路径，不要依赖 `python` 在 PATH 里：

```
C:\Users\14568\.workbuddy\binaries\python\versions\3.13.12\python.exe
```

**路径写法**：在 Git Bash 里把路径传给 python.exe 时，必须用 `C:/...` 盘符写法。
用 MSYS 风格的 `/c/...` 会被错误转换成 `c:\c\...` 导致找不到文件。

```bash
# 错：python.exe: can't open file 'c:\c\Users\...'
PY="/c/Users/14568/.workbuddy/binaries/python/versions/3.13.12/python.exe"   # 作为 argv[0] 可以
"$PY" "/c/Users/.../script.py"                                              # 作为参数会错

# 对
PY="C:/Users/14568/.workbuddy/binaries/python/versions/3.13.12/python.exe"
"$PY" "C:/Users/.../script.py"
```

## 装包

默认 pip 源（清华镜像）在这台机器上取不到包，**必须加官方源**：

```
python.exe -m pip install -i https://pypi.org/simple --no-warn-script-location pandas numpy pyreadstat matplotlib openpyxl scipy python-docx
```

装大包（pandas、scipy、python-docx）耗时 1~4 分钟，用后台任务跑，别在前台等超时。

## 虚拟环境

`python -m venv <路径>` 在本机**静默失败**：退出码 0，但目录根本不生成。
不要在这上面耗时间，直接装进托管 Python。

## 中文编码三件套

1. Python 脚本开头（否则 print 中文在 Windows 控制台报 UnicodeEncodeError）：
   ```python
   try:
       sys.stdout.reconfigure(encoding="utf-8")
   except Exception:
       pass
   ```
2. 导出 CSV 用 `encoding="utf-8-sig"`，否则 Excel 打开是乱码。
3. `.bat` 脚本内容**必须纯 ASCII**，中文注释会出现乱码导致脚本执行异常。
   如果要中文提示，写在 Python 脚本里，.bat 只负责调用。

## matplotlib 中文

```python
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "KaiTi"]
plt.rcParams["axes.unicode_minus"] = False   # 否则负号显示为方块
```
后端用 `matplotlib.use("Agg")`，无图形界面环境下也能存图。

## 网络

外网直连部分不通：`github.com` 走本地代理 `127.0.0.1:60413` 返回 502，
但 `api.github.com` 可达（200），npm registry 可达。
需要访问 GitHub 时优先考虑 API 通道。

## 验证 Word 输出的手段

本机没装 Word / LibreOffice / WPS，无法渲染截图。
验证 .docx 是否正确，直接读压缩包里的 XML：

```python
import zipfile
from xml.etree import ElementTree as ET
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
root = ET.fromstring(zipfile.ZipFile('x.docx').read('word/document.xml'))
```
可检查：字体 `w:rFonts/@w:eastAsia`、字号 `w:sz/@w:val`（单位半磅）、
边框 `w:tblBorders` 与 `w:tcBorders`。
