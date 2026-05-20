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

# --- 2. 核心指标深度扫描引擎（融合业务逻辑） ---
def run_auto_dimension_scan(df, selected_metrics, categorical_cols, time_col, time_granularity):
    st.header("🤖 核心指标多维度智能拆解")
    
    if not selected_metrics:
        st.info("请在侧边栏选择至少一个核心指标。")
        return
    
    # 1. 处理时间维度
    time_dim_name = None
    if time_col and time_granularity != "无":
        if not pd.api.types.is_datetime64_any_dtype(df[time_col]):
            df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
        
        # 根据粒度生成新的时间列
        if time_granularity == "按年":
            df['_time_dim'] = df[time_col].dt.year
        elif time_granularity == "按月":
            df['_time_dim'] = df[time_col].dt.to_period('M').astype(str)
        elif time_granularity == "按周":
            df['_time_dim'] = df[time_col].dt.isocalendar().week.astype(str)
        
        time_dim_name = '_time_dim'
        df = df.sort_values(by=time_dim_name)
    else:
        df['_time_dim'] = '总计'
        time_dim_name = '_time_dim'

    # --- 新增：大盘概览与归因分析 ---
    st.subheader("📊 核心指标大盘概览与归因")
    
    # 获取最新的时间周期
    time_periods = df[time_dim_name].unique()
    time_periods.sort()
    
    if len(time_periods) > 1:
        current_period = time_periods[-1]
        previous_period = time_periods[-2]
        
        df_current = df[df[time_dim_name] == current_period]
        df_prev = df[df[time_dim_name] == previous_period]
        
        overview_cols = st.columns(len(selected_metrics))
        
        for i, metric in enumerate(selected_metrics):
            val_curr = df_current[metric].sum()
            val_prev = df_prev[metric].sum()
            diff = val_curr - val_prev
            pct_change = (diff / val_prev * 100) if val_prev != 0 else 0
            
            with overview_cols[i]:
                st.metric(
                    label=f"{metric} ({current_period})",
                    value=f"{val_curr:,.0f}",
                    delta=f"{diff:+,.0f} ({pct_change:+.1f}%) vs {previous_period}"
                )
        
        # --- 归因分析：寻找增长/下降点 ---
        st.markdown("---")
        st.markdown("#### 🔍 关键变动归因分析")
        
        for metric in selected_metrics:
            best_driver = None
            best_impact = 0
            worst_driver = None
            worst_impact = 0
            
            # 遍历分类维度
            for dim in categorical_cols:
                # 计算当前周期各维度的值
                group_curr = df_current.groupby(dim)[metric].sum()
                # 计算上一周期各维度的值
                group_prev = df_prev.groupby(dim)[metric].sum()
                
                # 合并并对齐索引
                diff_series = group_curr - group_prev
                
                if not diff_series.empty:
                    max_val = diff_series.max()
                    min_val = diff_series.min()
                    
                    if max_val > best_impact:
                        best_impact = max_val
                        best_driver = f"【{dim}】{diff_series.idxmax()}"
                    
                    if min_val < worst_impact:
                        worst_impact = min_val
                        worst_driver = f"【{dim}】{diff_series.idxmin()}"
            
            # 生成概览话术
            insight_text = f"在 **{current_period}** 周期内，**{metric}** 总计为 **{val_curr:,.0f}**，较上周期变化 **{diff:+,.0f}**。\n\n"
            
            if best_driver:
                insight_text += f"📈 **增长引擎**：主要由 {best_driver} 贡献（贡献增量 {best_impact:+,.0f}）。\n"
            if worst_driver:
                insight_text += f"📉 **主要拖累**：主要受 {worst_driver} 影响（导致减少 {worst_impact:+,.0f}）。"
            
            st.info(insight_text)

    else:
        st.warning("数据仅包含一个时间周期，无法计算环比变化。仅展示当前数据分布。")

    st.markdown("---")

    # --- 3. 详细维度拆解（融合业务专属逻辑） ---
    for metric in selected_metrics:
        st.subheader(f"🎯 核心指标：【{metric}】的多维透视")
        
        # 确定要分析的维度列表
        dimensions_to_analyze = categorical_cols.copy()
        if time_dim_name:
            dimensions_to_analyze.insert(0, time_dim_name)
            
        for dim in dimensions_to_analyze:
            if dim == '_time_dim': continue
            
            # 计算聚合数据
            chart_data = df.groupby(dim)[metric].sum().reset_index()
            chart_data = chart_data.sort_values(by=metric, ascending=False)
            
            # 生成图表
            fig = px.bar(
                chart_data, 
                x=dim, 
                y=metric, 
                text_auto='.2s',
                color=metric,
                color_continuous_scale='Blues',
                title=f"按 [{dim}] 分布"
            )
            fig.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=20))
            
            # --- 布局调整：左侧文字(1)，右侧图表(2) ---
            col_text, col_chart = st.columns([1, 2])
            
            with col_text:
                # 简单的文字分析
                top_item = chart_data.iloc[0][dim]
                top_val = chart_data.iloc[0][metric]
                total_val = chart_data[metric].sum()
                share = (top_val / total_val) * 100
                
                st.markdown(f"**维度分析：{dim}**")
                st.write(f"- **最大值**：{top_item} ({top_val:,.0f})")
                st.write(f"- **占比**：占总额的 **{share:.1f}%**")
                st.write(f"- **最小值**：{chart_data.iloc[-1][dim]}")
            
            with col_chart:
                st.plotly_chart(fig, use_container_width=True)

