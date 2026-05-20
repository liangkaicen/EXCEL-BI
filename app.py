import streamlit as st
import pandas as pd
import plotly.express as px
import re

# 页面配置
st.set_page_config(page_title="全自动智能BI分析看板", layout="wide", page_icon="🤖")

# --- 1. 流量期次专属排序逻辑 ---
def sort_by_period(period_str):
    """
    将 '寒春暑秋+数字' 格式的期次转换为可排序的元组
    排序权重：寒=1, 春=2, 暑=3, 秋=4
    例如：'寒1' -> (1, 1), '春10' -> (2, 10), '暑2' -> (3, 2)
    """
    if not isinstance(period_str, str):
        return (0, 0)
    
    # 提取开头的汉字学季
    season_match = re.match(r'([寒春暑秋])', period_str)
    # 提取后面的数字
    number_match = re.search(r'(\d+)', period_str)
    
    season_map = {'寒': 1, '春': 2, '暑': 3, '秋': 4}
    
    season_weight = season_map.get(season_match.group(1), 0) if season_match else 0
    number_weight = int(number_match.group(1)) if number_match else 0
    
    return (season_weight, number_weight)

# --- 2. 数据加载与缓存（精准清洗类型，保住数值） ---
@st.cache_data
def load_data(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file)
        
        # 精准清洗底层数据类型，规避 ArrowStringArray 报错同时保住数值
        for col in df.columns:
            converted_numeric = pd.to_numeric(df[col], errors='ignore')
            if pd.api.types.is_numeric_dtype(converted_numeric):
                df[col] = converted_numeric.astype('float64')
            else:
                df[col] = df[col].astype(str).replace('nan', '')
                
        return df
    except Exception as e:
        st.error(f"文件读取错误: {e}")
        return None

# --- 3. 业务指标属性字典 ---
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

# --- 4. 核心指标深度扫描引擎（融合期次趋势逻辑） ---
def run_auto_dimension_scan(df, selected_metrics, categorical_cols, time_col, time_granularity, period_col):
    st.header("🤖 核心指标多维度智能拆解")
    
    if not selected_metrics:
        st.info("请在侧边栏选择至少一个核心指标。")
        return
    
    # 1. 处理常规时间维度
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

    # 2. 处理流量期次维度（专属逻辑）
    period_dim_name = None
    if period_col and period_col in df.columns:
        period_dim_name = '_period_dim'
        df[period_dim_name] = df[period_col]
        # 按照专属的寒春暑秋+数字逻辑进行排序
        df = df.sort_values(by=period_dim_name, key=lambda x: x.map(sort_by_period))

    # --- 大盘概览与归因分析 ---
    st.subheader("📊 核心指标大盘概览与归因")
    
    # 优先使用期次或时间维度作为趋势基准
    trend_col = period_dim_name if period_dim_name else time_dim_name
    trend_periods = sorted([p for p in df[trend_col].unique() if p != '总计'], key=sort_by_period if trend_col == period_dim_name else None)
    
    if len(trend_periods) > 1:
        current_period = trend_periods[-1]
        previous_period = trend_periods[-2]
        
        df_current = df[df[trend_col] == current_period]
        df_prev = df[df[trend_col] == previous_period]
        
        overview_cols = st.columns(len(selected_metrics))
        
        for i, metric in enumerate(selected_metrics):
            val_curr = df_current[metric].sum()
            val_prev = df_prev[metric].sum()
            diff = val_curr - val_prev
            pct_change = (diff / val_prev * 100) if val_prev != 0 else 0
            
            metric_type = get_metric_type(metric)
            delta_color = "inverse" if metric_type == '消耗类' else "normal"

            with overview_cols[i]:
                st.metric(
                    label=f"{metric} ({current_period})",
                    value=f"{val_curr:,.0f}",
                    delta=f"{diff:+,.0f} ({pct_change:+.1f}%) vs {previous_period}",
                    delta_color=delta_color
                )
        
        # --- 关键变动归因分析 ---
        st.markdown("---")
        st.markdown("#### 🔍 关键变动归因分析")
        
        for metric in selected_metrics:
            best_driver = None
            best_impact = 0
            worst_driver = None
            worst_impact = 0
            
            for dim in categorical_cols:
                if dim in [time_col, period_col]: continue # 跳过时间/期次维度
                
                group_curr = df_current.groupby(dim)[metric].sum()
                group_prev = df_prev.groupby(dim)[metric].sum()
                
                all_dims = set(group_curr.index) | set(group_prev.index)
                diff_dict = {d: group_curr.get(d, 0) - group_prev.get(d, 0) for d in all_dims}
                
                if diff_dict:
                    max_dim, max_val = max(diff_dict.items(), key=lambda x: x[1])
                    min_dim, min_val = min(diff_dict.items(), key=lambda x: x[1])
                    
                    if max_val > best_impact:
                        best_impact, best_driver = max_val, f"【{dim}】{max_dim}"
                    if min_val < worst_impact:
                        worst_impact, worst_driver = min_val, f"【{dim}】{min_dim}"
            
            insight_text = f"在 **{current_period}** 周期内，**{metric}** 总计为 **{val_curr:,.0f}**，较上周期变化 **{diff:+,.0f}**。\n\n"
            if best_driver: insight_text += f"📈 **增长引擎**：主要由 {best_driver} 贡献（贡献增量 {best_impact:+,.0f}）。\n"
            if worst_driver: insight_text += f"📉 **主要拖累**：主要受 {worst_driver} 影响（导致减少 {worst_impact:+,.0f}）。"
            st.info(insight_text)

        # --- 业务健康度专项诊断 ---
        st.markdown("---")
        st.markdown("#### 💡 业务健康度专项诊断")
        
        north_star_metrics = [m for m in selected_metrics if '北极星A' in m or '北A' in m]
        if north_star_metrics:
            ns_val = df_current[north_star_metrics[0]].sum()
            if ns_val > 1:
                st.success(f"🎉 **北极星A诊断**：当前北A值为 **{ns_val:.2f}**，大于1，业务模型已**打正（盈利）**！")
            else:
                st.error(f"⚠️ **北极星A诊断**：当前北A值为 **{ns_val:.2f}**，小于等于1，业务模型**尚未打正**，请重点优化产出或压降消耗！")

        if '例子' in selected_metrics:
            example_val = df_current['例子'].sum()
            if 'GMV' in selected_metrics:
                gmv_val = df_current['GMV'].sum()
                example_yield = gmv_val / example_val if example_val > 0 else 0
                st.info(f"当前周期产生 **{example_val:.0f} 个例子**。后端撬动 GMV **{gmv_val:,.0f}**，**例产（GMV/例子）为 {example_yield:.2f}**。")

    else:
        st.warning("数据仅包含一个时间/期次周期，无法计算环比变化。仅展示当前数据分布。")

    st.markdown("---")

    # --- 详细维度拆解 ---
    for metric in selected_metrics:
        st.subheader(f"🎯 核心指标：【{metric}】的多维透视")
        
        # 将期次维度强制插到最前面，优先展示趋势
        dimensions_to_analyze = [d for d in categorical_cols if d not in [time_col, period_col]]
        if period_dim_name: dimensions_to_analyze.insert(0, period_dim_name)
        elif time_dim_name: dimensions_to_analyze.insert(0, time_dim_name)
            
        for dim in dimensions_to_analyze:
            if dim in ['_time_dim', '_period_dim']: continue
            
            chart_data = df.groupby(dim)[metric].sum().reset_index()
            # 如果是期次维度，使用专属排序；否则按数值降序
            if dim == period_col:
                chart_data['_sort_key'] = chart_data[dim].map(sort_by_period)
                chart_data = chart_data.sort_values(by='_sort_key')
                chart_data = chart_data.drop(columns=['_sort_key'])
            else:
                chart_data = chart_data.sort_values(by=metric, ascending=False)
            
            fig = px.bar(
                chart_data, x=dim, y=metric, text_auto='.2s',
                color=metric, color_continuous_scale='Blues', title=f"按 [{dim}] 分布"
            )
            fig.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=20))
            
            col_text, col_chart = st.columns([1, 2])
            with col_text:
                top_item = chart_data.iloc[0][dim]
                top_val = chart_data.iloc[0][metric]
                total_val = chart_data[metric].sum()
                share = (top_val / total_val) * 100 if total_val > 0 else 0
                st.markdown(f"**维度分析：{dim}**")
                st.write(f"- **最大值**：{top_item} ({top_val:,.0f})")
                st.write(f"- **占比**：占总额的 **{share:.1f}%**")
            with col_chart:
                st.plotly_chart(fig, use_container_width=True)

