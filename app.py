import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 页面基础配置
st.set_page_config(page_title="智能BI数据分析看板", layout="wide", page_icon="📊")

# --- 1. 数据加载与缓存 ---
@st.cache_data
def load_data(uploaded_file):
    try:
        return pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"文件读取错误: {e}")
        return None

# --- 2. 智能图表推荐函数 ---
def get_recommended_chart_type(x_data, y_data):
    """根据数据类型自动推荐图表类型"""
    if not x_data or not y_data:
        return "bar" # 默认
    
    # 简单的类型推断逻辑
    is_x_numeric = pd.api.types.is_numeric_dtype(x_data)
    is_y_numeric = pd.api.types.is_numeric_dtype(y_data)
    
    # 如果Y不是数值，通常不适合画图，或者作为分类
    if not is_y_numeric:
        return "bar"

    if is_x_numeric and is_y_numeric:
        # 数字 vs 数字 -> 散点图 (也可以选折线，但散点更通用)
        return "scatter"
    elif not is_x_numeric and is_y_numeric:
        # 文本/分类 vs 数字 -> 柱状图
        return "bar"
    else:
        return "bar"

# --- 侧边栏：操作台 ---
with st.sidebar:
    st.header("🛠️ 看板配置中心")
    
    with st.expander("📖 使用说明", expanded=False):
        st.markdown("""
        - **步骤1**: 上传Excel文件。
        - **步骤2**: 使用顶部筛选器过滤数据。
        - **步骤3**: 在下方点击“添加新图表”，系统会自动推荐图表类型。
        """)

    uploaded_file = st.file_uploader("上传 Excel 底表", type=["xlsx", "xls"])
    
    # 初始化图表配置列表
    if 'charts_config' not in st.session_state:
        st.session_state.charts_config = []

    # 添加新图表按钮
    if st.button("➕ 添加新图表模块", type="primary"):
        # 默认配置
        new_chart = {
            "id": len(st.session_state.charts_config),
            "title": f"图表 {len(st.session_state.charts_config) + 1}",
            "chart_type": "auto", # 自动模式
            "x_axis": None,
            "y_axis": None,
            "color": None,
            "text": None
        }
        st.session_state.charts_config.append(new_chart)

    # 图表配置循环
    if uploaded_file:
        df_temp = load_data(uploaded_file)
        columns = df_temp.columns.tolist()
        
        st.divider()
        st.subheader("📊 图表列表配置")
        
        # 遍历所有已添加的图表进行配置
        for i, chart in enumerate(st.session_state.charts_config):
            with st.expander(f"⚙️ 配置: {chart['title']}", expanded=True):
                # 图表标题
                chart['title'] = st.text_input("图表标题", chart['title'], key=f"title_{i}")
                
                # 图表类型选择
                chart_type_options = ["auto", "bar", "line", "scatter", "pie", "histogram", "box", "area"]
                chart['chart_type'] = st.selectbox("图表类型 (Auto=智能推荐)", chart_type_options, index=0, key=f"type_{i}")
                
                # 字段选择
                chart['x_axis'] = st.selectbox("X轴字段", [None] + columns, index=columns.index(chart['x_axis'])+1 if chart['x_axis'] in columns else 0, key=f"x_{i}")
                chart['y_axis'] = st.selectbox("Y轴字段 (数值)", [None] + columns, index=columns.index(chart['y_axis'])+1 if chart['y_axis'] in columns else 0, key=f"y_{i}")
                chart['color'] = st.selectbox("颜色分类 (可选)", [None] + columns, index=columns.index(chart['color'])+1 if chart['color'] in columns else 0, key=f"c_{i}")
                chart['text'] = st.selectbox("数值标签 (可选)", [None] + columns, index=columns.index(chart['text'])+1 if chart['text'] in columns else 0, key=f"t_{i}")
                
                # 删除按钮
                if st.button(f"删除图表 {i+1}", key=f"del_{i}"):
                    st.session_state.charts_config.pop(i)
                    st.rerun()

