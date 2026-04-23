# 输出目录改动汇总

## 目标

把 `model selection` 生成的预测结果，从原来的默认分析目录改为项目根目录下的：

```text
output/预测日期/
```

例如：

```text
output/2026-04-22/
```

---

## 我改了什么

### 1. 默认输出目录改为 `output/`

文件：

- `roll/config.yaml`

改动：

- 把 `analysis_folder` 从 `~/.qlibAssistant/analysis/` 改成了 `output/`

作用：

- 按 README 默认命令运行时，不需要额外传参数，结果会直接写到项目里的 `output/`

---

### 2. 保存目录从时间戳目录改成日期目录

文件：

- `roll/modelcli.py`

改动：

- 新增 `_resolve_analysis_dir()`：把相对路径 `output/` 解析为项目根目录下的真实路径
- 新增 `_get_output_dir_name()`：根据预测日期生成子目录名
- 修改 `_save_results()`：
  - 原来输出到 `selection_YYYYMMDD_HH_MM_SS/`
  - 现在输出到 `output/YYYY-MM-DD/`

作用：

- 结果目录更直观，按日期查找更方便
- 多次跑同一天结果时，会落到同一个日期目录

---

### 3. 避免同一天重复跑时 `total.md` 一直追加

文件：

- `roll/modelcli.py`

改动：

- `total.md` 改为覆盖写入，而不是每次追加

作用：

- 同一天重复生成结果时，不会把旧内容重复叠加进去

---

### 4. 兼容复盘逻辑识别新目录名

文件：

- `roll/model_review.py`

改动：

- 让复盘目录扫描逻辑同时支持：
  - 旧格式：`selection_20260423_19_46_52`
  - 新格式：`2026-04-22`

作用：

- 后续 `review` / `backtest` 不会因为输出目录改名而失效

---

### 5. README 补充了新的输出位置说明

文件：

- `README.md`

改动：

- 在本地运行步骤下补充说明：预测结果默认写入 `output/预测日期/`

作用：

- 文档和当前行为一致

---

### 6. 把 `output/` 加入 `.gitignore`

文件：

- `.gitignore`

改动：

- 新增 `output/`

作用：

- 跑预测生成的 CSV/MD 文件不会污染 Git 状态

---

### 7. 补了两个轻量测试

文件：

- `tests/test_model.py`

改动：

- 增加路径解析测试
- 增加目录名生成测试

作用：

- 防止后续有人再改输出逻辑时把行为改坏

---

## 我做过的运行时操作（假设conda env是xuangu）

### 1. 删除了临时 `.venv`

原因：

- 你已经有 `conda` 环境 `xuangu`

结果：

- 后续全部使用 `xuangu`

---

### 2. 用 `xuangu` 跑通了预测

环境：

```bash
conda activate xuangu
```

已跑通流程包括：

- 数据更新
- 模型解压
- 模型筛选与预测生成

---

### 3. 已把现有结果同步放到新目录结构

当前已有结果目录：

- `output/2026-04-22/`

其中包含：

- `2026-04-22_ret.csv`
- `2026-04-22_filter_ret.csv`
- `total.csv`
- `total.md`

说明：

- 这批文件已经可以直接使用

---

## 现在启动预测的命令

如果你已经进入 `xuangu` 环境，预测命令还是：

```bash
cd ./roll && python ./roll.py model selection
```

如果从项目根目录完整写法是：

```bash
conda activate xuangu
cd /Users/ZeroneRY/Desktop/project/Qlib/qlibAssistant/roll
python ./roll.py model selection
```

---

## 和原来是否一样

结论：

- **启动预测的命令和原来一样**

不一样的只有：

- 默认输出位置变了
- 以前默认写到 `~/.qlibAssistant/analysis/selection_时间戳/`
- 现在默认写到 `项目根目录/output/预测日期/`

---

## 当前结果位置

你现在可以直接看：

- `output/2026-04-22/2026-04-22_ret.csv`
- `output/2026-04-22/2026-04-22_filter_ret.csv`