# --- 主程序入口 ---
def main():
    st.title("🚀 全自动智能BI分析助手")
    st.markdown("上传Excel文件，选择指标，一键生成多维分析报告。")

    # 侧边栏
    with st.sidebar:
        st.header("1. 数据上传")
        uploaded_file = st.file_uploader("上传Excel文件", type=['xlsx', 'xls'])
        
        if uploaded_file:
            df = load_data(uploaded_file)
            if df is not None:
                st.success("数据加载成功！")
                with st.expander("查看原始数据预览", expanded=False):
                    st.dataframe(df.head())
                
                st.divider()
                
                st.header("2. 分析配置")
                # 自动识别列类型
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
                date_cols = [col for col in categorical_cols if 'date' in col.lower() or 'time' in col.lower()]
                
                # 用户选择
                target_metric = st.multiselect("选择核心指标 (数值型)", numeric_cols)
                dimensions = st.multiselect("选择分析维度 (分类)", categorical_cols, default=categorical_cols[:3])
                
                time_dimension = st.selectbox("选择时间维度 (可选)", [None] + date_cols)
                time_granularity = st.selectbox("时间粒度", ["按月", "按周", "按日", "按年", "无"])
                
                st.divider()
                
                # 运行按钮
                run_btn = st.button("🚀 开始智能分析", type="primary", use_container_width=True)
                
                if run_btn:
                    # 使用 Session State 标记需要运行
                    st.session_state['run_analysis'] = True
                    st.session_state['config'] = {
                        'df': df,
                        'metrics': target_metric,
                        'dims': dimensions,
                        'time_col': time_dimension,
                        'granularity': time_granularity
                    }
            else:
                st.stop()
        else:
            st.info("请先上传文件")
            st.stop()

    # 主区域：根据 Session State 决定是否运行
    if st.session_state.get('run_analysis'):
        config = st.session_state['config']
        
        # 使用 status 容器显示运行状态
        with st.status("正在聚合数据并生成图表...", expanded=True) as status:
            try:
                run_auto_dimension_scan(
                    config['df'], 
                    config['metrics'], 
                    config['dims'], 
                    config['time_col'], 
                    config['granularity']
                )
                status.update(label="✅ 智能分析完成！", state="complete", expanded=False)
            except Exception as e:
                st.error(f"分析过程中出错: {e}")
                status.update(label="❌ 分析失败", state="error")

if __name__ == "__main__":
    main()
