# IPTV_stream_checker
一个简单的IPTV直播源检测工具及可用直播源列表（不稳定更新）


## 运行程序
双击 `run_checker.bat` 文件即可启动程序。
程序会自动：
- 检查Python环境
- 创建虚拟环境（如果不存在）
- 安装必要依赖（requests库）
- 启动中文GUI界面

## 支持格式
### M3U格式
```
#EXTM3U
#EXTINF:-1 group-title="央视频道",CCTV1
http://example.com/cctv1.m3u8
#EXTINF:-1 group-title="卫视频道",湖南卫视
http://example.com/hunantv.m3u8
```
### 简单URL列表（txt格式居多）
```
http://example.com/cctv1.m3u8
http://example.com/hunantv.m3u8
```

## 导出格式
### 有效频道
- `有效频道_时间戳.csv` - CSV格式的有效频道列表
- `有效频道_时间戳.m3u` - M3U格式的有效频道列表
### 无效频道
- `无效频道_时间戳.csv` - CSV格式的无效频道列表（包含错误信息）
### 检测报告
- `检测报告_时间戳.json` - 完整的检测报告（JSON格式）

## 常见问题

**Q: 提示"未找到Python"**
A: 请从 https://www.python.org/downloads/ 下载并安装Python 3.6+

**Q: 程序无法启动**
A: 确保Python安装时勾选了"Add Python to PATH"选项

**Q: 检测速度慢**
A: 可以适当增加并发数，但不要超过50，避免对目标服务器造成压力

**Q: 某些频道检测不准确**
A: 尝试更换检测方法，或启用重试机制
