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

# --- 2. 单指标基础分析模块 ---
def analyze_single_metric(df, metric_name, time_col):
    """针对单个指标生成基础分析报告"""
    data = df[metric_name]
    total_val = data.sum()
    mean_val = data.mean()
    std_dev = data.std()
    cv = (std_dev / mean_val) * 100 if mean_val != 0 else 0
    stability_status = "⚠️ 波动较大" if cv > 50 else "✅ 相对稳定"
    
    with st.container(border=True):
        st.subheader(f"📊 指标：{metric_name}")
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("总量", f"{total_val:,.0f}")
        kpi2.metric("平均值", f"{mean_val:,.2f}")
        kpi3.metric("样本数", len(data))
        
        st.markdown(f"- **数据稳定性**：变异系数(CV)为 **{cv:.1f}%**，表明数据表现 **{stability_status}**。")
        
        # 智能图表匹配
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

# --- 3. 核心指标深度扫描引擎（全自动维度拆解 + 时间周期） ---
def run_auto_dimension_scan(df, selected_metrics, categorical_cols, time_col, time_granularity):
    st.header("🤖 核心指标多维度智能拆解")
    
    if not selected_metrics:
        st.info("请在侧边栏选择至少一个核心指标。")
        return
    
    # 1. 处理时间维度（新增逻辑）
    time_dim_name = None
    if time_col and time_granularity != "无":
        # 确保日期列是 datetime 格式
        if not pd.api.types.is_datetime64_any_dtype(df[time_col]):
            df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
        
        # 根据选择的粒度生成新的时间列
        if time_granularity == "按年":
            df['时间维度'] = df[time_col].dt.strftime('%Y年')
        elif time_granularity == "按月":
            df['时间维度'] = df[time_col].dt.strftime('%Y-%m')
        elif time_granularity == "按周":
            df['时间维度'] = df[time_col].dt.strftime('%Y第%W周')
        time_dim_name = '时间维度'

    # 合并所有可用于拆解的维度（常规文本列 + 新生成的时间列）
    all_dims = categorical_cols.copy()
    if time_dim_name:
        all_dims.insert(0, time_dim_name) # 将时间维度放在最前面

    if not all_dims:
        st.warning("⚠️ 未找到可用于拆解的分类维度（文本列或时间列），无法进行深度交叉分析。")
        return

    # 2. 遍历用户选择的每一个核心指标
    for metric in selected_metrics:
        st.divider()
        st.subheader(f"🎯 核心指标：【{metric}】的多维透视")
        total_metric_val = df[metric].sum()
        
        # 3. 遍历每一个维度进行自动分析
        for dim in all_dims:
            # 排除基数过大或过小的维度
            if df[dim].nunique() > 50 or df[dim].nunique() < 2:
                continue
                
            with st.expander(f"🔍 维度拆解：按【{dim}】分析", expanded=True):
                try:
                    # 自动聚合、排序
                    pivot_df = df.pivot_table(values=metric, index=dim, aggfunc='sum').sort_values(by=metric, ascending=False).reset_index()
                    
                    # 提取头部和尾部数据
                    top_row = pivot_df.iloc[0]
                    bottom_row = pivot_df.iloc[-1]
                    top_contribution = (top_row[metric] / total_metric_val) * 100 if total_metric_val > 0 else 0
                    
                    # 自动生成智能洞察文字
                    st.markdown(f"""
                    **💡 智能洞察：**
                    - **头部贡献**：**【{top_row[dim]}】** 是该指标的核心贡献者，单项数值达到 **{top_row[metric]:,.2f}**，占整体总量的 **{top_contribution:.1f}%**。
                    - **长尾差距**：表现最好的 **【{top_row[dim]}】** 与排名末尾的 **【{bottom_row[dim]}】**（数值：{bottom_row[metric]:,.2f}）之间存在显著差距。
                    - **业务建议**：建议总结 **【{top_row[dim]}】** 的成功经验，并关注排名后 3 位的异常低值情况。
                    """)
                    
                    # 绘制该维度的分析图表
                    fig = px.bar(pivot_df.head(20), x=dim, y=metric, title=f"各【{dim}】的【{metric}】排名 (Top 20)", color=metric, text_auto='.2s')
                    fig.update_layout(height=350, margin=dict(l=30, r=30, t=40, b=30))
                    st.plotly_chart(fig, use_container_width=True)
                    
                except Exception as e:
                    st.write(f"该维度无法进行数值聚合分析。")

# --- 4. 主程序 ---
def main():
    st.title("🤖 全自动智能数据分析看板")
    
    with st.sidebar:
        st.header("🛠️ 分析配置")
        uploaded_file = st.file_uploader("上传 Excel 文件", type=['xlsx', 'xls'])
        
        if uploaded_file:
            df_temp = load_data(uploaded_file)
            if df_temp is not None:
                numeric_cols = df_temp.select_dtypes(include=['number']).columns.tolist()
                
                # 自动识别时间列
                time_col = None
                for col in df_temp.columns:
                    if pd.api.types.is_datetime64_any_dtype(df_temp[col]) or '日期' in str(col) or '时间' in str(col):
                        time_col = col
                        break
                
                if numeric_cols:
                    st.subheader("🎯 核心指标选择")
                    selected_metrics = st.multiselect("选择核心指标", options=numeric_cols, default=[numeric_cols[0]])
                    
                    # 新增：时间粒度选择器
                    if time_col:
                        st.subheader("⏳ 时间周期拆解")
                        time_granularity = st.selectbox("选择时间维度", ["无", "按周", "按月", "按年"], index=2) # 默认按月
                    else:
                        time_granularity = "无"
                        st.info("未检测到日期/时间列，无法进行时间拆解。")
                else:
                    selected_metrics = []
                    time_granularity = "无"
            else:
                selected_metrics = []
                time_granularity = "无"
        else:
            selected_metrics = []
            time_granularity = "无"
        
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None and not df.empty:
            with st.expander("查看原始数据", expanded=False):
                st.dataframe(df, use_container_width=True)
            
            # 1. 基础单指标分析
            st.header("📊 核心指标基础概览")
            time_col = None
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]) or '日期' in str(col) or '时间' in str(col):
                    time_col = col
                    break
            
            cols = st.columns(2)
            for i, metric in enumerate(selected_metrics):
                with cols[i % 2]:
                    analyze_single_metric(df, metric, time_col)
            
            st.divider()
            
            # 2. 全自动多维度智能拆解（传入时间粒度参数）
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            run_auto_dimension_scan(df, selected_metrics, categorical_cols, time_col, time_granularity)

if __name__ == "__main__":
    main()
