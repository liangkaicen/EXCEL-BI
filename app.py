import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 页面基础配置 ---
st.set_page_config(page_title="全自动智能BI分析助手", layout="wide", page_icon="🚀")

# --- 2. 数据加载与缓存（最终稳健版） ---
@st.cache_data
def load_data(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file)
        
        # 【核心修复】彻底避开 pd.to_numeric 的报错，使用基础类型判断
        for col in df.columns:
            # 1. 如果整列原本就是数值类型，直接强制转为标准的 float64
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].astype('float64')
            else:
                # 2. 如果是文本，先转字符串，再尝试转数值（失败则变 NaN）
                converted = pd.to_numeric(df[col].astype(str), errors='coerce')
                # 3. 只有当这列里有超过一半的有效数字时，才认为它是数字列
                if converted.notna().sum() > len(df) * 0.5:
                    df[col] = converted
                
        return df
    except Exception as e:
        st.error(f"文件读取错误: {e}")
        return None

# --- 3. 辅助函数：期次排序 ---
def sort_by_period(period):
    """
    自定义排序逻辑：
    1. 优先级：寒 < 春 < 暑 < 秋
    2. 次级：数字大小
    """
    if not isinstance(period, str):
        return (99, 99)
        
    season_map = {'寒': 1, '春': 2, '暑': 3, '秋': 4}
    season = None
    num = 99
    
    # 提取季节
    for s in season_map.keys():
        if s in period:
            season = season_map[s]
            break
    
    # 提取数字
    import re
    nums = re.findall(r'\d+', period)
    if nums:
        num = int(nums[0])
        
    if season is None:
        return (99, num)
    return (season, num)

# --- 4. 辅助函数：颜色逻辑 ---
def get_color_class(metric_name, is_up):
    """根据指标类型（消耗vs产出）和涨跌方向返回颜色类"""
    consume_keywords = ['消耗', '成本', '费用', 'CPL', 'CPA', '例均']
    is_consume = any(k in metric_name for k in consume_keywords)
    
    # 消耗类：涨是红（坏），跌是绿（好）
    if is_consume:
        return "red" if is_up else "green"
    # 产出类：涨是绿（好），跌是红（坏）
    else:
        return "green" if is_up else "red"

