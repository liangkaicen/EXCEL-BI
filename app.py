import streamlit as st
import pandas as pd
import plotly.express as px
import json

# 页面配置
st.set_page_config(page_title="全能交互式数据看板", layout="wide")
st.title("📊 Excel 全能交互式数据看板")

# 初始化 Session State 用于存储图表配置
if "charts" not in st.session_state:
    st.session_state.charts = []

# 1. 上传文件区域
uploaded_file = st.file_uploader("请上传 Excel 文件 (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    # 读取数据
    df = pd.read_excel(uploaded_file)
    
    # 2. 数据筛选区域 (方案一：基础字段筛选)
    with st.expander("🔍 点击展开数据筛选面板", expanded=True):
        filtered_df = df.copy()
        
        # 文本/分类字段筛选
        text_cols = df.select_dtypes(include=['object']).columns.tolist()
        if text_cols:
            cols = st.columns(len(text_cols))
            for i, col_name in enumerate(text_cols):
                with cols[i]:
                    unique_values = df[col_name].dropna().unique()
                    selected_values = st.multiselect(f"筛选 {col_name}", unique_values, default=unique_values, key=f"filter_{col_name}")
                    filtered_df = filtered_df[filtered_df[col_name].isin(selected_values)]

        # 数值字段筛选
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        if num_cols:
            cols = st.columns(len(num_cols))
            for i, col_name in enumerate(num_cols):
                with cols[i]:
                    min_val, max_val = float(df[col_name].min()), float(df[col_name].max())
                    # 防止最小最大值相等导致滑块报错
                    if min_val == max_val:
                        st.write(f"{col_name}: 固定值 {min_val}")
                    else:
                        range_val = st.slider(f"筛选 {col_name}", min_val, max_val, (min_val, max_val), key=f"slider_{col_name}")
                        filtered_df = filtered_df[(filtered_df[col_name] >= range_val[0]) & (filtered_df[col_name] <= range_val[1])]

        # 日期字段筛选
        date_cols = df.select_dtypes(include=['datetime']).columns.tolist()
        if date_cols:
            cols = st.columns(len(date_cols))
            for i, col_name in enumerate(date_cols):
                with cols[i]:
                    min_date, max_date = df[col_name].min().date(), df[col_name].max().date()
                    date_range = st.date_input(f"筛选 {col_name}", [min_date, max_date], key=f"date_{col_name}")
                    if len(date_range) == 2:
                        filtered_df = filtered_df[(filtered_df[col_name] >= pd.to_datetime(date_range[0])) & (filtered_df[col_name] <= pd.to_datetime(date_range[1]))]
        
        st.success(f"✅ 筛选完成，当前展示 {len(filtered_df)} 条数据（原始数据共 {len(df)} 条）")

    # 获取筛选后数据的列名，用于后续图表配置
    columns = filtered_df.columns.tolist()
    numeric_cols = filtered_df.select_dtypes(include=['number']).columns.tolist()
    object_cols = filtered_df.select_dtypes(include=['object']).columns.tolist()

    # 3. 侧边栏：布局管理与图表操作
    st.sidebar.header("⚙️ 看板操作台")
    
    # 导出布局
    if st.session_state.charts:
        json_str = json.dumps(st.session_state.charts, ensure_ascii=False)
        st.sidebar.download_button(
            label="⬇️ 导出当前布局 (JSON)",
            data=json_str,
            file_name="my_dashboard_layout.json",
            mime="application/json"
        )
    
    # 导入布局
    uploaded_layout = st.sidebar.file_uploader("⬆️ 导入布局文件 (JSON)", type=["json"])
    if uploaded_layout is not None:
        try:
            st.session_state.charts = json.load(uploaded_layout)
            st.sidebar.success("布局已成功加载！")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"布局文件解析失败: {e}")
            
    st.sidebar.markdown("---")
    
    # 增加图表按钮
    if st.sidebar.button("➕ 添加新图表"):
        # 默认选择第一个分类列作为X轴，第一个数值列作为Y轴
        default_x = object_cols[0] if object_cols else (columns[0] if columns else None)
        default_y = numeric_cols[0] if numeric_cols else None
        
        st.session_state.charts.append({
            "chart_type": "柱状图",
            "x_axis": default_x,
            "y_axis": default_y,
            "width": 6  # 默认宽度（Streamlit列宽最大为12，6即占一半）
        })
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.info("💡 提示：在下方独立配置每个图表的参数和宽度。")

    # 4. 自由布局画布区域 (使用原生 st.columns 实现稳健的网格布局)
    if st.session_state.charts:
        # 将图表按每行2个（宽度为6）或根据用户设置进行排版
        # 这里为了展示自由宽度，我们动态计算行
        row_charts = []
        current_row_width = 0
        
        for i, chart_config in enumerate(st.session_state.charts):
            # 侧边栏独立配置每个图表
            with st.sidebar.expander(f"⚙️ 配置图表 {i+1}", expanded=False):
                chart_config["chart_type"] = st.selectbox(
                    "图表类型", ["柱状图", "折线图", "散点图", "饼图", "箱线图", "面积图"], 
                    key=f"type_{i}"
                )
                
                # 饼图比较特殊，它的数值是 values，分类是 names
                if chart_config["chart_type"] == "饼图":
                    chart_config["x_axis"] = st.selectbox("分类字段 (Names)", object_cols + numeric_cols, key=f"x_{i}")
                    chart_config["y_axis"] = st.selectbox("数值字段 (Values)", numeric_cols, key=f"y_{i}")
                else:
                    chart_config["x_axis"] = st.selectbox("X 轴 (维度)", columns, key=f"x_{i}")
                    chart_config["y_axis"] = st.selectbox("Y 轴 (数值)", numeric_cols, key=f"y_{i}")
                
                # 调节图表宽度 (1-12)
                chart_config["width"] = st.slider("图表宽度 (1-12)", 1, 12, chart_config["width"], key=f"w_{i}")
                
                if st.button("🗑️ 删除此图表", key=f"del_{i}"):
                    st.session_state.charts.pop(i)
                    st.rerun()

            # 生成实际的 Plotly 图表对象，存入列表等待排版
            try:
                fig = None
                if chart_config["chart_type"] == "柱状图":
                    fig = px.bar(filtered_df, x=chart_config["x_axis"], y=chart_config["y_axis"])
                elif chart_config["chart_type"] == "折线图":
                    fig = px.line(filtered_df, x=chart_config["x_axis"], y=chart_config["y_axis"])
                elif chart_config["chart_type"] == "散点图":
                    fig = px.scatter(filtered_df, x=chart_config["x_axis"], y=chart_config["y_axis"])
                elif chart_config["chart_type"] == "饼图":
                    fig = px.pie(filtered_df, names=chart_config["x_axis"], values=chart_config["y_axis"])
                elif chart_config["chart_type"] == "箱线图":
                    fig = px.box(filtered_df, x=chart_config["x_axis"], y=chart_config["y_axis"])
                elif chart_config["chart_type"] == "面积图":
                    fig = px.area(filtered_df, x=chart_config["x_axis"], y=chart_config["y_axis"])
                
                if fig is not None:
                    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
                    # 将 plotly 图表存入待渲染列表，并带上宽度属性
                    row_charts.append({"width": chart_config["width"], "chart": st.plotly_chart(fig, use_container_width=True, key=f"plot_{i}")})
            except Exception as e:
                row_charts.append({"width": 12, "chart": st.error(f"⚠️ 图表 {i+1} 生成出错: {e}")})

        # 简单的自动换行排版逻辑
        st.subheader("🎨 看板展示区")
        i = 0
        while i < len(row_charts):
            # 尝试填满一行（总宽度不超过12）
            row_width = 0
            row_items = []
            # 临时指针，用于预读取这一行能放下哪些图表
            temp_i = i
            while temp_i < len(row_charts) and (row_width + row_charts[temp_i]['width'] <= 12):
                row_width += row_charts[temp_i]['width']
                row_items.append(row_charts[temp_i]['chart'])
                temp_i += 1
            
            # 如果这一行一个都放不下（比如宽度设置成了13，虽然滑块限制了12，但做健壮性处理），强制放一个
            if not row_items and i < len(row_charts):
                row_items.append(row_charts[i]['chart'])
                i += 1
            else:
                i = temp_i
            
            # 使用 st.columns 渲染这一行的图表
            if row_items:
                # 计算每个图表在这一行中占据的比例
                col_specs = [item['width'] for item in row_charts[i-len(row_items):i]] if i > 0 else [row_charts[0]['width']]
                # 重新根据实际的 row_items 数量生成 columns
                cols = st.columns([item['width'] for item in [row_charts[j] for j in range(i-len(row_items), i)]])
                for idx, col in enumerate(cols):
                    with col:
                        # 这里其实已经渲染过了，st.columns 主要是做布局容器
                        # 由于 st.plotly_chart 已经在上面执行并返回了 None，
                        # 真正的布局技巧是：在生成图表时就直接放入 with col 环境中。
                        # 为了代码简洁且不出错，我们采用更直接的“即时渲染布局”：
                        pass 
        
        # --- 修正：采用更直观的即时渲染布局 ---
        st.subheader("🎨 看板展示区")
        i = 0
        while i < len(st.session_state.charts):
            # 重新计算每一行
            current_row_width = 0
            row_chart_configs = []
            
            # 预读取这一行能放下的图表
            temp_i = i
            while temp_i < len(st.session_state.charts):
                w = st.session_state.charts[temp_i]['width']
                if current_row_width + w <= 12:
                    row_chart_configs.append(st.session_state.charts[temp_i])
                    current_row_width += w
                    temp_i += 1
                else:
                    break
            
            # 创建这一行的列
            if row_chart_configs:
                cols = st.columns([cfg['width'] for cfg in row_chart_configs])
                for idx, cfg in enumerate(row_chart_configs):
                    with cols[idx]:
                        try:
                            fig = None
                            if cfg["chart_type"] == "柱状图":
                                fig = px.bar(filtered_df, x=cfg["x_axis"], y=cfg["y_axis"])
                            elif cfg["chart_type"] == "折线图":
                                fig = px.line(filtered_df, x=cfg["x_axis"], y=cfg["y_axis"])
                            elif cfg["chart_type"] == "散点图":
                                fig = px.scatter(filtered_df, x=cfg["x_axis"], y=cfg["y_axis"])
                            elif cfg["chart_type"] == "饼图":
                                fig = px.pie(filtered_df, names=cfg["x_axis"], values=cfg["y_axis"])
                            elif cfg["chart_type"] == "箱线图":
                                fig = px.box(filtered_df, x=cfg["x_axis"], y=cfg["y_axis"])
                            elif cfg["chart_type"] == "面积图":
                                fig = px.area(filtered_df, x=cfg["x_axis"], y=cfg["y_axis"])
                            
                            if fig:
                                fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
                                st.plotly_chart(fig, use_container_width=True, key=f"final_plot_{i}")
                        except Exception as e:
                            st.error(f"图表出错: {e}")
                    i += 1

    else:
        st.info("👈 请在左侧点击【添加新图表】开始构建你的看板。")

else:
    st.info("👈 请先上传 Excel 文件开始分析。")