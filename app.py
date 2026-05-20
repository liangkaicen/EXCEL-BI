import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 页面配置
st.set_page_config(page_title="全自动智能BI分析看板", layout="wide", page_icon="🤖")

# --- 1. 数据加载与缓存 ---
@st.cache_data
def load_data(uploaded_file):
    try:
        return pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"文件读取错误: {e}")
        return None

# --- 2. 核心指标深度扫描引擎 ---
def run_auto_dimension_scan(df, selected_metrics, categorical_cols, time_col, time_granularity):
    st.header("🤖 核心指标多维度智能拆解")

    # 核心逻辑：只有点击了按钮，才会进入这个函数
    # 使用 st.status 来管理“运行中”和“完成”的状态显示
    with st.status("正在聚合数据并生成图表...", expanded=True) as status:
        try:
            # --- 第一步：处理时间维度 ---
            time_dim_name = None
            if time_col and time_granularity != "无":
                if not pd.api.types.is_datetime64_any_dtype(df[time_col]):
                    df[time_col] = pd.to_datetime(df[time_col])

                if time_granularity == "按月":
                    df['_time_period'] = df[time_col].dt.to_period('M').astype(str)
                elif time_granularity == "按周":
                    df['_time_period'] = df[time_col].dt.isocalendar().week.astype(str) + "周"
                elif time_granularity == "按年":
                    df['_time_period'] = df[time_col].dt.year.astype(str)

                time_dim_name = '时间周期 (' + time_granularity + ')'
                st.caption(f"ℹ️ 已检测到时间列，正在按 **{time_granularity}** 进行趋势分析...")
            else:
                st.caption("ℹ️ 未选择时间维度，仅进行静态维度拆解。")

            # --- 第二步：遍历核心指标 ---
            for metric in selected_metrics:
                st.divider()
                st.subheader(f"🎯 核心指标：【{metric}】的多维透视")

                # 1. 生成大盘概览话术 (如果有时间维度)
                if time_dim_name:
                    # 按时间排序
                    time_summary = df.groupby('_time_period')[metric].sum().reset_index()
                    time_summary = time_summary.sort_values('_time_period')

                    if len(time_summary) >= 2:
                        current_val = time_summary.iloc[-1][metric]
                        prev_val = time_summary.iloc[-2][metric]
                        diff = current_val - prev_val
                        pct_change = (diff / prev_val) * 100 if prev_val != 0 else 0

                        trend = "📈 上升" if diff > 0 else "📉 下降" if diff < 0 else "➡️ 持平"
                        color = "red" if diff > 0 else "green" if diff < 0 else "gray" # 注意：通常涨是红/绿取决于市场，这里简单处理

                        st.markdown(f"""
                        > **📊 大盘概览**：在最新的时间周期（{time_summary.iloc[-1]['_time_period']}），**{metric}** 达到 **{current_val:,.0f}**。
                        > 较上一周期（{time_summary.iloc[-2]['_time_period']}）{trend} **{abs(diff):,.0f}** ({pct_change:+.1f}%)。
                        """)

                        # 查找增长/下降的主要贡献点 (简略版逻辑：对比两期的维度差值)
                        # 这里为了演示，我们简单列出最新一期的Top3
                        latest_period = time_summary.iloc[-1]['_time_period']
                        df_latest = df[df['_time_period'] == latest_period]

                        st.markdown(f"**🔍 最新周期（{latest_period}）表现突出的维度：**")
                        cols = st.columns(3)
                        for i, dim in enumerate(categorical_cols[:3]): # 只看前3个维度
                            top_row = df_latest.groupby(dim)[metric].sum().sort_values(ascending=False).head(1)
                            if not top_row.empty:
                                dim_name = top_row.index[0]
                                dim_val = top_row.values[0]
                                cols[i].metric(label=f"Top {dim}", value=f"{dim_val:,.0f}", delta=dim_name)

                    # 绘制趋势图
                    fig_trend = px.line(time_summary, x='_time_period', y=metric, markers=True, title=f"{metric} 趋势图")
                    st.plotly_chart(fig_trend, use_container_width=True)

                # 2. 遍历所有分类维度进行拆解
                for dim in categorical_cols:
                    # 聚合数据
                    dim_summary = df.groupby(dim)[metric].agg(['sum', 'count']).reset_index()
                    dim_summary = dim_summary.sort_values('sum', ascending=False)

                    # 只展示数据量大于0的维度
                    dim_summary = dim_summary[dim_summary['count'] > 0]

                    if dim_summary.empty:
                        continue

                    # 生成洞察
                    top_item = dim_summary.iloc[0]
                    top_name = top_item[dim]
                    top_val = top_item['sum']
                    contribution = (top_val / dim_summary['sum'].sum()) * 100

                    with st.expander(f"📊 维度拆解：按【{dim}】分析 (共 {len(dim_summary)} 个分类)", expanded=False):
                        c1, c2 = st.columns([1, 2])
                        with c1:
                            st.markdown(f"**智能洞察**：")
                            st.write(f"- **{top_name}** 是该维度的绝对主力，贡献了 **{top_val:,.0f}**，占比高达 **{contribution:.1f}%**。")

                            # 找出尾部
                            bottom_item = dim_summary.iloc[-1]
                            st.write(f"- 表现最弱的是 **{bottom_item[dim]}**，仅为 {bottom_item['sum']:,.0f}。")

                        with c2:
                            # 绘图
                            fig = px.bar(dim_summary, x=dim, y='sum', text_auto='.2s',
                                         title=f"{metric} 按 {dim} 分布", color='sum', color_continuous_scale='Blues')
                            st.plotly_chart(fig, use_container_width=True)

            # 状态更新为完成
            status.update(label="✅ 智能分析完成！", state="complete", expanded=False)

        except Exception as e:
            status.update(label="❌ 分析出错", state="error")
            st.error(f"分析过程中发生错误: {e}")

