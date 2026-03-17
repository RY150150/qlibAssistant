import re
from pathlib import Path
from typing import Dict

import pandas as pd
from loguru import logger

from utils import append_to_file, get_trade_data


class ModelReviewHelper:
    """负责模型预测结果的回测复盘逻辑，拆分自 ModelCLI 降低单文件复杂度。"""

    def __init__(self, cli: "ModelCLI"):
        # 延迟注入，避免循环依赖（类型仅作注释使用）
        self.cli = cli
        self.kwargs: Dict = cli.kwargs

        self.review_result_string = "# 复盘统计分析\n"
        self.review_result_string += (
            f"\n 统计时间 {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        self.review_result_df = {}
        self.review_result_df_filter = {}

    # ---------- CSV 单日回测 ----------
    def _review_csv(self, df, real_df, n1, n2):
        df = df[df["avg_score"] > 0].copy()  # 避免 SettingWithCopyWarning
        real_map = real_df.drop_duplicates("instrument").set_index("instrument")["real_label"]
        df["real_label"] = df["instrument"].map(real_map)

        df["error"] = df["avg_score"] - df["real_label"]
        df["abs_error"] = df["error"].abs()

        date_str = df["datetime"].iloc[0]
        print(f"分析 {date_str} csv")

        n1_renamed = n1[["instrument", "close"]].rename(columns={"close": "n1close"})
        n2_renamed = n2[["instrument", "high"]].rename(columns={"high": "n2high"})

        df = df.merge(n1_renamed, on="instrument", how="left")
        df = df.merge(n2_renamed, on="instrument", how="left")

        top_num_list = [10, 20, 30, 50, 80, 100]
        profit_num_list = [0.01 * i for i in range(1, 11)]  # 0.01 ~ 0.10

        topk_result_dict = {}
        topk_result_index = [
            "止盈1%胜率",
            "止盈2%胜率",
            "止盈3%胜率",
            "止盈4%胜率",
            "止盈5%胜率",
            "止盈6%胜率",
            "止盈7%胜率",
            "止盈8%胜率",
            "止盈9%胜率",
            "止盈10%胜率",
            "持有一天平均收益",
            "一天正收益占比",
        ]

        for top_num in top_num_list:
            topk_df = df.sort_values(by="avg_score", ascending=False).head(top_num)
            topk_avg_profit = topk_df["real_label"].mean()
            topk_radio = ((topk_df["real_label"] * topk_df["avg_score"]) > 0).sum() / len(topk_df)

            profit_list = []
            for profit_num in profit_num_list:
                topk_df_profit = (topk_df["n2high"] > topk_df["n1close"] * (1 + profit_num)).sum() / len(
                    topk_df
                )
                profit_list.append(topk_df_profit)

            profit_list.append(topk_avg_profit)
            profit_list.append(topk_radio)
            topk_result_dict[f"Top{top_num}"] = profit_list

        topk_result_df = pd.DataFrame(topk_result_dict, index=topk_result_index)
        topk_result_df.index.name = date_str

        def to_percent(val):
            if isinstance(val, (float, int)):
                return f"{val * 100:.2f}%"
            return val

        pct_df = topk_result_df.applymap(to_percent)
        print(pct_df.to_markdown(index=True))

        self.review_result_string += pct_df.to_markdown(index=True) + "\n"
        return df

    # ---------- 遍历单日子目录 ----------
    def _review_subdir(self, subdir: Path):
        print(f"- {subdir.name}")
        self.review_result_string += f"## {subdir.name}\n"

        date_str = next(
            (
                re.match(r"(\d{4}-\d{2}-\d{2})_.*\.csv", file.name).group(1)
                for file in subdir.iterdir()
                if file.is_file() and re.match(r"(\d{4}-\d{2}-\d{2})_.*\.csv", file.name)
            ),
            None,
        )
        if date_str:
            print(f"直接从文件名提取的日期: {date_str}")
        else:
            print("未发现格式为 xxxx-xx-xx_ 的 CSV 文件名")

        trade_data_list = get_trade_data(self.kwargs.get("provider_uri"))
        if date_str and trade_data_list and date_str in trade_data_list[-2:]:
            logger.info(f"还不能复盘 {date_str}")
            self.review_result_string += f"\n{subdir.name} 还不能复盘 {date_str}\n"
            return

        next1_date = None
        if date_str and trade_data_list:
            try:
                idx = trade_data_list.index(date_str)
                if idx + 1 < len(trade_data_list):
                    next1_date = trade_data_list[idx + 1]
            except ValueError:
                next1_date = None

        next2_date = None
        if next1_date and trade_data_list:
            try:
                idx = trade_data_list.index(next1_date)
                if idx + 1 < len(trade_data_list):
                    next2_date = trade_data_list[idx + 1]
            except ValueError:
                next2_date = None

        logger.info(
            f"开始复盘 {date_str if date_str else '[未知日期]'}  "
            f"btw:[下1个交易日: {next1_date if next1_date else '[未知日期]'}  "
            f"下2个交易日: {next2_date if next2_date else '[未知日期]'}]"
        )

        df_filter_ret, df_ret = None, None
        if date_str:
            filter_ret_path = subdir / f"{date_str}_filter_ret.csv"
            ret_path = subdir / f"{date_str}_ret.csv"

            if filter_ret_path.exists():
                try:
                    df_filter_ret = pd.read_csv(filter_ret_path)
                    print(f"已读取: {filter_ret_path.name}, 行数: {len(df_filter_ret)}")
                except Exception as e:
                    print(f"读取 {filter_ret_path.name} 出错: {e}")
            else:
                print(f"  未找到: {filter_ret_path.name}")

            if ret_path.exists():
                try:
                    df_ret = pd.read_csv(ret_path)
                    print(f"已读取: {ret_path.name}, 行数: {len(df_ret)}")
                except Exception as e:
                    print(f"读取 {ret_path.name} 出错: {e}")
            else:
                print(f"未找到: {ret_path.name}")

        real_df = self.cli.get_real_label(dates={"start": date_str, "end": date_str})
        real_df = real_df.reset_index()

        # 删除 'KMID' 及其右侧所有表项（包含 KMID）
        for name, df in [("df_ret", df_ret), ("df_filter_ret", df_filter_ret)]:
            if df is not None and not df.empty:
                if "KMID" in df.columns:
                    kmid_idx = df.columns.get_loc("KMID")
                    if name == "df_ret":
                        df_ret = df.iloc[:, :kmid_idx]
                    else:
                        df_filter_ret = df.iloc[:, :kmid_idx]
                else:
                    print(f"⚠️ {name} 中不存在 'KMID' 列，未做裁剪。")

        next1_date_original_data = self.cli.get_orignal_data(
            dates={"start": next1_date, "end": next1_date}
        )
        next2_date_original_data = self.cli.get_orignal_data(
            dates={"start": next2_date, "end": next2_date}
        )

        print("分析 df_ret:")
        self.review_result_string += f"### {date_str}_ret.csv\n"
        df = self._review_csv(df_ret, real_df, next1_date_original_data, next2_date_original_data)
        self.review_result_df[subdir.name] = df

        print("分析 df_filter_ret:")
        self.review_result_string += f"### {date_str}_filter_ret.csv\n"
        df = self._review_csv(
            df_filter_ret, real_df, next1_date_original_data, next2_date_original_data
        )
        self.review_result_df_filter[subdir.name] = df

    # ---------- 最终结果落盘 ----------
    def save_review_result(self):
        review_dir = Path("../review_csv")
        review_dir.mkdir(parents=True, exist_ok=True)
        for name, df in self.review_result_df.items():
            df.to_csv(review_dir / f"{name}_ret.csv", index=True)
        for name, df in self.review_result_df_filter.items():
            df.to_csv(review_dir / f"{name}_filter_ret.csv", index=True)

    def _get_review_subdirs(self) -> list[Path] | None:
        """获取复盘用的子目录列表，按日期倒序。目录不存在时返回 None。"""
        base_dir = Path("../qlib_score_csv")
        if not base_dir.exists() or not base_dir.is_dir():
            print(f"⚠️ 目录不存在: {base_dir.resolve()}")
            return None

        subdirs = [d for d in base_dir.iterdir() if d.is_dir()]
        print(f"共发现 {len(subdirs)} 个子目录：")

        def extract_date(subdir: Path):
            m = re.match(r"selection_(\d{8})_", subdir.name)
            if m:
                return m.group(1)
            return ""

        return sorted(subdirs, key=extract_date, reverse=True)

    # ---------- 对外入口 ----------
    def review(self):
        """马后炮"""
        sorted_subdirs = self._get_review_subdirs()
        if sorted_subdirs is None:
            return

        for subdir in sorted_subdirs:
            self._review_subdir(subdir)

        print(self.review_result_string)
        append_to_file("/tmp/review_result.md", self.review_result_string, mmode="w")
        logger.info("review result saved to /tmp/review_result.md")

        self.save_review_result()
        logger.info("review result saved to ../review_csv")

