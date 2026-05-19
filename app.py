import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# 页面基础配置：宽屏布局，适配数据看板
st.set_page_config(page_title="交互式数据分析看板", layout="wide", page_icon="📊")

# 1. 性能优化：使用缓存加载和处理数据
@st.cache_data
def load_and_merge_data(uploaded_file, selected_sheets):
    """读取并合并Excel的多个Sheet"""
    excel_file = pd.ExcelFile(uploaded_file)
    dfs = []
    for sheet in selected_sheets:
        df = pd.read_excel(uploaded_file, sheet_name=sheet)
        df['来源Sheet'] = sheet # 标记数据来源
        dfs.append(df)
    # 纵向合并数据（假设各Sheet表头结构一致）
    combined_df = pd.concat(dfs, ignore_index=True)
    return combined_df

@st.cache_data
def convert_df_to_excel(df):
    """将合并后的DataFrame转换为Excel二进制流以供下载"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='合并数据')
    return output.getvalue()

# ---------------- 侧边栏操作台 ----------------
with st.sidebar:
    st.header("🛠️ 看板操作台")
    
    # 1. 点击展开配置说明
    with st.expander("📖 点击展开配置说明"):
        st.markdown("""
        1. 上传Excel文件（支持多Sheet）
        2. 勾选需要合并分析的Sheet
        3. 在主体页面进行筛选与图表配置
        """)

    # 2. 上传文件入口
    uploaded_file = st.file_uploader("上传Excel底表 (.xlsx)", type=["xlsx", "xls"])
    
    merged_df = None
    if uploaded_file:
        # 3. 合并分析sheet
        excel_file = pd.ExcelFile(uploaded_file)
        sheet_names = excel_file.sheet_names
        selected_sheets = st.multiselect("选择需要合并的Sheet", options=sheet_names, default=sheet_names)
        
        if st.button("开始合并与分析", type="primary"):
            if selected_sheets:
                with st.spinner("正在处理数据..."):
                    merged_df = load_and_merge_data(uploaded_file, selected_sheets)
                    st.success(f"成功合并 {len(selected_sheets)} 个Sheet，共 {len(merged_df)} 行数据！")
            else:
                st.warning("请至少选择一个Sheet！")

        if merged_df is not None:
            # 4. 导出合并后的excel
            excel_data = convert_df_to_excel(merged_df)
            st.download_button(
                label="📥 导出合并后的Excel",
                data=excel_data,
                file_name="merged_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # 5. 添加新图表 (逻辑示意)
    st.divider()
    st.subheader("📈 图表管理")
    add_chart = st.button("➕ 添加新图表模块")
    
    # 6. 图表配置说明
    with st.expander("📝 图表配置说明"):
        st.write("支持动态选择X/Y轴字段、图表类型及颜色主题。")
        
    # 7. 导入导出看板配置 (逻辑示意)
    st.divider()
    st.download_button(label="⚙️ 导出看板配置", data="配置JSON占位符", file_name="config.json")
    st.file_uploader("导入看板配置", type=["json"])

# ---------------- 页面主体展示区 ----------------
st.title("📊 企业级数据可视化看板")

if merged_df is not None:
    # 顶部：全局数据筛选器
    st.header("🔍 全局筛选栏")
    filter_cols = st.multiselect("选择筛选字段（关联字段）", options=merged_df.columns)
    
    filtered_df = merged_df.copy()
    
    # 修复报错：只有当用户选择了筛选字段时，才去生成列布局
    if filter_cols:
        # 动态生成筛选控件
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
    if st.checkbox("展开统计分析报告"):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**数据概览：**")
            st.dataframe(filtered_df.describe()) # 核心统计指标
        with col2:
            st.write("**缺失值统计：**")
            st.dataframe(filtered_df.isnull().sum())

    st.divider()

    # 图表展示区域 (以动态配置图表为例)
    st.header("📉 可视化图表展示")
    
    # 模拟“每一个图表的配置和图表要相连展示”的布局
    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            chart_type = st.selectbox("图表类型", ["柱状图", "折线图", "散点图", "饼图", "气泡图", "色块地图"])
            x_axis = st.selectbox("X轴字段", filtered_df.select_dtypes(include=['object', 'datetime']).columns)
        with c2:
            y_axis = st.selectbox("Y轴/数值字段", filtered_df.select_dtypes(include=['number']).columns)
            color_theme = st.selectbox("配色主题", px.colors.qualitative.Plotly)
        
        with c3:
            # 根据选择动态渲染图表
            if chart_type == "柱状图":
                fig = px.bar(filtered_df, x=x_axis, y=y_axis, title=f"{x_axis} - {y_axis} 柱状图", color_discrete_sequence=[color_theme])
            elif chart_type == "折线图":
                fig = px.line(filtered_df, x=x_axis, y=y_axis, title=f"{x_axis} - {y_axis} 趋势图", markers=True)
            elif chart_type == "散点图":
                fig = px.scatter(filtered_df, x=x_axis, y=y_axis, title=f"{x_axis} - {y_axis} 分布图")
            elif chart_type == "饼图":
                fig = px.pie(filtered_df, names=x_axis, values=y_axis, title=f"{x_axis} 占比分析")
            # 气泡图和地图需要特定的经纬度或额外数值字段，此处为逻辑示意
            else:
                fig = px.bar(filtered_df, x=x_axis, y=y_axis, title="示例图表")
            
            # 添加数值标签与格式设置 (Plotly原生支持)
            if chart_type in ["柱状图", "折线图"]:
                fig.update_traces(texttemplate='%{y:.2s}', textposition='outside') # 添加数值
                fig.update_layout(yaxis_tickformat=',.0f') # 坐标轴格式设置
            
            st.plotly_chart(fig, use_container_width=True)

else:
    st.info("👈 请先在左侧侧边栏上传Excel文件以开始分析！")