# --- 主程序入口 ---
def main():
    st.title("🚀 全自动智能BI分析助手")
    st.markdown("上传Excel文件，选择指标，一键生成多维分析报告。")

    with st.sidebar:
        st.header("1. 数据上传")
        uploaded_file = st.file_uploader("上传Excel文件", type=['xlsx', 'xls'])
        
        if uploaded_file:
            df = load_data(uploaded_file)
            if df is not None:
                st.success("数据加载成功！")
                
                st.divider()
                st.header("2. 分析配置")
                
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
                
                # 自动识别期次列（查找包含“期次”二字的列）
                period_candidates = [col for col in categorical_cols if '期次' in col]
                default_period = period_candidates[0] if period_candidates else None
                time_candidates = [col for col in categorical_cols if any(k in col.lower() for k in ['date', 'time', '日期', '时间'])]
                
                target_metric = st.multiselect("选择核心指标 (数值型)", numeric_cols)
                dimensions = st.multiselect("选择分析维度 (分类)", categorical_cols, default=categorical_cols[:3] if len(categorical_cols) >= 3 else categorical_cols)
                
                # 专属的期次选择框
                period_dimension = st.selectbox("选择流量期次 (专属趋势维度)", [None] + [c for c in categorical_cols if '期次' in c])
                # 常规时间选择框
                time_dimension = st.selectbox("选择常规时间维度 (可选)", [None] + time_candidates)
                time_granularity = st.selectbox("常规时间粒度", ["按月", "按周", "按日", "按年", "无"])
                
                st.divider()
                run_btn = st.button("🚀 开始智能分析", type="primary", use_container_width=True)
                
                if run_btn:
                    st.session_state['run_analysis'] = True
                    st.session_state['config'] = {
                        'df': df, 'metrics': target_metric, 'dims': dimensions,
                        'time_col': time_dimension, 'granularity': time_granularity,
                        'period_col': period_dimension
                    }
            else:
                st.stop()
        else:
            st.info("请先上传文件")
            st.stop()

    if st.session_state.get('run_analysis'):
        config = st.session_state['config']
        with st.status("正在聚合数据并生成图表...", expanded=True) as status:
            try:
                run_auto_dimension_scan(
                    config['df'], config['metrics'], config['dims'], 
                    config['time_col'], config['granularity'], config['period_col']
                )
                status.update(label="✅ 智能分析完成！", state="complete", expanded=False)
            except Exception as e:
                st.error(f"分析过程中出错: {e}")
                status.update(label="❌ 分析失败", state="error")

if __name__ == "__main__":
    main()
