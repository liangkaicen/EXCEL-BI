import streamlit as st
import pandas as pd
import plotly.express as px

# 页面配置
st.set_page_config(page_title="全自动智能BI分析看板", layout="wide", page_icon="🤖")

# --- 1. 数据加载与缓存（彻底规避 ArrowStringArray 报错） ---
@st.cache_data
def load_data(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file)
        
        # 【核心修复】强制清洗底层数据类型，彻底规避 Arrow 兼容性问题
        for col in df.columns:
            # 强制将所有文本类数据转为最原始的 Python str 对象
            if pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col]):
                df[col] = df[col].astype(str).replace('nan', '')
            # 强制将所有数值类数据转为标准的 float64
            elif pd.api.types.is_numeric_dtype(df[col]):
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('float64')
                
        return df
    except Exception as e:
        st.error(f"文件读取错误: {e}")
        return None

# --- 2. 业务指标属性字典（根据你的要求内化） ---
METRIC_ATTRIBUTES = {
    '消耗类': ['线索', '粉丝', '成本'],
    '产出类': ['例子', 'PV', 'GMV', '利润', '北极星A', '北A']
}

def get_metric_type(metric_name):
    """识别指标是消耗还是产出"""
    for attr_type, keywords in METRIC_ATTRIBUTES.items():
        if any(keyword in str(metric_name) for keyword in keywords):
            return attr_type
    return '未知'

# --- 3. 核心指标深度扫描引擎（融合业务逻辑） ---
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
        
        if time_granularity == "按年":
            df['_time_dim'] = df[time_col].dt.year.astype(str)
        elif time_granularity == "按月":
            df['_time_dim'] = df[time_col].dt.to_period('M').astype(str)
        elif time_granularity == "按周":
            df['_time_dim'] = df[time_col].dt.isocalendar().week.astype(str)
        elif time_granularity == "按日":
            df['_time_dim'] = df[time_col].dt.date.astype(str)
        
        time_dim_name = '_time_dim'
        df = df.sort_values(by=time_dim_name)
    else:
        df['_time_dim'] = '总计'
        time_dim_name = '_time_dim'

    # --- 新增：大盘概览与归因分析 ---
    st.subheader("📊 核心指标大盘概览与归因")
    
    # 获取最新的时间周期
    time_periods = sorted([p for p in df[time_dim_name].unique() if p != '总计'])
    
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
            
            # 根据指标属性（消耗/产出）调整 Delta 颜色的逻辑
            metric_type = get_metric_type(metric)
            delta_color = "normal"
            if metric_type == '消耗类':
                # 消耗类指标，下降（负数）是好事，显示绿色；上升（正数）是坏事，显示红色
                delta_color = "inverse" 
            elif metric_type == '产出类':
                # 产出类指标，上升（正数）是好事，显示绿色
                delta_color = "normal"

            with overview_cols[i]:
                st.metric(
                    label=f"{metric} ({current_period})",
                    value=f"{val_curr:,.0f}",
                    delta=f"{diff:+,.0f} ({pct_change:+.1f}%)",
                    delta_color=delta_color
                )
        
        # --- 归因分析：寻找增长/下降点 ---
        st.markdown("---")
        st.markdown("#### 🔍 关键变动归因分析")
        
        for metric in selected_metrics:
            best_driver = None
            best_impact = 0
            worst_driver = None
            worst_impact = 0
            
            for dim in categorical_cols:
                group_curr = df_current.groupby(dim)[metric].sum()
                group_prev = df_prev.groupby(dim)[metric].sum()
                
                # 对齐索引并计算差值
                all_dims = set(group_curr.index) | set(group_prev.index)
                diff_dict = {}
                for d in all_dims:
                    curr_val = group_curr.get(d, 0)
                    prev_val = group_prev.get(d, 0)
                    diff_dict[d] = curr_val - prev_val
                
                if diff_dict:
                    max_dim = max(diff_dict, key=diff_dict.get)
                    min_dim = min(diff_dict, key=diff_dict.get)
                    max_val = diff_dict[max_dim]
                    min_val = diff_dict[min_dim]
                    
                    if max_val > best_impact:
                        best_impact = max_val
                        best_driver = f"【{dim}】{max_dim}"
                    
                    if min_val < worst_impact:
                        worst_impact = min_val
                        worst_driver = f"【{dim}】{min_dim}"
            
            # 生成概览话术
            insight_text = f"在 **{current_period}** 周期内，**{metric}** 总计为 **{val_curr:,.0f}**，较上周期变化 **{diff:+,.0f}**。\n\n"
            
            if best_driver:
                insight_text += f"📈 **增长引擎**：主要由 {best_driver} 贡献（贡献增量 {best_impact:+,.0f}）。\n"
            if worst_driver:
                insight_text += f"📉 **主要拖累**：主要受 {worst_driver} 影响（导致减少 {worst_impact:+,.0f}）。"
            
            st.info(insight_text)

        # --- 专属业务逻辑：北极星A与例子专项分析 ---
        st.markdown("---")
        st.markdown("#### 💡 业务健康度专项诊断")
        
        # 1. 北极星A（北A）盈利判断
        north_star_metrics = [m for m in selected_metrics if '北极星A' in m or '北A' in m]
        if north_star_metrics:
            ns_metric = north_star_metrics[0]
            ns_val = df_current[ns_metric].sum()
            if ns_val > 1:
                st.success(f"🎉 **北极星A诊断**：当前北A值为 **{ns_val:.2f}**，大于1，业务模型已**打正（盈利）**！")
            else:
                st.error(f"⚠️ **北极星A诊断**：当前北A值为 **{ns_val:.2f}**，小于等于1，业务模型**尚未打正**，请重点优化产出或压降消耗！")

        # 2. 例子（前端/后端枢纽）分析
        if '例子' in selected_metrics:
            st.markdown("**例子（前端转化结果 / 后端转化起点）**")
            example_val = df_current['例子'].sum()
            # 尝试计算例产 (GMV / 例子)
            if 'GMV' in selected_metrics:
                gmv_val = df_current['GMV'].sum()
                example_yield = gmv_val / example_val if example_val > 0 else 0
                st.info(f"当前周期产生 **{example_val:.0f} 个例子**。后端撬动 GMV **{gmv_val:,.0f}**，**例产（GMV/例子）为 {example_yield:.2f}**。")

    else:
        st.warning("数据仅包含一个时间周期，无法计算环比变化。仅展示当前数据分布。")

    st.markdown("---")

    # --- 4. 详细维度拆解 ---
    for metric in selected_metrics:
        st.subheader(f"🎯 核心指标：【{metric}】的多维透视")
        
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
            
            # 布局调整：左侧文字(1)，右侧图表(2)
            col_text, col_chart = st.columns([1, 2])
            
            with col_text:
                top_item = chart_data.iloc[0][dim]
                top_val = chart_data.iloc[0][metric]
                total_val = chart_data[metric].sum()
                share = (top_val / total_val) * 100 if total_val > 0 else 0
                
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
                # 智能推测时间列
                date_cols = [col for col in categorical_cols if any(keyword in col.lower() for keyword in ['date', 'time', '日期', '时间'])]
                
                # 用户选择
                target_metric = st.multiselect("选择核心指标 (数值型)", numeric_cols)
                dimensions = st.multiselect("选择分析维度 (分类)", categorical_cols, default=categorical_cols[:3] if len(categorical_cols) >= 3 else categorical_cols)
                
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
