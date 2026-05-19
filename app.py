import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import io

# 页面配置
st.set_page_config(page_title="高级交互式数据看板", layout="wide")
st.title("📊 Excel 高级交互式数据看板")

# 初始化 Session State
if "charts" not in st.session_state:
    st.session_state.charts = []
if "filters" not in st.session_state:
    st.session_state.filters = []

# 1. 上传文件与多Sheet合并读取区域
uploaded_file = st.file_uploader("请上传 Excel 文件 (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        # 一次性读取 Excel 中的所有 Sheet
        all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
        sheet_names = list(all_sheets.keys())
        
        # 多选框自由选择需要合并分析的 Sheet（默认全选）
        selected_sheets = st.multiselect(
            "📑 请选择要合并分析的 Sheet 表格（支持多选）", 
            sheet_names, 
            default=sheet_names
        )
        
        if not selected_sheets:
            st.warning("⚠️ 请至少选择一个 Sheet 进行分析！")
            st.stop()
        
        # 将选中的多个 Sheet 合并成一个巨大的 DataFrame
        df_list = [all_sheets[sheet] for sheet in selected_sheets]
        df = pd.concat(df_list, ignore_index=True)
        
        st.info(f"✅ 已成功合并 {len(selected_sheets)} 个 Sheet，共计 {len(df)} 条数据。")
        
    except Exception as e:
        st.error(f"读取或合并 Excel 文件失败，请检查文件格式: {e}")
        st.stop()
    
    # 2. 动态数据筛选区域
    with st.expander("🔍 点击展开/收起数据筛选面板", expanded=True):
        st.sidebar.header("⚙️ 看板操作台")
        
        # --- 侧边栏配置说明（折叠式） ---
        st.sidebar.markdown("""
<details>
<summary style="cursor: pointer; font-weight: bold;">📖 点击展开配置说明</summary>

**1. 数据筛选**
* 点击“添加数据筛选器”按钮。
* 在弹出的选项中，自主选择需要过滤的字段。

**2. 图表配置**
* 点击“添加新图表”生成空白卡片。
* 在下方展开的配置栏中，自由选择图表类型。
* 拖拽“图表宽度”滑块（1-12）调节卡片大小。

**3. 布局保存**
* 点击“导出当前看板配置”保存为 JSON 文件。
* 下次上传 Excel 并导入该 JSON 文件，即可一键还原！
</details>
""", unsafe_allow_html=True)
        st.sidebar.markdown("---")
        # --- 侧边栏说明结束 ---

        if st.sidebar.button("➕ 添加数据筛选器"):
            st.session_state.filters.append({"col_name": None, "filter_type": None})
            st.rerun()

        filtered_df = df.copy()
        all_cols = df.columns.tolist()
        text_cols = df.select_dtypes(include=['object']).columns.tolist()
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        date_cols = df.select_dtypes(include=['datetime']).columns.tolist()
        
        for i, f_config in enumerate(st.session_state.filters):
            with st.sidebar.expander(f"🔎 筛选器设置 {i+1}", expanded=True):
                # 修复：安全获取当前字段在列表中的索引，防止字段变更导致报错
                current_col_idx = 0
                if f_config["col_name"] is not None and f_config["col_name"] in all_cols:
                    current_col_idx = all_cols.index(f_config["col_name"]) + 1
                
                selected_col = st.selectbox("选择关联字段", [None] + all_cols, 
                    index=current_col_idx, key=f"sel_col_{i}")
                f_config["col_name"] = selected_col
                
                if selected_col:
                    if selected_col in text_cols:
                        f_config["filter_type"] = "text"
                        unique_values = df[selected_col].dropna().unique()
                        selected_values = st.multiselect(f"选择 {selected_col} 的值", unique_values, default=unique_values, key=f"filter_val_{i}")
                        filtered_df = filtered_df[filtered_df[selected_col].isin(selected_values)]
                    elif selected_col in num_cols:
                        f_config["filter_type"] = "number"
                        min_val, max_val = float(df[selected_col].min()), float(df[selected_col].max())
                        if min_val != max_val:
                            range_val = st.slider(f"选择 {selected_col} 范围", min_val, max_val, (min_val, max_val), key=f"filter_val_{i}")
                            filtered_df = filtered_df[(filtered_df[selected_col] >= range_val[0]) & (filtered_df[selected_col] <= range_val[1])]
                    elif selected_col in date_cols:
                        f_config["filter_type"] = "date"
                        min_date, max_date = df[selected_col].min().date(), df[selected_col].max().date()
                        date_range = st.date_input(f"选择 {selected_col} 范围", [min_date, max_date], key=f"filter_val_{i}")
                        if len(date_range) == 2:
                            filtered_df = filtered_df[(filtered_df[selected_col] >= pd.to_datetime(date_range[0])) & (filtered_df[selected_col] <= pd.to_datetime(date_range[1]))]
                
                if st.button("🗑️ 删除此筛选器", key=f"del_filter_{i}"):
                    st.session_state.filters.pop(i)
                    st.rerun()
        
        st.success(f"✅ 筛选完成，当前展示 {len(filtered_df)} 条数据")

    # 获取筛选后数据的各类字段
    columns = filtered_df.columns.tolist()
    numeric_cols = filtered_df.select_dtypes(include=['number']).columns.tolist()
    object_cols = filtered_df.select_dtypes(include=['object']).columns.tolist()
    # 自动寻找经纬度列（用于地图）
    lat_cols = [col for col in columns if 'lat' in col.lower() or '纬度' in col]
    lon_cols = [col for col in columns if 'lon' in col.lower() or 'long' in col.lower() or '经度' in col]

    # 3. 侧边栏：布局管理与图表操作
    st.sidebar.markdown("---")
    
    # 导出/导入看板配置
    export_data = {"charts": st.session_state.charts, "filters": st.session_state.filters}
    if st.session_state.charts or st.session_state.filters:
        json_str = json.dumps(export_data, ensure_ascii=False, default=str)
        st.sidebar.download_button(label="⬇️ 导出当前看板配置 (JSON)", data=json_str, file_name="my_dashboard_config.json", mime="application/json")
    
    uploaded_config = st.sidebar.file_uploader("⬆️ 导入看板配置 (JSON)", type=["json"])
    if uploaded_config is not None:
        try:
            import_data = json.load(uploaded_config)
            st.session_state.charts = import_data.get("charts", [])
            st.session_state.filters = import_data.get("filters", [])
            st.sidebar.success("配置加载成功！")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"配置文件解析失败: {e}")
            
    st.sidebar.markdown("---")
    
    if st.sidebar.button("➕ 添加新图表"):
        st.session_state.charts.append({
            "chart_type": "柱状图", 
            "x_axis": (object_cols[0] if object_cols else columns[0]) if columns else None,
            "y_axis": numeric_cols[0] if numeric_cols else None, 
            "width": 6,
            "y_axis_2": numeric_cols[1] if len(numeric_cols) > 1 else None,
            "size_col": numeric_cols[0] if numeric_cols else None,
            "lat_col": lat_cols[0] if lat_cols else None,
            "lon_col": lon_cols[0] if lon_cols else None,
            "color_col": (object_cols[0] if object_cols else numeric_cols[0]) if (object_cols or numeric_cols) else None
        })
        st.rerun()

    st.sidebar.info("💡 提示：混搭图、气泡图、地图需要配置特定的字段。")

    # 4. 自由布局画布区域
    if st.session_state.charts:
        st.subheader("🎨 看板展示区")
        i = 0
        while i < len(st.session_state.charts):
            current_row_width = 0
            row_chart_configs = []
            temp_i = i
            while temp_i < len(st.session_state.charts):
                w = st.session_state.charts[temp_i]['width']
                if current_row_width + w <= 12:
                    row_chart_configs.append(st.session_state.charts[temp_i])
                    current_row_width += w
                    temp_i += 1
                else:
                    break
            
            if row_chart_configs:
                cols = st.columns([cfg['width'] for cfg in row_chart_configs])
                for idx, cfg in enumerate(row_chart_configs):
                    with cols[idx]:
                        with st.expander(f"⚙️ 配置图表 {i+1}", expanded=False):
                            # 基础配置
                            chart_types = ["柱状图", "折线图", "散点图", "饼图", "箱线图", "面积图", 
                                           "气泡图", "百分比柱状图", "线柱混搭图", "色块地图", "气泡地图"]
                            cfg["chart_type"] = st.selectbox("图表类型", chart_types, key=f"type_{i}")
                            
                            # 辅助函数：安全获取下拉框默认索引
                            def get_safe_index(val, options):
                                if val in options:
                                    return options.index(val)
                                return 0
                            
                            # 根据图表类型动态显示需要配置的字段
                            if cfg["chart_type"] in ["色块地图", "气泡地图"]:
                                cfg["lat_col"] = st.selectbox("纬度列 (lat)", columns, index=get_safe_index(cfg["lat_col"], columns), key=f"lat_{i}")
                                cfg["lon_col"] = st.selectbox("经度列 (lon)", columns, index=get_safe_index(cfg["lon_col"], columns), key=f"lon_{i}")
                                cfg["color_col"] = st.selectbox("数值/颜色列", numeric_cols, index=get_safe_index(cfg["color_col"], numeric_cols), key=f"color_{i}")
                            elif cfg["chart_type"] == "线柱混搭图":
                                cfg["x_axis"] = st.selectbox("X 轴 (维度)", columns, index=get_safe_index(cfg["x_axis"], columns), key=f"x_{i}")
                                cfg["y_axis"] = st.selectbox("柱状图数值 (Y1)", numeric_cols, index=get_safe_index(cfg["y_axis"], numeric_cols), key=f"y1_{i}")
                                cfg["y_axis_2"] = st.selectbox("折线图数值 (Y2)", numeric_cols, index=get_safe_index(cfg["y_axis_2"], numeric_cols), key=f"y2_{i}")
                            elif cfg["chart_type"] == "气泡图":
                                cfg["x_axis"] = st.selectbox("X 轴", columns, index=get_safe_index(cfg["x_axis"], columns), key=f"x_{i}")
                                cfg["y_axis"] = st.selectbox("Y 轴", numeric_cols, index=get_safe_index(cfg["y_axis"], numeric_cols), key=f"y_{i}")
                                cfg["size_col"] = st.selectbox("气泡大小", numeric_cols, index=get_safe_index(cfg["size_col"], numeric_cols), key=f"size_{i}")
                                color_options = [None] + columns
                                cfg["color_col"] = st.selectbox("气泡颜色(可选)", color_options, index=get_safe_index(cfg["color_col"], color_options), key=f"col_{i}")
                            elif cfg["chart_type"] == "百分比柱状图":
                                x_options = object_cols or columns
                                cfg["x_axis"] = st.selectbox("X 轴 (分类)", x_options, index=get_safe_index(cfg["x_axis"], x_options), key=f"x_{i}")
                                cfg["color_col"] = st.selectbox("分组维度 (堆积)", object_cols, index=get_safe_index(cfg["color_col"], object_cols), key=f"group_{i}")
                                cfg["y_axis"] = st.selectbox("数值列", numeric_cols, index=get_safe_index(cfg["y_axis"], numeric_cols), key=f"y_{i}")
                            else:
                                # 常规图表配置
                                if cfg["chart_type"] == "饼图":
                                    cfg["x_axis"] = st.selectbox("分类字段 (Names)", columns, index=get_safe_index(cfg["x_axis"], columns), key=f"x_{i}")
                                    cfg["y_axis"] = st.selectbox("数值字段 (Values)", numeric_cols, index=get_safe_index(cfg["y_axis"], numeric_cols), key=f"y_{i}")
                                else:
                                    cfg["x_axis"] = st.selectbox("X 轴 (维度)", columns, index=get_safe_index(cfg["x_axis"], columns), key=f"x_{i}")
                                    cfg["y_axis"] = st.selectbox("Y 轴 (数值)", numeric_cols, index=get_safe_index(cfg["y_axis"], numeric_cols), key=f"y_{i}")
                            
                            cfg["width"] = st.slider("图表宽度 (1-12)", 1, 12, cfg["width"], key=f"w_{i}")
                            if st.button("🗑️ 删除此图表", key=f"del_{i}"):
                                st.session_state.charts.pop(i)
                                st.rerun()

                        # 渲染图表
                        try:
                            fig = None
                            ct = cfg["chart_type"]
                            if ct == "柱状图": fig = px.bar(filtered_df, x=cfg["x_axis"], y=cfg["y_axis"])
                            elif ct == "折线图": fig = px.line(filtered_df, x=cfg["x_axis"], y=cfg["y_axis"])
                            elif ct == "散点图": fig = px.scatter(filtered_df, x=cfg["x_axis"], y=cfg["y_axis"])
                            elif ct == "饼图": fig = px.pie(filtered_df, names=cfg["x_axis"], values=cfg["y_axis"])
                            elif ct == "箱线图": fig = px.box(filtered_df, x=cfg["x_axis"], y=cfg["y_axis"])
                            elif ct == "面积图": fig = px.area(filtered_df, x=cfg["x_axis"], y=cfg["y_axis"])
                            # --- 新增的高级图表 ---
                            elif ct == "气泡图":
                                fig = px.scatter(filtered_df, x=cfg["x_axis"], y=cfg["y_axis"], size=cfg["size_col"], color=cfg["color_col"], size_max=60)
                            elif ct == "百分比柱状图":
                                pivot_df = filtered_df.groupby([cfg["x_axis"], cfg["color_col"]])[cfg["y_axis"]].sum().reset_index()
                                fig = px.bar(pivot_df, x=cfg["x_axis"], y=cfg["y_axis"], color=cfg["color_col"], barmode='relative', text_auto='.2s')
                                fig.update_layout(yaxis_tickformat='%') 
                            elif ct == "线柱混搭图":
                                fig = go.Figure()
                                fig.add_trace(go.Bar(x=filtered_df[cfg["x_axis"]], y=filtered_df[cfg["y_axis"]], name=cfg["y_axis"]))
                                fig.add_trace(go.Scatter(x=filtered_df[cfg["x_axis"]], y=filtered_df[cfg["y_axis_2"]], name=cfg["y_axis_2"], mode='lines+markers', yaxis='y2'))
                                fig.update_layout(yaxis2=dict(title=cfg["y_axis_2"], overlaying='y', side='right'))
                            elif ct == "色块地图":
                                fig = px.density_mapbox(filtered_df, lat=cfg["lat_col"], lon=cfg["lon_col"], z=cfg["color_col"], radius=10, center=dict(lat=filtered_df[cfg["lat_col"]].mean(), lon=filtered_df[cfg["lon_col"]].mean()), zoom=5, mapbox_style="carto-positron")
                            elif ct == "气泡地图":
                                fig = px.scatter_mapbox(filtered_df, lat=cfg["lat_col"], lon=cfg["lon_col"], size=cfg["color_col"], hover_name=cfg["x_axis"], size_max=30, zoom=3)
                                fig.update_layout(mapbox_style="open-street-map")

                            if fig:
                                fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
                                st.plotly_chart(fig, use_container_width=True, key=f"final_plot_{i}")
                        except Exception as e:
                            st.error(f"图表生成出错: {e}")
                    i += 1
    else:
        st.info("👈 请在左侧点击【添加新图表】开始构建你的看板。")

    # ============================
    # 导出合并后的 Excel 数据
    # ============================
    st.divider()
    st.subheader("💾 导出数据")
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='合并数据')
    
    processed_data = output.getvalue()

    st.download_button(
        label="📥 点击下载合并后的 Excel 文件",
        data=processed_data,
        file_name="merged_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # ============================
    # 页面底部：图表配置简介模块
    # ============================
    st.divider()
    with st.expander("📖 图表配置与字段选择指南（点击展开）", expanded=False):
        st.markdown("""
        ### 📊 基础图表配置
        * **柱状图 / 折线图 / 面积图 / 箱线图**：通常需要选择一个**分类字段（X轴）**和一个**数值字段（Y轴）**。
        * **散点图**：需要选择两个**数值字段**，分别作为 X 轴和 Y 轴，用于分析两个变量之间的相关性。
        * **饼图**：需要一个**分类字段（Names）**和一个**数值字段（Values）**，用于展示各部分占总体的比例。
        
        ### ✨ 高级图表配置
        * **气泡图**：在散点图的基础上，额外指定一个**数值字段作为“气泡大小”**，可同时展示三维数据。
        * **百分比柱状图**：需要一个**分类字段（X轴）**、一个**分组维度（堆积颜色）**和一个**数值字段**。系统会自动计算并展示各分组在分类中的占比（%）。
        * **线柱混搭图**：需要一个**分类字段（X轴）**和**两个数值字段**，分别作为左侧Y轴的柱状图和右侧Y轴的折线图，适合对比量级不同的数据。
        
        ### 🗺️ 地图类图表配置（需包含经纬度数据）
        * **色块地图 (热力地图)**：需要指定**纬度列 (lat)**、**经度列 (lon)**以及一个**数值/颜色列**。地图上会根据数值大小生成不同深浅的热力色块。
        * **气泡地图**：需要指定**纬度列 (lat)**、**经度列 (lon)**以及一个**气泡大小列**。地图上会在对应坐标生成大小不一的气泡。
        
        > **💡 提示**：如果你的 Excel 表格中包含“纬度”、“经度”、“lat”、“lon”等字样的列，系统在添加地图时会自动尝试将其设为默认选项。
        """)

else:
    st.info("👈 请先上传 Excel 文件开始分析。")
