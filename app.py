import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# 页面宽屏布局
st.set_page_config(page_title="全能数据看板", layout="wide")

# 1. 初始化 Session State (用于存储数据)
if 'df' not in st.session_state:
    st.session_state.df = None
if 'charts_config' not in st.session_state:
    st.session_state.charts_config = []

# --- 侧边栏：操作台 ---
with st.sidebar:
    st.header("🛠️ 看板操作台")
    
    # 配置说明
    with st.expander("📖 点击展开配置说明"):
        st.write("1. 上传Excel自动合并所有Sheet\n2. 在下方添加图表并绑定字段\n3. 顶部筛选器会自动关联数据")

    # 上传文件入口
    st.subheader("📂 数据源")
    uploaded_file = st.file_uploader("上传 Excel 文件", type=["xlsx", "xls"])
    
    if uploaded_file:
        # 读取并合并多 Sheet
        xlsx = pd.ExcelFile(uploaded_file)
        all_sheets = []
        for sheet in xlsx.sheet_names:
            df_sheet = pd.read_excel(xlsx, sheet_name=sheet)
            df_sheet['_来源Sheet'] = sheet  # 标记来源
            all_sheets.append(df_sheet)
        
        st.session_state.df = pd.concat(all_sheets, ignore_index=True)
        st.success(f"成功合并 {len(xlsx.sheet_names)} 个Sheet，共 {len(st.session_state.df)} 条数据")

    # 导出合并后的 Excel
    if st.session_state.df is not None:
        if st.button("📥 导出合并后的Excel"):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                st.session_state.df.to_excel(writer, index=False, sheet_name='MergedData')
            st.download_button(
                label="点击下载 Excel",
                data=output.getvalue(),
                file_name="Merged_Data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    st.divider()
    st.subheader("📊 图表管理")
    if st.button("➕ 添加新图表", use_container_width=True):
        st.session_state.charts_config.append({
            "id": len(st.session_state.charts_config),
            "title": f"图表 {len(st.session_state.charts_config) + 1}",
            "type": "柱状图",
            "x": st.session_state.df.columns[0] if len(st.session_state.df.columns) > 0 else "",
            "y": st.session_state.df.columns[1] if len(st.session_state.df.columns) > 1 else ""
        })
        st.rerun()

    # 导出/导入看板配置 (简化版：提供JSON下载)
    if st.session_state.charts_config:
        import json
        config_json = json.dumps(st.session_state.charts_config, ensure_ascii=False)
        st.download_button("💾 导出看板配置", config_json, file_name="config.json", mime="text/json")

# --- 页面主体 ---
df = st.session_state.df

if df is None:
    st.info("👈 请先在左侧上传 Excel 文件以开始分析")
else:
    # 2. 顶部全局筛选栏
    st.header("🔍 全局数据筛选")
    filter_cols = st.columns(4)
    filters = {}
    # 取前4个非数值列作为筛选示例
    cat_cols = df.select_dtypes(include=['object', 'category']).columns[:4]
    
    for i, col in enumerate(cat_cols):
        with filter_cols[i]:
            unique_vals = df[col].dropna().unique()
            selected = st.multiselect(f"筛选 {col}", options=unique_vals, key=f"filter_{col}")
            if selected:
                filters[col] = selected

    # 应用筛选
    filtered_df = df.copy()
    for col, vals in filters.items():
        filtered_df = filtered_df[filtered_df[col].isin(vals)]

    st.divider()

    # 3. 图表展示区
    st.header("📈 数据可视化展示")
    
    # 使用 Streamlit 的 columns 布局来展示多个图表
    for idx, config in enumerate(st.session_state.charts_config):
        with st.container(border=True):
            # 图表配置行
            col_set1, col_set2, col_set3, col_set4, col_set5 = st.columns([2, 2, 2, 2, 1])
            with col_set1:
                config['title'] = st.text_input("图表标题", config['title'], key=f"title_{idx}")
            with col_set2:
                config['type'] = st.selectbox("图表类型", ["柱状图", "条形图", "饼图", "散点图", "折线图", "线柱混搭"], key=f"type_{idx}")
            with col_set3:
                config['x'] = st.selectbox("X轴/维度", df.columns, index=list(df.columns).index(config['x']) if config['x'] in df.columns else 0, key=f"x_{idx}")
            with col_set4:
                config['y'] = st.selectbox("Y轴/数值", df.columns, index=list(df.columns).index(config['y']) if config['y'] in df.columns else (1 if len(df.columns)>1 else 0), key=f"y_{idx}")
            
            # 绘制图表
            chart_df = filtered_df
            chart_type = config['type']
            
            try:
                if chart_type == "柱状图":
                    fig = px.bar(chart_df, x=config['x'], y=config['y'], title=config['title'], text_auto=True)
                elif chart_type == "条形图":
                    fig = px.bar(chart_df, x=config['y'], y=config['x'], orientation='h', title=config['title'], text_auto=True)
                elif chart_type == "饼图":
                    fig = px.pie(chart_df, names=config['x'], values=config['y'], title=config['title'])
                elif chart_type == "散点图":
                    fig = px.scatter(chart_df, x=config['x'], y=config['y'], title=config['title'])
                elif chart_type == "折线图":
                    fig = px.line(chart_df, x=config['x'], y=config['y'], title=config['title'], markers=True)
                elif chart_type == "线柱混搭":
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=chart_df[config['x']], y=chart_df[config['y']], name=config['y']))
                    # 混搭图添加一条模拟趋势线
                    fig.add_trace(go.Scatter(x=chart_df[config['x']], y=chart_df[config['y']], mode='lines', name='趋势'))
                    fig.update_layout(title=config['title'])
                
                if chart_type != "线柱混搭":
                    fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"图表生成出错: {e}")
