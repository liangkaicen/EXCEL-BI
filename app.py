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

# --- 2. 核心指标深度扫描引擎（含大盘概览与维度拆解） ---
def run_auto_dimension_scan(df, selected_metrics, categorical_cols, time_col, time_granularity):
    st.header("🤖 核心指标多维度智能拆解")
    
    if not selected_metrics:
        st.info("请在侧边栏选择至少一个核心指标。")
        return
    
    # 1. 处理时间维度，生成用于分析的时间列
    time_dim_name = None
    if time_col and time_granularity != "无":
        if not pd.api.types.is_datetime64_any_dtype(df[time_col]):
            df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
        
        if time_granularity == "按年":
            df['时间维度'] = df[time_col].dt.strftime('%Y年')
            df['时间排序'] = df[time_col].dt.year
        elif time_granularity == "按月":
            df['时间维度'] = df[time_col].dt.strftime('%Y-%m')
            df['时间排序'] = df[time_col].dt.to_period('M').astype(int)
        elif time_granularity == "按周":
            df['时间维度'] = df[time_col].dt.strftime('%Y第%W周')
            df['时间排序'] = df[time_col].dt.strftime('%Y%W').astype(int)
        time_dim_name = '时间维度'

    # 合并所有可用于拆解的维度
    all_dims = categorical_cols.copy()
    if time_dim_name:
        all_dims.insert(0, time_dim_name)

    if not all_dims:
        st.warning("⚠️ 未找到可用于拆解的分类维度（文本列或时间列），无法进行深度交叉分析。")
        return

    # 2. 遍历用户选择的每一个核心指标
    for metric in selected_metrics:
        st.divider()
        st.subheader(f"🎯 核心指标：【{metric}】的多维透视")
        
        # --- 核心升级：生成大盘概览话术（仅在选择时间维度时生效） ---
        if time_dim_name:
            # 聚合生成时间序列大盘数据
            time_pivot = df.pivot_table(values=metric, index=['时间维度', '时间排序'], aggfunc='sum').reset_index().sort_values('时间排序')
            
            if len(time_pivot) >= 2:
                # 计算环比变化
                time_pivot['上期数值'] = time_pivot[metric].shift(1)
                time_pivot['环比变化'] = time_pivot[metric] - time_pivot['上期数值']
                time_pivot['环比涨跌幅'] = (time_pivot['环比变化'] / time_pivot['上期数值']) * 100
                
                # 获取最新一期的数据
                latest = time_pivot.iloc[-1]
                prev = time_pivot.iloc[-2]
                period_name = latest['时间维度']
                prev_period_name = prev['时间维度']
                current_val = latest[metric]
                change_val = latest['环比变化']
                change_pct = latest['环比涨跌幅']
                
                # 找出增长和下降的贡献点（细分维度拆解）
                # 这里我们拿第一个非时间维度（比如城市、产品）来作为主要拆解点
                sub_dim = None
                for dim in categorical_cols:
                    if df[dim].nunique() > 1 and df[dim].nunique() <= 50:
                        sub_dim = dim
                        break
                
                growth_point = "数据量较少，暂无细分贡献点。"
                if sub_dim:
                    # 计算各细分项的环比变化
                    sub_pivot = df.pivot_table(values=metric, index=[sub_dim, '时间排序'], aggfunc='sum').reset_index()
                    sub_pivot_wide = sub_pivot.pivot(index=sub_dim, columns='时间排序', values=metric).reset_index()
                    if len(sub_pivot_wide.columns) >= 3: # 至少有两期数据+索引列
                        sub_pivot_wide['变化值'] = sub_pivot_wide.iloc[:, -1] - sub_pivot_wide.iloc[:, -2]
                        sub_pivot_wide = sub_pivot_wide.sort_values('变化值', ascending=False)
                        
                        top_growth = sub_pivot_wide.iloc[0]
                        top_decline = sub_pivot_wide.iloc[-1]
                        
                        if change_val > 0:
                            growth_point = f"其中，**【{sub_dim}：{top_growth[sub_dim]}】** 拉动增长效果最明显，较上期增加了 **{top_growth['变化值']:,.2f}**。"
                        else:
                            growth_point = f"其中，**【{sub_dim}：{top_decline[sub_dim]}】** 是主要的下降拖累项，较上期减少了 **{abs(top_decline['变化值']):,.2f}**。"

                # 生成大盘概览话术
                trend_emoji = "📈" if change_val >= 0 else "📉"
                trend_text = "增长" if change_val >= 0 else "下降"
                overview_text = f"""
                #### {trend_emoji} 大盘概览：{period_name} {metric} 整体{trend_text}
                在 **{period_name}**，【{metric}】的总量为 **{current_val:,.2f}**。
                与上一个周期（{prev_period_name}）相比，整体{trend_text}了 **{abs(change_val):,.2f}**，环比涨跌幅为 **{change_pct:+.2f}%**。
                {growth_point}
                """
                st.info(overview_text)

        total_metric_val = df[metric].sum()
        
        # 3. 遍历每一个维度进行自动分析
        for dim in all_dims:
            if df[dim].nunique() > 50 or df[dim].nunique() < 2:
                continue
                
            with st.expander(f"🔍 维度拆解：按【{dim}】分析", expanded=True):
                try:
                    pivot_df = df.pivot_table(values=metric, index=dim, aggfunc='sum').sort_values(by=metric, ascending=False).reset_index()
                    
                    top_row = pivot_df.iloc[0]
                    bottom_row = pivot_df.iloc[-1]
                    top_contribution = (top_row[metric] / total_metric_val) * 100 if total_metric_val > 0 else 0
                    
                    st.markdown(f"""
                    **💡 智能洞察：**
                    - **头部贡献**：**【{top_row[dim]}】** 是该指标的核心贡献者，单项数值达到 **{top_row[metric]:,.2f}**，占整体总量的 **{top_contribution:.1f}%**。
                    - **长尾差距**：表现最好的 **【{top_row[dim]}】** 与排名末尾的 **【{bottom_row[dim]}】**（数值：{bottom_row[metric]:,.2f}）之间存在显著差距。
                    - **业务建议**：建议总结 **【{top_row[dim]}】** 的成功经验，并关注排名后 3 位的异常低值情况。
                    """)
                    
                    fig = px.bar(pivot_df.head(20), x=dim, y=metric, title=f"各【{dim}】的【{metric}】排名 (Top 20)", color=metric, text_auto='.2s')
                    fig.update_layout(height=350, margin=dict(l=30, r=30, t=40, b=30))
                    st.plotly_chart(fig, use_container_width=True)
                    
                except Exception as e:
                    st.write(f"该维度无法进行数值聚合分析。")

