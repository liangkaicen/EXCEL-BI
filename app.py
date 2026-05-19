import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 页面基础配置：宽屏布局，适配数据看板
st.set_page_config(page_title="交互式数据分析看板", layout="wide", page_icon="📊")

# 1. 性能优化：使用缓存加载数据
@st.cache_data
def load_data(uploaded_file):
    """读取Excel底表"""
    return pd.read_excel(uploaded_file)

# ---------------- 侧边栏操作台 ----------------
with st.sidebar:
    st.header("🛠️ 看板操作台")
    
    # 1. 点击展开配置说明
    with st.expander("📖 点击展开配置说明"):
        st.markdown("""
        1. 上传Excel底表（.xlsx）
        2. 在主体页面进行全局筛选与图表配置
        3. 支持动态添加多个图表模块
        """)

    # 2. 上传文件入口
    uploaded_file = st.file_uploader("上传Excel底表 (.xlsx)", type=["xlsx", "xls"])
    
    # 3. 添加新图表
    st.divider()
    if st.button("➕ 添加新图表模块", type="primary"):
        # 使用 session_state 来动态增加图表数量
        if 'chart_count' not in st.session_state:
            st.session_state.chart_count = 1
        else:
            st.session_state.chart_count += 1

    # 4. 图表配置说明
    with st.expander("📝 图表配置说明"):
        st.write("支持柱状图、折线图、饼图、散点图、气泡图、百分比柱状图、线柱混搭等。")
        st.write("可自定义数值标签格式（如百分比、千分位）及坐标轴格式。")
        
    # 5. 导入导出看板配置 (逻辑示意)
    st.divider()
    st.download_button(label="⚙️ 导出看板配置", data="配置JSON占位符", file_name="config.json")
    st.file_uploader("导入看板配置", type=["json"])

# ---------------- 页面主体展示区 ----------------
st.title("📊 企业级数据可视化看板")

