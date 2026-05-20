import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 页面配置
st.set_page_config(page_title="全量智能BI分析看板", layout="wide", page_icon="📊")

# --- 1. 数据加载与缓存 ---
@st.cache_data
def load_data(uploaded_file):
    try:
        return pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"文件读取错误: {e}")
        return None

# --- 2. 单指标深度分析模块 ---
def analyze_single_metric(df, metric_name, time_col):
    """针对单个指标生成深度分析报告"""
    data = df[metric_name]
    total_val = data.sum()
    mean_val = data.mean()
    std_dev = data.std()
    cv = (std_dev / mean_val) * 100 if mean_val != 0 else 0
    stability_status = "⚠️ 波动较大" if cv > 50 else "✅ 相对稳定"
    
    with st.container(border=True):
        st.subheader(f"📊 指标：{metric_name}")
        
        # 基础KPI展示
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("总量", f"{total_val:,.0f}")
        kpi2.metric("平均值", f"{mean_val:,.2f}")
        kpi3.metric("样本数", len(data))
        
        # 文字结论
        st.markdown(f"""
        - **数据稳定性**：变异系数(CV)为 **{cv:.1f}%**，表明数据表现 **{stability_status}**。
        - **极值情况**：最大值为 **{data.max():,.2f}**，最小值为 **{data.min():,.2f}**。
        """)
        
        # --- 智能图表匹配逻辑 ---
        data_len = len(df)
        is_ratio = any(keyword in metric_name for keyword in ['占比', '率', '比例', '百分比'])
        
        if is_ratio:
            fig_main = px.pie(df, values=metric_name, names=df.index.astype(str), title=f"{metric_name} 结构分布", hole=0.4)
        elif data_len <= 20:
            fig_main = px.bar(df, x=df.index, y=metric_name, title=f"{metric_name} 数值对比", text_auto='.2s')
        else:
            if time_col:
                fig_main = px.line(df, x=time_col, y=metric_name, title=f"{metric_name} 趋势变化", markers=True)
            else:
                df_temp = df.reset_index()
                fig_main = px.line(df_temp, x='index', y=metric_name, title=f"{metric_name} 趋势变化 (按行号)", markers=True)
        
        fig_main.update_layout(height=300, margin=dict(l=30, r=30, t=40, b=30))
        st.plotly_chart(fig_main, use_container_width=True)

        fig_hist = px.histogram(df, x=metric_name, nbins=20, title=f"{metric_name} 分布直方图", marginal="box")
        fig_hist.update_layout(height=300, margin=dict(l=30, r=30, t=40, b=30))
        st.plotly_chart(fig_hist, use_container_width=True)

# --- 3. 深度智能分析引擎 ---
def run_deep_analysis(df, selected_metrics):
    st.header("🧠 全量指标深度分析报告")
    if not selected_metrics:
        st.info("请在侧边栏至少选择一个核心指标进行分析。")
        return

    time_col = None
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]) or '日期' in str(col) or '时间' in str(col) or 'Date' in str(col):
            time_col = col
            break

    cols = st.columns(2)
    for i, metric in enumerate(selected_metrics):
        with cols[i % 2]:
            analyze_single_metric(df, metric, time_col)

# --- 4. 智能交叉分析模块（全新升级：增加自动洞察） ---
def run_cross_analysis(df, numeric_cols, categorical_cols):
    st.header("🔍 智能交叉分析与业务洞察")
    
    if not numeric_cols or not categorical_cols:
        st.warning("⚠️ 交叉分析需要同时具备数值列和分类（文本）列。")
        return

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        cross_metric = st.selectbox("选择分析指标 (数值)", numeric_cols, key="cross_metric")
    with col2:
        cross_dim = st.selectbox("选择分析维度 (分类)", categorical_cols, key="cross_dim")
    with col3:
        agg_type = st.selectbox("聚合方式", ["求和", "平均值", "计数"], key="agg_type")
    
    if cross_metric and cross_dim:
        agg_func_map = {"求和": "sum", "平均值": "mean", "计数": "count"}
        agg_func = agg_func_map[agg_type]
        
        try:
            pivot_df = df.pivot_table(
                values=cross_metric,
                index=cross_dim,
                aggfunc=agg_func
            ).sort_values(by=cross_metric, ascending=False).reset_index()
            
            # --- 核心升级：自动生成业务洞察 ---
            st.subheader("💡 智能业务洞察")
            total_val = pivot_df[cross_metric].sum()
            top_row = pivot_df.iloc[0]
            bottom_row = pivot_df.iloc[-1]
            
            top_contribution = (top_row[cross_metric] / total_val) * 100 if total_val > 0 else 0
            gap = top_row[cross_metric] - bottom_row[cross_metric]
            gap_ratio = (gap / bottom_row[cross_metric] * 100) if bottom_row[cross_metric] != 0 else 0
            
            insight_text = f"""
            - **头部效应明显**：**【{top_row[cross_dim]}】** 在该指标上表现最为突出，单项数值达到 **{top_row[cross_metric]:,.2f}**，贡献了整体总量的 **{top_contribution:.1f}%**。
            - **内部差异显著**：表现最好的 **【{top_row[cross_dim]}】** 与表现最弱的 **【{bottom_row[cross_dim]}】**（数值：{bottom_row[cross_metric]:,.2f}）之间，绝对差距达到了 **{gap:,.2f}**，头部是尾部的 **{gap_ratio:.1f}%**。
            - **业务建议**：建议深入复盘 **【{top_row[cross_dim]}】** 的成功经验，并针对排名后 20% 的维度进行专项优化或资源倾斜。
            """
            st.markdown(insight_text)

            # 绘制交叉分析图表
            fig_cross = px.bar(
                pivot_df, 
                x=cross_dim, 
                y=cross_metric, 
                title=f"各【{cross_dim}】的【{cross_metric}】{agg_type}",
                color=cross_metric,
                text_auto='.2s'
            )
            fig_cross.update_layout(height=400, xaxis_title=cross_dim, yaxis_title=cross_metric)
            st.plotly_chart(fig_cross, use_container_width=True)
            
            with st.expander("查看交叉分析明细数据"):
                st.dataframe(pivot_df, use_container_width=True, hide_index=True)
                
        except Exception as e:
            st.error(f"交叉分析生成失败: {e}")