# --- 3. 主程序 ---
def main():
    st.title("🤖 全自动智能数据分析看板")
    
    # 初始化会话状态
    if 'run_analysis' not in st.session_state:
        st.session_state.run_analysis = False

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
                    selected_metrics = st.multiselect("选择核心指标", options=numeric_cols, default=[numeric_cols[0]], key="metrics_select")
                    
                    # 时间粒度选择器
                    if time_col:
                        st.subheader("⏳ 时间周期拆解")
                        time_granularity = st.selectbox("选择时间维度", ["无", "按周", "按月", "按年"], index=2, key="time_granularity")
                    else:
                        time_granularity = "无"
                        st.info("未检测到日期/时间列，无法进行时间拆解。")
                else:
                    selected_metrics = []
                    time_granularity = "无"
                
                # 运行按钮
                st.divider()
                if st.button("🚀 开始智能分析", type="primary", use_container_width=True):
                    st.session_state.run_analysis = True
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
            
            # 识别基础时间列
            time_col = None
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]) or '日期' in str(col) or '时间' in str(col):
                    time_col = col
                    break
            
            st.divider()
            
            # 全自动多维度智能拆解（由按钮触发）
            if st.session_state.run_analysis:
                with st.status("⚙️ 正在进行多维度数据拆解与智能洞察生成...", expanded=True) as status:
                    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
                    current_metrics = st.session_state.metrics_select
                    current_time_granularity = st.session_state.time_granularity
                    
                    st.write("正在聚合数据并生成图表...")
                    run_auto_dimension_scan(df, current_metrics, categorical_cols, time_col, current_time_granularity)
                    
                    status.update(label="✅ 智能分析完成！", state="complete", expanded=False)
            else:
                st.info("👈 请在左侧配置好参数后，点击【开始智能分析】按钮查看深度拆解报告。")

if __name__ == "__main__":
    main()
