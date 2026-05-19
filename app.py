import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import io

# 页面配置：宽屏模式，让图表展示更大气
st.set_page_config(page_title="高级交互式数据看板", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Excel 高级交互式数据看板")

# 初始化 Session State
if "charts" not in st.session_state:
    st.session_state.charts = []
if "filters" not in st.session_state:
    st.session_state.filters = []

# ============================
# 页面整体布局：左中右三栏结构
# ============================
col_left_sidebar, col_main, col_right_sidebar = st.columns([2.5, 8, 2.5])

# ============================
# 1. 左侧主操作台
# ============================
with col_left_sidebar:
    st.header("⚙️ 看板操作台")
    
    # 1.1 点击展开配置说明
    with st.expander("📖 点击展开配置说明", expanded=False):
        st.markdown("""
**1. 数据筛选**
* 在页面主体顶部直接进行全局数据过滤。
**2. 图表配置**
* 点击“添加新图表”生成空白卡片。
* 在图表下方的配置栏中，自由选择图表类型、字段及数值格式。
* 拖拽“图表宽度”滑块（1-12）调节卡片大小。
**3. 布局保存**
* 点击“导出当前看板配置”保存为 JSON 文件。
* 下次上传 Excel 并导入该 JSON 文件，即可一键还原！
""")

    st.divider()

    # 1.2 上传文件入口
    st.subheader("📂 数据源")
    uploaded_file = st.file_uploader("请上传 Excel 文件 (.xlsx)", type=["xlsx"], label_visibility="collapsed")

    st.divider()

    # 1.3 添加新图表
    st.subheader("🎨 图表管理")
    if st.button("➕ 添加新图表", use_container_width=True, type="primary"):
        # 获取当前数据的字段，防止报错
        init_x = st.session_state.get('df_columns', [None])[0] if st.session_state.get('df_columns') else None
        init_y = st.session_state.get('df_numeric', [None])[0] if st.session_state.get('df_numeric') else None
        init_color = st.session_state.get('df_object', [None])[0] if st.session_state.get('df_object') else None
        
        st.session_state.charts.append({
            "chart_type": "柱状图", "x_axis": init_x,
            "y_axis": init_y, "width": 12, 
            "y_axis_2": init_y,
            "size_col": init_y,
            "lat_col": None, "lon_col": None,
            "color_col": init_color,
            # 👇 新增字段默认值
            "show_values": False,
            "value_format": ".2f",
            "y_axis_title_format": ""
        })
        st.rerun()

    st.divider()

    # 1.4 导入导出看板配置
    st.subheader("💾 配置存取")
    export_data = {"charts": st.session_state.charts, "filters": st.session_state.filters}
    if st.session_state.charts or st.session_state.filters:
        json_str = json.dumps(export_data, ensure_ascii=False, default=str)
        st.download_button(label="⬇️ 导出看板配置 (JSON)", data=json_str, file_name="my_dashboard_config.json", mime="application/json", use_container_width=True)
    
    uploaded_config = st.file_uploader("⬆️ 导入看板配置 (JSON)", type=["json"], label_visibility="collapsed")
    if uploaded_config is not None:
        try:
            import_data = json.load(uploaded_config)
            st.session_state.charts = import_data.get("charts", [])
            st.session_state.filters = import_data.get("filters", [])
            st.success("✅ 配置加载成功！")
            st.rerun()
        except Exception as e:
            st.error(f"配置文件解析失败: {e}")

# ============================
# 2. 右侧辅助功能区
# ============================
with col_right_sidebar:
    st.header("🔧 辅助功能区")
    
    # 2.1 合并分析 Sheet
    st.subheader("📑 多Sheet合并")
    if uploaded_file is not None:
        try:
            # 只有在文件上传后，才读取 Sheet 信息
            if 'all_sheets_cache' not in st.session_state or st.session_state.get('current_file_name') != uploaded_file.name:
                all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
                st.session_state['all_sheets_cache'] = all_sheets
                st.session_state['current_file_name'] = uploaded_file.name
            
            all_sheets = st.session_state['all_sheets_cache']
            sheet_names = list(all_sheets.keys())
            
            selected_sheets = st.multiselect(
                "选择要合并的表格", 
                sheet_names, 
                default=sheet_names,
                label_visibility="collapsed"
            )
            
            if not selected_sheets:
                st.warning("⚠️ 请至少选择一个 Sheet")
                st.stop()
            
            # 合并数据
            df_list = [all_sheets[sheet] for sheet in selected_sheets]
            df = pd.concat(df_list, ignore_index=True)
            
            # 将字段信息存入 session_state，供左侧初始化图表使用
            st.session_state['df_columns'] = df.columns.tolist()
            st.session_state['df_numeric'] = df.select_dtypes(include=['number']).columns.tolist()
            st.session_state['df_object'] = df.select_dtypes(include=['object']).columns.tolist()

            st.caption(f"✅ 已合并 {len(selected_sheets)} 个表，共 {len(df)} 条数据")

        except Exception as e:
            st.error(f"读取文件失败: {e}")
            st.stop()
    else:
        st.info("请先在左侧上传 Excel 文件")
        df = None

    st.divider()

    # 2.2 导出合并后的数据
    st.subheader("💾 导出数据")
    if uploaded_file is not None and 'df' in locals():
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='合并数据')
        processed_data = output.getvalue()
        st.download_button(
            label="📥 下载合并后的 Excel",
            data=processed_data,
            file_name="merged_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

# ============================
# 3. 页面主体展示区
# ============================
with col_main:
    if uploaded_file is not None and 'df' in locals():
        
        # 全局提取字段信息，防止后续作用域报错
        all_cols = df.columns.tolist()
        text_cols = df.select_dtypes(include=['object']).columns.tolist()
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        date_cols = df.select_dtypes(include=['datetime']).columns.tolist()
        
        # 3.1 顶部数据筛选器（平铺展示）
        with st.container(border=True):
            st.subheader("🔍 全局数据筛选")
            
            # 管理筛选器
            if st.button("➕ 添加筛选条件", key="add_filter_main"):
                st.session_state.filters.append({"col_name": None, "filter_type": None})
                st.rerun()
                
            # 渲染筛选器
            filtered_df = df.copy()
            filter_cols = st.columns(3) # 每行放3个筛选器
            
            for i, f_config in enumerate(st.session_state.filters):
                with filter_cols[i % 3]: 
                    with st.container(border=True):
                        current_col_idx = 0
                        if f_config["col_name"] is not None and f_config["col_name"] in all_cols:
                            current_col_idx = all_cols.index(f_config["col_name"]) + 1
                            
                        selected_col = st.selectbox("选择字段", [None] + all_cols, 
                            index=current_col_idx,
                            key=f"sel_col_{i}", label_visibility="collapsed")
                        f_config["col_name"] = selected_col
                        
                        if selected_col:
                            if selected_col in text_cols:
                                unique_values = df[selected_col].dropna().unique()
                                selected_values = st.multiselect(f"选择 {selected_col} 的值", unique_values, default=list(unique_values), key=f"filter_val_{i}", label_visibility="collapsed")
                                filtered_df = filtered_df[filtered_df[selected_col].isin(selected_values)]
                            elif selected_col in num_cols:
                                min_val, max_val = float(df[selected_col].min()), float(df[selected_col].max())
                                if min_val != max_val:
                                    range_val = st.slider(f"选择 {selected_col} 范围", min_val, max_val, (min_val, max_val), key=f"filter_val_{i}", label_visibility="collapsed")
                                    filtered_df = filtered_df[(filtered_df[selected_col] >= range_val[0]) & (filtered_df[selected_col] <= range_val[1])]
                            elif selected_col in date_cols:
                                min_date, max_date = df[selected_col].min().date(), df[selected_col].max().date()
                                date_range = st.date_input(f"选择 {selected_col} 范围", [min_date, max_date], key=f"filter_val_{i}", label_visibility="collapsed")
                                if len(date_range) == 2:
                                    filtered_df = filtered_df[(filtered_df[selected_col] >= pd.to_datetime(date_range[0])) & (filtered_df[selected_col] <= pd.to_datetime(date_range[1]))]
                        
                        if st.button("🗑️", key=f"del_filter_{i}"):
                            st.session_state.filters.pop(i)
                            st.rerun()
        
        st.success(f"✅ 筛选完成，当前展示 {len(filtered_df)} 条数据")
        st.divider()

        # 3.2 图表展示区（配置与展示相连）
        st.subheader("📈 图表展示区")
        if not st.session_state.charts:
            st.info("👈 请在左侧操作台点击【添加新图表】开始构建你的看板。")
        
        # 提取筛选后数据的字段，用于图表配置下拉框
        f_columns = filtered_df.columns.tolist()
        f_numeric_cols = filtered_df.select_dtypes(include=['number']).columns.tolist()
        f_object_cols = filtered_df.select_dtypes(include=['object']).columns.tolist()
        f_lat_cols = [col for col in f_columns if 'lat' in col.lower() or '纬度' in col]
        f_lon_cols = [col for col in f_columns if 'lon' in col.lower() or 'long' in col.lower() or '经度' in col]

        # 辅助函数：安全获取下拉框默认索引
        def get_safe_index(val, options):
            if val in options: return options.index(val)
            return 0

        i = 0
        while i < len(st.session_state.charts):
            current_row_width = 0
            row_chart_configs = []
            temp_i = i
            # 计算当前行能放下哪些图表
            while temp_i < len(st.session_state.charts):
                w = st.session_state.charts[temp_i]['width']
                if current_row_width + w <= 12:
                    row_chart_configs.append(st.session_state.charts[temp_i])
                    current_row_width += w
                    temp_i += 1
                else:
                    break
            
            if row_chart_configs:
                # 渲染当前行的图表
                cols = st.columns([cfg['width'] for cfg in row_chart_configs])
                for idx, cfg in enumerate(row_chart_configs):
                    with cols[idx]:
                        # 配置与展示相连：直接在图表上方或内部提供配置
                        with st.expander(f"⚙️ 配置图表 {i+1}: {cfg['chart_type']}", expanded=False):
                            chart_types = ["柱状图", "折线图", "散点图", "饼图", "箱线图", "面积图", 
                                           "气泡图", "百分比柱状图", "线柱混搭图", "色块地图", "气泡地图"]
                            cfg["chart_type"] = st.selectbox("图表类型", chart_types, key=f"type_{i}")
                            
                            # 动态字段配置
                            if cfg["chart_type"] in ["色块地图", "气泡地图"]:
                                cfg["lat_col"] = st.selectbox("纬度列 (lat)", f_columns, index=get_safe_index(cfg["lat_col"], f_columns), key=f"lat_{i}")
                                cfg["lon_col"] = st.selectbox("经度列 (lon)", f_columns, index=get_safe_index(cfg["lon_col"], f_columns), key=f"lon_{i}")
                                cfg["color_col"] = st.selectbox("数值/颜色列", f_numeric_cols, index=get_safe_index(cfg["color_col"], f_numeric_cols), key=f"color_{i}")
                            elif cfg["chart_type"] == "线柱混搭图":
                                cfg["x_axis"] = st.selectbox("X 轴 (维度)", f_columns, index=get_safe_index(cfg["x_axis"], f_columns), key=f"x_{i}")
                                cfg["y_axis"] = st.selectbox("柱状图数值 (Y1)", f_numeric_cols, index=get_safe_index(cfg["y_axis"], f_numeric_cols), key=f"y1_{i}")
                                cfg["y_axis_2"] = st.selectbox("折线图数值 (Y2)", f_numeric_cols, index=get_safe_index(cfg["y_axis_2"], f_numeric_cols), key=f"y2_{i}")
                            elif cfg["chart_type"] == "气泡图":
                                cfg["x_axis"] = st.selectbox("X 轴", f_columns, index=get_safe_index(cfg["x_axis"], f_columns), key=f"x_{i}")
                                cfg["y_axis"] = st.selectbox("Y 轴", f_numeric_cols, index=get_safe_index(cfg["y_axis"], f_numeric_cols), key=f"y_{i}")
                                cfg["size_col"] = st.selectbox("气泡大小", f_numeric_cols, index=get_safe_index(cfg["size_col"], f_numeric_cols), key=f"size_{i}")
                                color_options = [None] + f_columns
                                cfg["color_col"] = st.selectbox("气泡颜色(可选)", color_options, index=get_safe_index(cfg["color_col"], color_options), key=f"col_{i}")
                            elif cfg["chart_type"] == "百分比柱状图":
                                x_options = f_object_cols or f_columns
                                cfg["x_axis"] = st.selectbox("X 轴 (分类)", x_options, index=get_safe_index(cfg["x_axis"], x_options), key=f"x_{i}")
                                cfg["color_col"] = st.selectbox("分组维度 (堆积)", f_object_cols, index=get_safe_index(cfg["color_col"], f_object_cols), key=f"group_{i}")
                                cfg["y_axis"] = st.selectbox("数值列", f_numeric_cols, index=get_safe_index(cfg["y_axis"], f_numeric_cols), key=f"y_{i}")
                            else:
                                if cfg["chart_type"] == "饼图":
                                    cfg["x_axis"] = st.selectbox("分类字段 (Names)", f_columns, index=get_safe_index(cfg["x_axis"], f_columns), key=f"x_{i}")
                                    cfg["y_axis"] = st.selectbox("数值字段 (Values)", f_numeric_cols, index=get_safe_index(cfg["y_axis"], f_numeric_cols), key=f"y_{i}")
                                else:
                                    cfg["x_axis"] = st.selectbox("X 轴 (维度)", f_columns, index=get_safe_index(cfg["x_axis"], f_columns), key=f"x_{i}")
                                    cfg["y_axis"] = st.selectbox("Y 轴 (数值)", f_numeric_cols, index=get_safe_index(cfg["y_axis"], f_numeric_cols), key=f"y_{i}")
                            
                            cfg["width"] = st.slider("图表宽度 (1-12)", 1, 12, cfg["width"], key=f"w_{i}")

                            # 👇 新增：数值与坐标轴格式配置
                            st.markdown("**🔢 数值与坐标轴格式**")
                            show_values = st.checkbox("展示数值标签", value=cfg.get("show_values", False), key=f"show_val_{i}")
                            cfg["show_values"] = show_values
                            
                            value_format = st.text_input("数值格式 (如 .2f, $,)", value=cfg.get("value_format", ".2f"), key=f"val_fmt_{i}")
                            cfg["value_format"] = value_format
                            
                            y_axis_title_format = st.text_input("Y轴标题格式 (如 销售额(万元))", value=cfg.get("y_axis_title_format", ""), key=f"y_title_fmt_{i}")
                            cfg["y_axis_title_format"] = y_axis_title_format

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
                                
                                # 👇 应用数值标签与坐标轴格式
                                # 1. 配置 Y 轴标题
                                if cfg.get("y_axis_title_format"):
                                    fig.update_layout(yaxis_title=cfg["y_axis_title_format"])
                                
                                # 2. 配置数值标签展示
                                if cfg.get("show_values"):
                                    if ct == "饼图":
                                        fig.update_traces(texttemplate=f"%{{value:{cfg.get('value_format', '.2f')}}}", textposition="outside")
                                    elif ct in ["柱状图", "折线图", "面积图"]:
                                        fig.update_traces(texttemplate=f"%{{y