if uploaded_file is not None:
    # 读取数据
    df = load_data(uploaded_file)
    
    # 顶部：全局数据筛选器
    st.header("🔍 全局筛选栏")
    # 筛选数值型和分类字段
    all_cols = df.columns.tolist()
    filter_cols = st.multiselect("选择筛选字段（关联字段）", options=all_cols)
    
    filtered_df = df.copy()
    # 修复报错：只有当用户选择了筛选字段时，才去生成列布局
    if filter_cols:
        cols = st.columns(len(filter_cols))
        for i, col_name in enumerate(filter_cols):
            unique_vals = filtered_df[col_name].dropna().unique()
            # 限制下拉框选项数量，防止数据量过大导致页面卡顿
            options = ["全部"] + list(unique_vals[:1000]) 
            selected_val = cols[i].selectbox(f"筛选 {col_name}", options=options)
            if selected_val != "全部":
                filtered_df = filtered_df[filtered_df[col_name] == selected_val]

    st.divider()

    # 传统统计学自动分析功能
    st.header("🧮 自动统计分析")
    if st.checkbox("展开统计分析报告", value=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**数据概览（描述性统计）：**")
            st.dataframe(filtered_df.describe())
        with col2:
            st.write("**数据缺失值统计：**")
            missing_data = filtered_df.isnull().sum()
            # 修复报错：如果有缺失值展示表格，如果没有则展示成功提示语
            if missing_data.any():
                st.dataframe(missing_data[missing_data > 0])
            else:
                st.success("✅ 数据非常完美，无缺失值！")

    st.divider()

    # 图表展示区域
    st.header("📉 可视化图表展示")
    
    # 动态渲染多个图表（每个图表的配置和图表相连展示）
    chart_count = st.session_state.get('chart_count', 1)
    
    # 提取数值列和分类列供图表配置使用
    numeric_cols = filtered_df.select_dtypes(include=['number']).columns.tolist()
    category_cols = filtered_df.select_dtypes(include=['object', 'datetime']).columns.tolist()
    
    for i in range(chart_count):
        with st.container(border=True):
            st.subheader(f"图表模块 {i+1}")
            # 图表配置区
            c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
            with c1:
                chart_type = st.selectbox("图表类型", 
                    ["柱状图", "条形图", "折线图", "饼图", "散点图", "气泡图", "百分比柱状图", "线柱混搭图"], 
                    key=f"type_{i}")
                x_axis = st.selectbox("X轴/分类字段", options=category_cols, key=f"x_{i}")
            with c2:
                y_axis = st.selectbox("Y轴/数值字段", options=numeric_cols, key=f"y_{i}")
                y_axis_2 = st.selectbox("次Y轴(混搭图用)", options=["无"] + numeric_cols, key=f"y2_{i}")
            with c3:
                color_val = st.selectbox("颜色/分组字段", options=["无"] + category_cols, key=f"color_{i}")
                text_format = st.selectbox("数值标签格式", options=["整数", "百分比(%)", "千分位(,)"], key=f"format_{i}")
            with c4:
                show_values = st.checkbox("显示数值标签", value=True, key=f"show_val_{i}")
                # 占位，保持布局整齐

            # 图表绘制区
            if x_axis and y_axis:
                try:
                    fig = None
                    # 基础格式设置
                    tick_format = ""
                    if text_format == "百分比(%)": tick_format = ".1%"
                    elif text_format == "千分位(,)": tick_format = ","
                    text_template = '%{y:' + tick_format + '}' if show_values else None

                    # 根据不同图表类型进行绘制
                    if chart_type == "柱状图":
                        fig = px.bar(filtered_df, x=x_axis, y=y_axis, color=color_val if color_val != "无" else None)
                        if show_values: fig.update_traces(texttemplate=text_template, textposition='outside')
                    
                    elif chart_type == "条形图":
                        fig = px.bar(filtered_df, x=y_axis, y=x_axis, orientation='h', color=color_val if color_val != "无" else None)
                        if show_values: fig.update_traces(texttemplate=text_template, textposition='outside')

                    elif chart_type == "折线图":
                        fig = px.line(filtered_df, x=x_axis, y=y_axis, color=color_val if color_val != "无" else None, markers=True)
                        if show_values: fig.update_traces(texttemplate=text_template, textposition='top center')

                    elif chart_type == "饼图":
                        fig = px.pie(filtered_df, names=x_axis, values=y_axis, hole=0.4)
                        if show_values: fig.update_traces(textinfo='percent+label', texttemplate=None)

                    elif chart_type == "散点图":
                        fig = px.scatter(filtered_df, x=x_axis, y=y_axis, color=color_val if color_val != "无" else None)
                    
                    elif chart_type == "气泡图":
                        # 气泡图需要额外的数值字段作为大小，这里默认用Y轴字段的大小
                        size_val = y_axis_2 if y_axis_2 != "无" else y_axis
                        fig = px.scatter(filtered_df, x=x_axis, y=y_axis, size=size_val, color=color_val if color_val != "无" else None, size_max=50)

                    elif chart_type == "百分比柱状图":
                        # 需要预先聚合数据计算百分比
                        if color_val != "无":
                            pivot = pd.crosstab(filtered_df[x_axis], filtered_df[color_val], normalize='index') * 100
                            fig = px.bar(pivot, x=pivot.index, y=pivot.columns, title="百分比堆积柱状图")
                            fig.update_layout(xaxis_title=x_axis, yaxis_title="百分比 (%)")
                            if show_values: fig.update_traces(texttemplate='%{y:.1f}%', textposition='inside')
                        else:
                            st.warning("百分比柱状图需要选择'颜色/分组字段'！")

                    elif chart_type == "线柱混搭图":
                        if y_axis_2 != "无":
                            fig = go.Figure()
                            fig.add_trace(go.Bar(x=filtered_df[x_axis], y=filtered_df[y_axis], name=y_axis))
                            fig.add_trace(go.Scatter(x=filtered_df[x_axis], y=filtered_df[y_axis_2], name=y_axis_2, mode='lines+markers', yaxis='y2'))
                            fig.update_layout(yaxis2=dict(title=y_axis_2, overlaying='y', side='right'))
                        else:
                            st.warning("线柱混搭图需要选择'次Y轴'字段！")

                    if fig:
                        # 坐标轴字段格式设置
                        fig.update_layout(yaxis_tickformat=tick_format, height=400)
                        st.plotly_chart(fig, use_container_width=True)
                
                except Exception as e:
                    st.error(f"图表渲染出错: {e}")
else:
    st.info("👈 请先在左侧侧边栏上传Excel文件以开始分析！")
