# 脚本目录

从 [脚本索引](../docs/SCRIPT_INDEX.md) 找到阶段入口，再查看 [资产重建](../docs/REBUILDING.md) 和 [研究任务](../docs/RESEARCH.md)。日常开发、发布资产下载和构建入口在 [package.json](../package.json)。

- `landmarks/` 保存单对象建模模块和研究辅助工具。先核对对象 ID、城市、规格、来源和高度基准。
- `city_mesh.py` 提供共享网格与材质接口，导入会初始化并清空 Blender 场景。在独立的后台进程调用导出器。
- 杭州候选以 `artifacts/` 的新目录为输出。按对象分工，共享的地形、楼体排除、分块、清单、网页加载由一个集成人员串行更新。
- 历史脚本可能依赖固定的 v15、旧深圳 `public/city/`、本机 Blender 路径或未入 Git 的处理文件。查看参数、输入路径、输出目录及写入行为后再运行。