# --- 5. 智能图表推荐逻辑 ---
def get_chart_config(x_series, y_series):
    chart_type = "bar"
    is_time = pd.api.types.is_datetime64_any_dtype(x_series)
    is_numeric_x = pd.api.types.is_numeric_dtype(x_series)
    is_numeric_y = pd.api.types.is_numeric_dtype(y_series)
    
    if is_time:
        chart_type = "line"
    elif not is_numeric_x and is_numeric_y:
        chart_type = "bar"
    elif is_numeric_x and is_numeric_y:
        chart_type = "scatter"
    return chart_type

# --- 主程序 ---
def main():
    st.title("📊 全量智能数据分析看板")
    
    with st.sidebar:
        st.header("🛠️ 数据配置")
        uploaded_file = st.file_uploader("上传 Excel 文件", type=['xlsx', 'xls'])
        
        if uploaded_file:
            df_temp = load_data(uploaded_file)
            if df_temp is not None:
                numeric_cols = df_temp.select_dtypes(include=['number']).columns.tolist()
                if numeric_cols:
                    st.subheader("🎯 核心指标筛选")
                    st.caption("默认分析所有数值指标，可手动取消勾选")
                    selected_metrics = st.multiselect("选择要分析的指标", options=numeric_cols, default=numeric_cols)
                else:
                    selected_metrics = []
                    st.warning("未找到数值列")
            else:
                selected_metrics = []
        else:
            selected_metrics = []
        
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None and not df.empty:
            with st.expander("查看原始数据", expanded=False):
                st.dataframe(df, use_container_width=True)
            
            run_deep_analysis(df, selected_metrics)
            st.divider()
            
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            numeric_cols_all = df.select_dtypes(include=['number']).columns.tolist()
            run_cross_analysis(df, numeric_cols_all, categorical_cols)
            
            st.divider()
            
            st.header("📈 自定义图表分析")
            if not numeric_cols_all:
                st.info("当前数据没有数值列，无法生成图表。")
            else:
                chart_type = st.selectbox("选择图表类型 (自动/手动)", ["自动推荐", "柱状图", "折线图", "散点图", "饼图"])
                col1, col2 = st.columns(2)
                with col1:
                    x_axis = st.selectbox("选择 X 轴", df.columns.tolist(), index=0)
                with col2:
                    y_axis = st.selectbox("选择 Y 轴 (数值)", numeric_cols_all, index=0)
                    
                if st.button("生成图表"):
                    if x_axis and y_axis:
                        rec_type = get_chart_config(df[x_axis], df[y_axis])
                        final_type = chart_type if chart_type != "自动推荐" else rec_type
                        fig = None
                        try:
                            if final_type == "bar": fig = px.bar(df, x=x_axis, y=y_axis, title=f"{y_axis} by {x_axis}")
                            elif final_type == "line": fig = px.line(df, x=x_axis, y=y_axis, title=f"{y_axis} Trend")
                            elif final_type == "scatter": fig = px.scatter(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}")
                            elif final_type == "pie": fig = px.pie(df, names=x_axis, values=y_axis, title=f"{y_axis} Distribution")
                            if fig: st.plotly_chart(fig, use_container_width=True)
                        except Exception as e:
                            st.error(f"图表生成失败: {e}")

if __name__ == "__main__":
    main()