# --- 3. 主程序入口 ---
def main():
    # --- 侧边栏设置 ---
    st.sidebar.header("🎛️ 控制面板")

    # 1. 文件上传
    uploaded_file = st.sidebar.file_uploader("上传Excel文件", type=["xlsx", "xls", "csv"])

    if uploaded_file:
        # 加载数据
        df = load_data(uploaded_file)
        if df is not None:
            # 自动识别列类型
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            date_cols = df.select_dtypes(include=['datetime', 'datetimetz']).columns.tolist()

            # 尝试将看起来像日期的字符串列也加入日期选项（简单启发式）
            potential_dates = [col for col in categorical_cols if 'date' in col.lower() or 'time' in col.lower() or '日' in col or '月' in col or '年' in col]
            all_time_options = date_cols + potential_dates

            st.sidebar.divider()

            # 2. 核心指标选择
            metric_options = numeric_cols
            selected_metrics = st.sidebar.multiselect("选择核心指标", metric_options, default=metric_options[:1] if metric_options else [])

            # 3. 时间维度拆解
            st.sidebar.subheader("⏳ 时间周期拆解")
            time_granularity = st.sidebar.selectbox("选择时间维度", ["无", "按年", "按月", "按周"])
            time_col = None
            if time_granularity != "无":
                time_col = st.sidebar.selectbox("选择日期列", all_time_options, index=0 if all_time_options else 0)

            # 4. 运行按钮 (关键控制点)
            st.sidebar.divider()
            run_button = st.sidebar.button("🚀 开始智能分析", type="primary", use_container_width=True)

            # --- 主逻辑控制 ---
            # 只有当按钮被点击时，才执行分析函数
            # 利用 session_state 保持运行状态（可选，这里主要靠按钮触发）
            if run_button:
                # 调用分析函数
                run_auto_dimension_scan(df, selected_metrics, categorical_cols, time_col, time_granularity)
            else:
                # 按钮没点的时候，显示一些引导信息
                st.info("👈 请在左侧配置参数，并点击 **开始智能分析** 按钮以生成报告。")

    else:
        st.info("请上传 Excel 文件以开始分析。")

if __name__ == "__main__":
    main()
