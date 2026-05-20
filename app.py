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

# --- 2. 单指标深度分析模块（新增趋势图） ---
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
        
        # 绘制趋势图
        if time_col:
            # 优先使用日期列作为X轴
            fig_trend = px.line(df, x=time_col, y=metric_name, title=f"{metric_name} 趋势变化", markers=True)
        else:
            # 如果没有日期列，使用行号（索引）作为X轴
            df_temp = df.reset_index()
            fig_trend = px.line(df_temp, x='index', y=metric_name, title=f"{metric_name} 趋势变化 (按行号)", markers=True)
        
        fig_trend.update_layout(height=300, margin=dict(l=30, r=30, t=40, b=30))
        st.plotly_chart(fig_trend, use_container_width=True)

        # 单指标分布图
        fig_hist = px.histogram(df, x=metric_name, nbins=20, title=f"{metric_name} 分布直方图", marginal="box")
        fig_hist.update_layout(height=300, margin=dict(l=30, r=30, t=40, b=30))
        st.plotly_chart(fig_hist, use_container_width=True)

# --- 3. 深度智能分析引擎（全量扫描版） ---
def run_deep_analysis(df, selected_metrics):
    st.header("🧠 全量指标深度分析报告")
    
    if not selected_metrics:
        st.info("请在侧边栏至少选择一个核心指标进行分析。")
        return

    # 自动识别时间列（用于趋势图的X轴）
    time_col = None
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]) or '日期' in col or '时间' in col:
            time_col = col
            break

    # 动态布局：每 2 个指标并排展示
    cols = st.columns(2)
    for i, metric in enumerate(selected_metrics):
        # 使用取余运算，将指标交替放入左右两列
        with cols[i % 2]:
            analyze_single_metric(df, metric, time_col)

# --- 4. 智能图表推荐逻辑 ---
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
    
    # 侧边栏
    with st.sidebar:
        st.header("🛠️ 数据配置")
        uploaded_file = st.file_uploader("上传 Excel 文件", type=['xlsx', 'xls'])
        
        if uploaded_file:
            df_temp = load_data(uploaded_file)
            if df_temp is not None:
                # 提取所有数值列
                numeric_cols = df_temp.select_dtypes(include=['number']).columns.tolist()
                
                if numeric_cols:
                    st.subheader("🎯 核心指标筛选")
                    st.caption("默认分析所有数值指标，可手动取消勾选")
                    # 默认全选，支持手动选择 1 到多个
                    selected_metrics = st.multiselect(
                        "选择要分析的指标",
                        options=numeric_cols,
                        default=numeric_cols
                    )
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
            # 数据预览
            with st.expander("查看原始数据", expanded=False):
                st.dataframe(df, use_container_width=True)
            
            # 运行全量深度分析
            run_deep_analysis(df, selected_metrics)
            
            st.divider()
            
            # --- 自定义图表分析 ---
            st.header("📈 自定义图表分析")
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            all_cols = df.columns.tolist()
            
            if not numeric_cols:
                st.info("当前数据没有数值列，无法生成图表。")
            else:
                chart_type = st.selectbox("选择图表类型 (自动/手动)", ["自动推荐", "柱状图", "折线图", "散点图", "饼图"])
                
                col1, col2 = st.columns(2)
                with col1:
                    x_axis = st.selectbox("选择 X 轴", all_cols, index=0)
                with col2:
                    y_index = all_cols.index(numeric_cols[0]) if numeric_cols[0] in all_cols else 0
                    y_axis = st.selectbox("选择 Y 轴 (数值)", all_cols, index=y_index)
                    
                if st.button("生成图表"):
                    if x_axis and y_axis:
                        rec_type = get_chart_config(df[x_axis], df[y_axis])
                        final_type = chart_type if chart_type != "自动推荐" else rec_type
                        
                        fig = None
                        try:
                            if final_type == "bar":
                                fig = px.bar(df, x=x_axis, y=y_axis, title=f"{y_axis} by {x_axis}")
                            elif final_type == "line":
                                fig = px.line(df, x=x_axis, y=y_axis, title=f"{y_axis} Trend")
                            elif final_type == "scatter":
                                fig = px.scatter(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}")
                            elif final_type == "pie":
                                fig = px.pie(df, names=x_axis, values=y_axis, title=f"{y_axis} Distribution")
                            
                            if fig:
                                st.plotly_chart(fig, use_container_width=True)
                        except Exception as e:
                            st.error(f"图表生成失败: {e}")

if __name__ == "__main__":
    main()