# --- 主页面 ---
if uploaded_file:
    df = load_data(uploaded_file)
    
    # 1. 全局筛选器
    st.subheader("🔍 全局数据筛选")
    filter_cols = st.multiselect("选择筛选字段", df.columns)
    
    filtered_df = df.copy()
    if filter_cols:
        col1, col2 = st.columns(len(filter_cols))
        for i, col_name in enumerate(filter_cols):
            unique_vals = filtered_df[col_name].dropna().unique()
            selected_val = col1.multiselect(f"筛选 {col_name}", unique_vals, key=f"filter_{col_name}")
            if selected_val:
                filtered_df = filtered_df[filtered_df[col_name].isin(selected_val)]
    
    st.markdown("---")

    # 2. 智能统计分析报告 (修复版)
    st.header("🧮 智能统计分析报告")
    
    numeric_cols = filtered_df.select_dtypes(include=['number']).columns
    
    if len(numeric_cols) > 0:
        # 自动选取第一个数值列作为核心指标展示
        main_metric = numeric_cols[0] 
        avg_val = filtered_df[main_metric].mean()
        total_val = filtered_df[main_metric].sum()
        
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        kpi_col1.metric(label=f"📊 平均 {main_metric}", value=f"{avg_val:,.2f}")
        kpi_col2.metric(label=f"💰 总计 {main_metric}", value=f"{total_val:,.2f}")
        kpi_col3.metric(label=f"🔢 记录数", value=f"{len(filtered_df)}")
        
        st.divider()

        # 自动生成文字结论
        st.subheader("📝 自动分析结论")
        
        # 简单的波动性分析
        std_dev = filtered_df[main_metric].std()
        cv = (std_dev / avg_val * 100) if avg_val != 0 else 0
        
        conclusion = f"当前数据集包含 **{len(filtered_df)}** 条记录。核心指标 **{main_metric}** 的平均值为 **{avg_val:,.2f}**，总计 **{total_val:,.2f}**。"
        
        if cv > 50:
            conclusion += f" ⚠️ 数据波动较大 (变异系数 {cv:.1f}%)，说明{main_metric}在不同样本间差异显著。"
        else:
            conclusion += f" ✅ 数据相对平稳 (变异系数 {cv:.1f}%)，{main_metric}表现较为一致。"
            
        st.markdown(conclusion)
        
        # 展示前几行数据
        with st.expander("查看筛选后的原始数据"):
            st.dataframe(filtered_df.head(), use_container_width=True)

    else:
        st.info("暂无数值型数据可供统计分析。")

    st.markdown("---")

    # 3. 图表展示区域
    st.header("📈 可视化图表展示")
    
    if not st.session_state.charts_config:
        st.info("请在左侧边栏点击 '添加新图表模块' 来生成图表。")
    else:
        # 遍历配置并渲染图表
        for chart_conf in st.session_state.charts_config:
            if not chart_conf['x_axis'] or not chart_conf['y_axis']:
                st.warning(f"图表 **{chart_conf['title']}** 缺少X轴或Y轴配置，请在侧边栏完善。")
                continue

            with st.container(border=True):
                st.subheader(chart_conf['title'])
                
                # 确定最终图表类型
                final_type = chart_conf['chart_type']
                if final_type == "auto":
                    final_type = get_recommended_chart_type(filtered_df[chart_conf['x_axis']], filtered_df[chart_conf['y_axis']])
                
                # 生成图表
                try:
                    # 公共参数
                    plot_args = {
                        "data_frame": filtered_df,
                        "x": chart_conf['x_axis'],
                        "y": chart_conf['y_axis'],
                        "color": chart_conf['color'],
                        "text": chart_conf['text'],
                        "title": "" # 标题已在容器上方显示
                    }
                    
                    # 针对饼图的特殊处理 (饼图通常不需要X轴，或者X是名字Y是值)
                    if final_type == "pie":
                        plot_args["names"] = chart_conf['x_axis']
                        plot_args["values"] = chart_conf['y_axis']
                        fig = px.pie(**plot_args)
                    elif final_type == "histogram":
                        fig = px.histogram(**plot_args)
                    elif final_type == "box":
                        fig = px.box(**plot_args)
                    elif final_type == "area":
                        fig = px.area(**plot_args)
                    elif final_type == "line":
                        fig = px.line(**plot_args, markers=True)
                    elif final_type == "scatter":
                        fig = px.scatter(**plot_args, size=chart_conf['y_axis']) # 散点图默认用Y轴控制大小
                    else: # 默认为柱状图
                        fig = px.bar(**plot_args)
                    
                    # 样式微调
                    fig.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20))
                    st.plotly_chart(fig, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"图表渲染出错: {e}")

else:
    st.info("👈 请在左侧侧边栏上传 Excel 文件以开始分析")