# --- 5. 主程序逻辑 ---
def main():
    st.title("🚀 全自动智能BI分析助手")
    st.markdown("上传Excel文件，选择指标，一键生成多维分析报告。")

    # --- 文件上传 ---
    uploaded_file = st.file_uploader("上传 Excel 文件", type=["xlsx", "xls"])
    
    if uploaded_file:
        with st.spinner('正在加载并清洗数据...'):
            df = load_data(uploaded_file)
            
        if df is not None:
            st.success("✅ 数据加载成功！")
            
            # --- 识别列类型 ---
            # 排除明显的ID列（如果有的话）
            exclude_cols = [col for col in df.columns if 'id' in col.lower() or '日期' in col]
            cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            num_cols = df.select_dtypes(include=['number']).columns.tolist()
            
            # 清理列名空格
            df.columns = df.columns.str.strip()
            cat_cols = [c.strip() for c in cat_cols if c not in exclude_cols]
            num_cols = [c.strip() for c in num_cols]

            if not num_cols:
                st.error("未检测到数值列，请检查数据格式。")
                return

            # --- 侧边栏配置 ---
            st.sidebar.header("2. 分析配置")
            
            # 核心指标
            metric_col = st.sidebar.selectbox("选择核心指标 (数值型)", options=num_cols)
            
            # 分析维度
            dim_col = st.sidebar.selectbox("选择分析维度 (分类)", options=cat_cols)
            
            # 期次列（关键修复）
            # 尝试自动匹配“流量期次”或“期次”
            period_candidates = [c for c in df.columns if '期次' in c or '周期' in c]
            default_period = period_candidates[0] if period_candidates else None
            
            period_col = st.sidebar.selectbox(
                "选择流量期次 (趋势分析用)", 
                options=[None] + cat_cols, 
                index=cat_cols.index(default_period)+1 if default_period in cat_cols else 0
            )

            # --- 数据处理 ---
            # 1. 汇总数据用于大盘展示
            summary_data = df.groupby(dim_col)[metric_col].sum().reset_index()
            summary_data = summary_data.sort_values(by=metric_col, ascending=False)
            
            # 2. 计算占比
            total_val = summary_data[metric_col].sum()
            summary_data['占比'] = summary_data[metric_col] / total_val * 100
            
            # --- 页面展示 ---
            
            # 1. 核心指标透视
            st.subheader(f"核心指标：【{metric_col}】的多维透视")
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"**维度分析：{dim_col}**")
                top_item = summary_data.iloc[0]
                st.info(f"最大值：**{top_item[dim_col]} ({top_item[metric_col]:,.0f})**")
                st.write(f"占比：占总额的 **{top_item['占比']:.1f}%**")
            
            with col2:
                fig = px.bar(summary_data, x=dim_col, y=metric_col, 
                             color=metric_col, color_continuous_scale='Blues',
                             text_auto='.2s', title=f"按 [{dim_col}] 分布")
                st.plotly_chart(fig, use_container_width=True)

            # 2. 智能归因与趋势（修复重点）
            st.markdown("---")
            st.subheader("📊 核心指标大盘概览与归因")
            
            if period_col:
                # 确保期次列存在且能排序
                if period_col in df.columns:
                    # 尝试排序
                    try:
                        # 创建排序键
                        df['sort_key'] = df[period_col].apply(sort_by_period)
                        # 按排序键聚合
                        trend_data = df.groupby([period_col, 'sort_key'])[metric_col].sum().reset_index()
                        trend_data = trend_data.sort_values(by='sort_key')
                        
                        # 计算环比
                        trend_data['上期值'] = trend_data[metric_col].shift(1)
                        trend_data['环比增长'] = trend_data[metric_col] - trend_data['上期值']
                        trend_data['环比%'] = (trend_data['环比增长'] / trend_data['上期值']) * 100
                        
                        # 移除辅助列用于展示
                        trend_data = trend_data.drop(columns=['sort_key'])
                        
                        # 展示趋势图
                        fig_trend = px.line(trend_data, x=period_col, y=metric_col, markers=True,
                                            title=f"趋势分析：{metric_col} 随 {period_col} 变化")
                        st.plotly_chart(fig_trend, use_container_width=True)
                        
                        # 展示环比数据表
                        st.dataframe(trend_data, use_container_width=True)
                        
                    except Exception as e:
                        st.warning(f"期次排序计算出现异常：{e}。尝试按文本默认排序。")
                        # 备用方案：按文本排序
                        trend_data = df.groupby(period_col)[metric_col].sum().reset_index()
                        fig_trend = px.line(trend_data, x=period_col, y=metric_col, markers=True)
                        st.plotly_chart(fig_trend, use_container_width=True)
                        
                else:
                    st.warning(f"未找到列：{period_col}")
            else:
                st.info("请在侧边栏选择“流量期次”以查看趋势分析。")

            # 3. 贡献度分析
            st.markdown("---")
            st.subheader("🎯 贡献度分析 (帕累托)")
            
            summary_data['累计占比'] = summary_data['占比'].cumsum()
            
            fig_pareto = make_subplots(specs=[[{"secondary_y": True}]])
            
            # 柱状图
            fig_pareto.add_trace(
                go.Bar(x=summary_data[dim_col], y=summary_data[metric_col], name="数值", marker_color="#1f77b4"),
                secondary_y=False
            )
            
            # 折线图
            fig_pareto.add_trace(
                go.Line(x=summary_data[dim_col], y=summary_data['累计占比'], name="累计占比", marker_color="#ff7f0e"),
                secondary_y=True
            )
            
            fig_pareto.update_layout(title_text=f"{metric_col} 贡献度分析")
            fig_pareto.update_xaxes(title_text=dim_col)
            fig_pareto.update_yaxes(title_text="数值", secondary_y=False)
            fig_pareto.update_yaxes(title_text="累计占比 (%)", secondary_y=True, range=[0, 110])
            
            st.plotly_chart(fig_pareto, use_container_width=True)

if __name__ == "__main__":
    main()
