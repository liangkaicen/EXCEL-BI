import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import io

# 注入自定义 CSS：压缩顶部空白、调整字体大小、优化侧边栏间距
st.markdown("""
<style>
    /* 1. 大幅压缩页面顶部的空白区域 */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* 2. 主标题字体设为普通小标题的双倍大小 */
    h1 { font-size: 36px !important; margin-bottom: 10px !important; }
    h2 { font-size: 20px !important; margin-top: 10px !important; }
    h3 { font-size: 18px !important; }
    
    /* 3. 全局字体回归默认无衬线，并适当缩小字号 */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        font-size: 14px !important;
    }
    
    /* 4. 侧边栏各模块间距紧凑化 */
    .stSidebar .block-container {
        padding-top: 1rem !important;
    }
    .stSidebar div[data-testid="stVerticalBlock"] > div {
        margin-bottom: 0.5rem !important;
    }
    .stSidebar h2, .stSidebar h3 {
        margin-bottom: 0.3rem !important;
    }
    
    /* 5. 优化普通文本和按钮的紧凑感 */
    p, div, label, span, button {
        font-size: 14px !important;
        line-height: 1.4 !important;
    }
</style>
""", unsafe_allow_html=True)

# 页面配置
st.set_page_config(page_title="高级交互式数据看板", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Excel 高级交互式数据看板")

# 初始化 Session State
if "charts" not in st.session_state:
    st.session_state.charts = []
if "filters" not in st.session_state:
    st.session_state.filters = []

# ============================
# 侧边栏：紧凑化布局
# ============================
with st.sidebar:
    st.header("⚙️ 看板操作台")
    
    # 1. 配置说明（折叠）
    with st.expander("📖 配置说明", expanded=False):
        st.markdown("""
* **数据筛选**：在页面顶部进行全局过滤。
* **图表配置**：点击“添加新图表”，在卡片内配置类型与字段。
* **布局保存**：导出/导入 JSON 文件可一键还原看板！
""")

    st.divider()

    # 2. 数据源上传
    st.subheader("📂 数据源")
    uploaded_file = st.file_uploader("上传 Excel 文件 (.xlsx)", type=["xlsx"], label_visibility="collapsed")

    # 3. 多Sheet合并 & 下载 (紧挨着上传功能)
    if uploaded_file is not None:
        try:
            if 'all_sheets_cache' not in st.session_state or st.session_state.get('current_file_name') != uploaded_file.name:
                all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
                st.session_state['all_sheets_cache'] = all_sheets
                st.session_state['current_file_name'] = uploaded_file.name
            
            all_sheets = st.session_state['all_sheets_cache']
            sheet_names = list(all_sheets.keys())
            
            selected_sheets = st.multiselect("合并分析 Sheet", sheet_names, default=sheet_names)
            
            if not selected_sheets:
                st.warning("⚠️ 请至少选择一个 Sheet")
                st.stop()
            
            df_list = [all_sheets[sheet] for sheet in selected_sheets]
            df = pd.concat(df_list, ignore_index=True)
            
            st.session_state['df_columns'] = df.columns.tolist()
            st.session_state['df_numeric'] = df.select_dtypes(include=['number']).columns.tolist()
            st.session_state['df_object'] = df.select_dtypes(include=['object']).columns.tolist()
            st.caption(f"✅ 已合并 {len(selected_sheets)} 个表，共 {len(df)} 条数据")

            # 导出合并后的数据
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='合并数据')
            processed_data = output.getvalue()
            st.download_button(label="📥 下载合并后的 Excel", data=processed_data, file_name="merged_data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

        except Exception as e:
            st.error(f"读取文件失败: {e}")
            st.stop()
    else:
        st.info("请先上传 Excel 文件")
        df = None

    st.divider()

    # 4. 图表管理
    st.subheader("🎨 图表管理")
    if st.button("➕ 添加新图表", use_container_width=True, type="primary"):
        init_x = st.session_state.get('df_columns', [None])[0] if st.session_state.get('df_columns') else None
        init_y = st.session_state.get('df_numeric', [None])[0] if st.session_state.get('df_numeric') else None
        init_color = st.session_state.get('df_object', [None])[0] if st.session_state.get('df_object') else None
        
        st.session_state.charts.append({
            "chart_type": "柱状图", "x_axis": init_x, "y_axis": init_y, "width": 12, 
            "y_axis_2": init_y, "size_col": init_y, "lat_col": None, "lon_col": None,
            "color_col": init_color, "show_values": False, "value_format": ".2f", "y_axis_title_format": ""
        })
        st.rerun()

    st.divider()

    # 5. 配置存取
    st.subheader("💾 配置存取")
    export_data = {"charts": st.session_state.charts, "filters": st.session_state.filters}
    if st.session_state.charts or st.session_state.filters:
        json_str = json.dumps(export_data, ensure_ascii=False, default=str)
        st.download_button(label="⬇️ 导出看板配置 (JSON)", data=json_str, file_name="my_dashboard_config.json", mime="application/json", use_container_width=True)
    
    uploaded_config = st.file_uploader("⬆️ 导入看板配置", type=["json"], label_visibility="collapsed")
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
# 页面主体展示区 (上半部分：筛选器)
# ============================
if uploaded_file is not None and 'df' in locals():
    all_cols = df.columns.tolist()
    text_cols = df.select_dtypes(include=['object']).columns.tolist()
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    date_cols = df.select_dtypes(include=['datetime']).columns.tolist()
    
    # 1. 顶部数据筛选器
    with st.container(border=True):
        st.subheader("🔍 全局数据筛选")
        if st.button("➕ 添加筛选条件", key="add_filter_main"):
            st.session_state.filters.append({"col_name": None, "filter_type": None})
            st.rerun()
            
        filtered_df = df.copy()
        filter_cols = st.columns(3)
        for i, f_config in enumerate(st.session_state.filters):
            with filter_cols[i % 3]: 
                with st.container(border=True):
                    current_col_idx = 0
                    if f_config["col_name"] is not None and f_config["col_name"] in all_cols:
                        current_col_idx = all_cols.index(f_config["col_name"]) + 1
                    selected_col = st.selectbox("选择字段", [None] + all_cols, index=current_col_idx, key=f"sel_col_{i}", label_visibility="collapsed")
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

    # 2. 图表展示区 (核心逻辑)
    st.subheader("📈 图表展示区")
    if not st.session_state.charts:
        st.info("👈 请在左侧操作台点击【添加新图表】开始构建你的看板。")
    
    f_columns = filtered_df.columns.tolist()
    f_numeric_cols = filtered_df.select_dtypes(include=['number']).columns.tolist()
    f_object_cols = filtered_df.select_dtypes(include=['object']).columns.tolist()

    def get_safe_index(val, options):
        if val in options: return options.index(val)
        return 0

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
                    with st.expander(f"⚙️ 配置图表 {i+1}: {cfg['chart_type']}", expanded=False):
                        chart_types = ["柱状图", "折线图", "散点图", "饼图", "箱线图", "面积图", 
                                       "气泡图", "百分比柱状图", "线柱混搭图", "色块地图", "气泡地图"]
                        cfg["chart_type"] = st.selectbox("图表类型", chart_types, key=f"type_{i}")
                        
                        if cfg["chart_type"] in ["色块地图", "气泡地图"]:
                            f_lat_cols = [col for col in f_columns if 'lat' in col.lower() or '纬度' in col]
                            f_lon_cols = [col for col in f_columns if 'lon' in col.lower() or 'long' in col.lower() or '经度' in col]
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

                        st.markdown("**🔢 数值与坐标轴格式**")
                        show_values = st.checkbox("展示数值标签", value=cfg.get("show_values", False), key=f"show_val_{i}")
                        cfg["show_values"] = show_values
                        value_format = st.text_input("数值格式 (如 .2f, $,)", value=cfg.get("value_format", ".2f"), key=f"val_fmt_{i}")
                        cfg["value_format"] = value_format
                        y_axis_title_format = st.text_input("Y轴标题格式", value=cfg.get("y_axis_title_format", ""), key=f"y_title_fmt_{i}")
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
                            if cfg.get("y_axis_title_format"):
                                fig.update_layout(yaxis_title=cfg["y_axis_title_format"])
                            if cfg.get("show_values"):
                                if ct == "饼图":
                                    fig.update_traces(texttemplate=f"%{{value:{cfg.get('value_format', '.2f')}}}", textposition="outside")
                                elif ct in ["柱状图", "折线图", "面积图"]:
                                    fig.update_traces(texttemplate=f"%{{y:{cfg.get('value_format', '.2f')}}}", textposition="outside")
                            st.plotly_chart(fig, use_container_width=True, key=f"final_plot_{i}")
                    except Exception as e:
                        st.error(f"图表生成出错: {e}")
                i += 1
    
    # 3. 页面底部说明文档（精简完整版）
    st.divider()
    with st.expander("📖 图表配置指南（点击展开）", expanded=False
